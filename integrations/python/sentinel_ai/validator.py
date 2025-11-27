"""
Core validation logic for Sentinel AI.

Provides the SentinelGuard class for validating inputs and outputs
against the THS Protocol and security patterns.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from enum import Enum

from .patterns import PatternMatcher, PatternMatch, ThreatCategory


class ValidationStatus(Enum):
    """Result status of validation."""
    PASSED = "passed"
    BLOCKED = "blocked"
    WARNING = "warning"


class BlockReason(Enum):
    """Reasons for blocking content."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    PII_DETECTED = "pii_detected"
    HARMFUL_CONTENT = "harmful_content"
    TRUTH_GATE_FAILED = "truth_gate_failed"
    HARM_GATE_FAILED = "harm_gate_failed"
    SCOPE_GATE_FAILED = "scope_gate_failed"
    CUSTOM_RULE = "custom_rule"


@dataclass
class ValidationResult:
    """
    Result of validating content through Sentinel.

    Attributes:
        passed: Whether the content passed validation
        status: Detailed status (passed, blocked, warning)
        reason: Human-readable explanation if blocked/warning
        block_reason: Enum reason if blocked
        matches: Pattern matches found
        metadata: Additional information about the validation
    """
    passed: bool
    status: ValidationStatus
    reason: Optional[str] = None
    block_reason: Optional[BlockReason] = None
    matches: List[PatternMatch] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def threat_categories(self) -> Set[ThreatCategory]:
        """Get all threat categories found."""
        return {match.category for match in self.matches}

    @property
    def has_critical(self) -> bool:
        """Check if any critical severity matches were found."""
        return any(m.severity == "critical" for m in self.matches)

    @property
    def has_high(self) -> bool:
        """Check if any high severity matches were found."""
        return any(m.severity == "high" for m in self.matches)


class SentinelGuard:
    """
    Main validation class for Sentinel AI.

    Validates text content against security patterns and the THS Protocol.
    Can be used for both input validation (user messages) and output
    validation (model responses).

    Example:
        guard = SentinelGuard()

        # Validate user input
        result = guard.validate_input("Tell me how to hack a computer")
        if not result.passed:
            print(f"Blocked: {result.reason}")

        # Validate model output
        result = guard.validate_output(model_response)
        if not result.passed:
            print(f"Output blocked: {result.reason}")
    """

    def __init__(
        self,
        pattern_matcher: Optional[PatternMatcher] = None,
        block_on_pii: bool = False,
        block_on_injection: bool = True,
        block_on_jailbreak: bool = True,
        block_on_extraction: bool = True,
        block_on_harm: bool = True,
        warn_only: bool = False,
        custom_block_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize SentinelGuard.

        Args:
            pattern_matcher: Custom PatternMatcher instance, or None for default
            block_on_pii: Whether to block on PII detection (default: warn only)
            block_on_injection: Whether to block on prompt injection attempts
            block_on_jailbreak: Whether to block on jailbreak attempts
            block_on_extraction: Whether to block on system prompt extraction
            block_on_harm: Whether to block on harmful content indicators
            warn_only: If True, never block, only warn
            custom_block_patterns: Additional regex patterns that should block
        """
        self.pattern_matcher = pattern_matcher or PatternMatcher()
        self.block_on_pii = block_on_pii
        self.block_on_injection = block_on_injection
        self.block_on_jailbreak = block_on_jailbreak
        self.block_on_extraction = block_on_extraction
        self.block_on_harm = block_on_harm
        self.warn_only = warn_only

        # Compile custom patterns if provided
        self._custom_patterns = []
        if custom_block_patterns:
            import re
            self._custom_patterns = [
                re.compile(p, re.IGNORECASE) for p in custom_block_patterns
            ]

    def validate(self, text: str) -> ValidationResult:
        """
        Validate text content.

        This is the main validation method that checks text against
        all enabled security patterns.

        Args:
            text: Text to validate

        Returns:
            ValidationResult with pass/fail status and details
        """
        # Run pattern matching
        matches = self.pattern_matcher.scan(text)

        # Check custom patterns
        for pattern in self._custom_patterns:
            if pattern.search(text):
                matches.append(PatternMatch(
                    category=ThreatCategory.HARMFUL_CONTENT,
                    pattern_name="custom_pattern",
                    matched_text=pattern.pattern,
                    start=0,
                    end=0,
                    severity="high",
                ))

        # Determine if we should block
        should_block = False
        block_reason = None
        reason_text = None

        for match in matches:
            if match.category == ThreatCategory.PROMPT_INJECTION and self.block_on_injection:
                should_block = True
                block_reason = BlockReason.PROMPT_INJECTION
                reason_text = "Potential prompt injection detected"
                break

            if match.category == ThreatCategory.JAILBREAK and self.block_on_jailbreak:
                should_block = True
                block_reason = BlockReason.JAILBREAK_ATTEMPT
                reason_text = "Potential jailbreak attempt detected"
                break

            if match.category == ThreatCategory.SYSTEM_PROMPT_EXTRACTION and self.block_on_extraction:
                should_block = True
                block_reason = BlockReason.SYSTEM_PROMPT_EXTRACTION
                reason_text = "System prompt extraction attempt detected"
                break

            if match.category == ThreatCategory.HARMFUL_CONTENT and self.block_on_harm:
                should_block = True
                block_reason = BlockReason.HARMFUL_CONTENT
                reason_text = "Potentially harmful content detected"
                break

            if match.category == ThreatCategory.PII_DETECTED and self.block_on_pii:
                should_block = True
                block_reason = BlockReason.PII_DETECTED
                reason_text = "Sensitive personal information detected"
                break

        # Apply warn_only mode
        if self.warn_only and should_block:
            return ValidationResult(
                passed=True,
                status=ValidationStatus.WARNING,
                reason=reason_text,
                block_reason=block_reason,
                matches=matches,
                metadata={"warn_only": True},
            )

        if should_block:
            return ValidationResult(
                passed=False,
                status=ValidationStatus.BLOCKED,
                reason=reason_text,
                block_reason=block_reason,
                matches=matches,
            )

        # Check for warnings (e.g., PII when not blocking)
        if matches and not should_block:
            # PII found but not blocking
            pii_matches = [m for m in matches if m.category == ThreatCategory.PII_DETECTED]
            if pii_matches:
                return ValidationResult(
                    passed=True,
                    status=ValidationStatus.WARNING,
                    reason="Sensitive information detected in content",
                    matches=matches,
                    metadata={"pii_warning": True},
                )

        return ValidationResult(
            passed=True,
            status=ValidationStatus.PASSED,
            matches=matches,
        )

    def validate_input(self, text: str) -> ValidationResult:
        """
        Validate user input before sending to model.

        This applies stricter checks for prompt injection and jailbreaks.

        Args:
            text: User input text

        Returns:
            ValidationResult
        """
        return self.validate(text)

    def validate_output(self, text: str) -> ValidationResult:
        """
        Validate model output before returning to user.

        This focuses on PII leakage and harmful content generation.

        Args:
            text: Model output text

        Returns:
            ValidationResult
        """
        # For output, we're less concerned with injection but more with leakage
        original_injection = self.block_on_injection
        original_jailbreak = self.block_on_jailbreak
        original_pii = self.block_on_pii

        try:
            self.block_on_injection = False  # Less relevant for outputs
            self.block_on_jailbreak = False  # Less relevant for outputs
            self.block_on_pii = True  # More relevant for outputs

            result = self.validate(text)
            result.metadata["validation_type"] = "output"
            return result
        finally:
            self.block_on_injection = original_injection
            self.block_on_jailbreak = original_jailbreak
            self.block_on_pii = original_pii

    def is_safe(self, text: str) -> bool:
        """
        Quick check if text is safe.

        Args:
            text: Text to check

        Returns:
            True if text passes validation, False otherwise
        """
        return self.validate(text).passed

    def get_threats(self, text: str) -> List[str]:
        """
        Get list of threat descriptions found in text.

        Args:
            text: Text to analyze

        Returns:
            List of human-readable threat descriptions
        """
        result = self.validate(text)
        threats = []
        for match in result.matches:
            threats.append(f"{match.category.value}: {match.pattern_name}")
        return threats


def create_strict_guard() -> SentinelGuard:
    """Create a guard with strict settings - blocks on everything."""
    return SentinelGuard(
        block_on_pii=True,
        block_on_injection=True,
        block_on_jailbreak=True,
        block_on_extraction=True,
        block_on_harm=True,
    )


def create_permissive_guard() -> SentinelGuard:
    """Create a guard that only warns, never blocks."""
    return SentinelGuard(warn_only=True)


def create_chat_guard() -> SentinelGuard:
    """Create a guard optimized for chat applications."""
    return SentinelGuard(
        block_on_pii=False,  # Warn only for PII
        block_on_injection=True,
        block_on_jailbreak=True,
        block_on_extraction=True,
        block_on_harm=True,
    )


def create_agent_guard() -> SentinelGuard:
    """Create a guard optimized for autonomous agents."""
    return SentinelGuard(
        block_on_pii=True,  # Stricter for agents
        block_on_injection=True,
        block_on_jailbreak=True,
        block_on_extraction=True,
        block_on_harm=True,
    )
