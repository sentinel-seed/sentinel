"""
Sentinel v3.0 Result Types.

Result dataclasses for the 3-gate architecture as defined in
SENTINEL_V3_ARCHITECTURE.md.

Example:
    from sentinelseed.core import ObservationResult, SentinelResult

    # Gate 3 result
    observation = ObservationResult(
        is_safe=False,
        input_malicious=True,
        ai_complied=True,
        reasoning="AI provided harmful content",
    )

    # Final result
    result = SentinelResult.blocked(
        decided_by="gate3",
        gate3_result=observation,
    )

    # Get user-facing message (never reveals internal details)
    print(result.user_message)  # "I'm not able to help with that request."
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sentinelseed.detection.input_validator import InputValidationResult
from sentinelseed.detection.output_validator import OutputValidationResult

if TYPE_CHECKING:
    from sentinelseed.core.sentinel_config import BlockMessages


@dataclass
class ObservationResult:
    """
    Result from SentinelObserver (Gate 3).

    The observer analyzes a transcript of user-AI interaction
    and evaluates against the THSP protocol (Truth, Harm, Scope, Purpose).

    Attributes:
        is_safe: Overall safety assessment
        input_malicious: Whether the input was a malicious request
        ai_complied: Whether the AI complied with the request
        gates_violated: List of THSP gates violated (TRUTH, HARM, SCOPE, PURPOSE)
        reasoning: Explanation of the assessment
        raw_response: Raw LLM response (for debugging)
        latency_ms: Time taken for the observation
    """

    is_safe: bool
    input_malicious: bool = False
    ai_complied: bool = False
    gates_violated: List[str] = field(default_factory=list)
    reasoning: str = ""
    raw_response: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0

    # Token usage tracking (for cost monitoring)
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_safe": self.is_safe,
            "input_malicious": self.input_malicious,
            "ai_complied": self.ai_complied,
            "gates_violated": self.gates_violated,
            "reasoning": self.reasoning,
            "latency_ms": self.latency_ms,
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
            "tokens_total": self.tokens_total,
        }

    @classmethod
    def safe(cls, reasoning: str = "Transcript is safe") -> "ObservationResult":
        """Factory for safe observation."""
        return cls(
            is_safe=True,
            input_malicious=False,
            ai_complied=False,
            reasoning=reasoning,
        )

    @classmethod
    def unsafe(
        cls,
        input_malicious: bool,
        ai_complied: bool,
        reasoning: str,
    ) -> "ObservationResult":
        """Factory for unsafe observation."""
        return cls(
            is_safe=False,
            input_malicious=input_malicious,
            ai_complied=ai_complied,
            reasoning=reasoning,
        )

    @classmethod
    def error(cls, error_msg: str) -> "ObservationResult":
        """Factory for error case (fail-closed)."""
        return cls(
            is_safe=False,
            reasoning=f"Observation failed: {error_msg}",
        )


# Default messages (imported at runtime to avoid circular import)
_DEFAULT_MESSAGES = {
    "gate1": "I'm not able to help with that request.",
    "gate2": "I'm not able to help with that request.",
    "gate3": "I'm not able to help with that request.",
    "gate4": "I'm not able to help with that request.",
    "l4_unavailable": "I'm not able to help with that request.",
    "error": "Something went wrong. Please try again.",
    "default": "I'm not able to help with that request.",
}


@dataclass
class SentinelResult:
    """
    Unified result from SentinelValidator.

    Aggregates results from all 3 gates and provides a single
    decision point for the calling code.

    Attributes:
        blocked: Whether the interaction was blocked
        allowed: Whether the interaction was allowed
        decided_by: Which gate made the final decision
        gate1_result: Result from Gate 1 (InputValidator)
        gate2_result: Result from Gate 2 (OutputValidator)
        gate3_result: Result from Gate 3 (SentinelObserver)
        confidence: Confidence level of the decision
        reasoning: Explanation of the decision (INTERNAL - never show to user)
        violated_gates: List of THSP gates that were violated
        evidence: Evidence supporting the decision (INTERNAL - never show to user)
        latency_ms: Total time for validation
        gate3_was_called: Whether Gate 3 was invoked
        user_message: Safe message to show to end user (never reveals detection details)

    SECURITY NOTE:
        When blocked=True, the AI's response (if any) should NEVER be shown to the user.
        Always use `user_message` property for user-facing output.
        The `reasoning` and `evidence` fields are for internal logging only.
    """

    # Overall decision
    blocked: bool
    allowed: bool

    # Gate that made the decision
    decided_by: str  # "gate1", "gate2", "gate3", "gate4", "error"

    # Details from each gate
    gate1_result: Optional[InputValidationResult] = None
    gate2_result: Optional[OutputValidationResult] = None
    gate3_result: Optional[ObservationResult] = None

    # Aggregated info
    confidence: float = 0.0
    reasoning: str = ""  # INTERNAL ONLY - never expose to user
    violated_gates: List[str] = field(default_factory=list)
    evidence: str = ""  # INTERNAL ONLY - never expose to user

    # Metadata
    latency_ms: float = 0.0
    gate3_was_called: bool = False

    # Partial validation (when L4 fails but L1-L2-L3 passed)
    partial_validation: bool = False
    l4_error: Optional[str] = None  # Error message if L4 failed

    # User-facing message (set by validator with configured messages)
    _user_message: Optional[str] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate result state."""
        if self.blocked == self.allowed:
            raise ValueError("blocked and allowed cannot have the same value")

    @property
    def user_message(self) -> str:
        """
        Get the user-facing message for this result.

        SECURITY: This message is safe to show to end users.
        It never reveals detection mechanisms or internal reasoning.

        Returns:
            Empty string if allowed, configured message if blocked.
        """
        if self.allowed:
            return ""

        if self._user_message:
            return self._user_message

        # Fallback to default messages
        return _DEFAULT_MESSAGES.get(self.decided_by, _DEFAULT_MESSAGES["default"])

    def with_user_message(self, message: str) -> "SentinelResult":
        """
        Return a copy of this result with a custom user message.

        Args:
            message: The user-facing message to set.

        Returns:
            New SentinelResult with the message set.
        """
        self._user_message = message
        return self

    def to_dict(self, include_internal: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Args:
            include_internal: If True, includes reasoning/evidence (for logging).
                              If False, only includes safe user-facing data.
        """
        result = {
            "blocked": self.blocked,
            "allowed": self.allowed,
            "decided_by": self.decided_by,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "gate3_was_called": self.gate3_was_called,
            "partial_validation": self.partial_validation,
        }

        # Always include user_message (safe for users)
        if self.blocked:
            result["user_message"] = self.user_message

        # Internal details only for logging/debugging
        if include_internal:
            result["reasoning"] = self.reasoning
            result["violated_gates"] = self.violated_gates
            result["evidence"] = self.evidence

            if self.gate1_result:
                result["gate1"] = {
                    "is_attack": self.gate1_result.is_attack,
                    "attack_types": self.gate1_result.attack_types,
                    "confidence": self.gate1_result.confidence,
                }

            if self.gate2_result:
                result["gate2"] = {
                    "seed_failed": self.gate2_result.seed_failed,
                    "failure_types": self.gate2_result.failure_types,
                    "gates_failed": self.gate2_result.gates_failed,
                }

            if self.gate3_result:
                result["gate3"] = self.gate3_result.to_dict()

        return result

    # Factory methods

    @classmethod
    def blocked_by_gate1(
        cls,
        gate1_result: InputValidationResult,
        latency_ms: float = 0.0,
        user_message: Optional[str] = None,
    ) -> "SentinelResult":
        """
        Factory for Gate 1 block (input attack detected).

        NOTE: When Gate 1 blocks, the AI is NEVER called.
        The user receives only the user_message.
        """
        result = cls(
            blocked=True,
            allowed=False,
            decided_by="gate1",
            gate1_result=gate1_result,
            confidence=gate1_result.confidence,
            reasoning=f"Attack detected: {', '.join(gate1_result.attack_types)}",
            evidence="; ".join(gate1_result.attack_types),
            latency_ms=latency_ms,
            gate3_was_called=False,
        )
        if user_message:
            result._user_message = user_message
        return result

    @classmethod
    def blocked_by_gate2(
        cls,
        gate2_result: OutputValidationResult,
        gate1_result: Optional[InputValidationResult] = None,
        latency_ms: float = 0.0,
        user_message: Optional[str] = None,
    ) -> "SentinelResult":
        """
        Factory for Gate 2 block (seed failure detected in output).

        NOTE: When Gate 2 blocks, the AI's response is DISCARDED.
        The user receives only the user_message.
        """
        result = cls(
            blocked=True,
            allowed=False,
            decided_by="gate2",
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            confidence=gate2_result.confidence,
            reasoning=f"Seed failed: {', '.join(gate2_result.failure_types)}",
            violated_gates=gate2_result.gates_failed,
            evidence="; ".join(gate2_result.failure_types),
            latency_ms=latency_ms,
            gate3_was_called=False,
        )
        if user_message:
            result._user_message = user_message
        return result

    @classmethod
    def blocked_by_gate3(
        cls,
        gate3_result: ObservationResult,
        gate1_result: Optional[InputValidationResult] = None,
        gate2_result: Optional[OutputValidationResult] = None,
        latency_ms: float = 0.0,
        user_message: Optional[str] = None,
    ) -> "SentinelResult":
        """
        Factory for Gate 3 block (output validator detected issue).

        NOTE: When Gate 3 blocks, the AI's response is DISCARDED.
        The user receives only the user_message.
        """
        result = cls(
            blocked=True,
            allowed=False,
            decided_by="gate3",
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            gate3_result=gate3_result,
            confidence=0.9,  # LLM-based, high confidence
            reasoning=gate3_result.reasoning,
            latency_ms=latency_ms,
            gate3_was_called=True,
        )
        if user_message:
            result._user_message = user_message
        return result

    @classmethod
    def blocked_by_gate4(
        cls,
        gate3_result: ObservationResult,
        gate1_result: Optional[InputValidationResult] = None,
        gate2_result: Optional[OutputValidationResult] = None,
        latency_ms: float = 0.0,
        user_message: Optional[str] = None,
    ) -> "SentinelResult":
        """
        Factory for Gate 4 block (LLM observer detected issue).

        This is the L4 Sentinel Observer - the final semantic analysis layer.

        NOTE: When Gate 4 blocks, the AI's response is DISCARDED.
        The user receives only the user_message.
        """
        result = cls(
            blocked=True,
            allowed=False,
            decided_by="gate4",
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            gate3_result=gate3_result,
            confidence=0.9,  # LLM-based, high confidence
            reasoning=gate3_result.reasoning,
            latency_ms=latency_ms,
            gate3_was_called=True,
        )
        if user_message:
            result._user_message = user_message
        return result

    @classmethod
    def allowed_by_gate2(
        cls,
        gate2_result: OutputValidationResult,
        gate1_result: Optional[InputValidationResult] = None,
        latency_ms: float = 0.0,
    ) -> "SentinelResult":
        """Factory for Gate 2 allow (high confidence safe)."""
        return cls(
            blocked=False,
            allowed=True,
            decided_by="gate2",
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            confidence=gate2_result.confidence,
            reasoning="Content passed Gate 2 validation",
            latency_ms=latency_ms,
            gate3_was_called=False,
        )

    @classmethod
    def allowed_by_gate3(
        cls,
        gate3_result: ObservationResult,
        gate1_result: Optional[InputValidationResult] = None,
        gate2_result: Optional[OutputValidationResult] = None,
        latency_ms: float = 0.0,
    ) -> "SentinelResult":
        """Factory for Gate 3 allow (observer confirmed safe)."""
        return cls(
            blocked=False,
            allowed=True,
            decided_by="gate3",
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            gate3_result=gate3_result,
            confidence=0.9,
            reasoning=gate3_result.reasoning,
            latency_ms=latency_ms,
            gate3_was_called=True,
        )

    @classmethod
    def error(
        cls,
        error_msg: str,
        fail_closed: bool = True,
        user_message: Optional[str] = None,
    ) -> "SentinelResult":
        """
        Factory for error case.

        When fail_closed=True, the user receives the error user_message.
        The actual error details are never exposed.
        """
        result = cls(
            blocked=fail_closed,
            allowed=not fail_closed,
            decided_by="error",
            reasoning=f"Validation error: {error_msg}",
            confidence=0.0,
        )
        if user_message:
            result._user_message = user_message
        return result

    # --- L4 Fallback Factory Methods ---

    @classmethod
    def l4_unavailable_blocked(
        cls,
        error_msg: str,
        gate1_result: Optional[InputValidationResult] = None,
        gate2_result: Optional[OutputValidationResult] = None,
        latency_ms: float = 0.0,
        user_message: Optional[str] = None,
    ) -> "SentinelResult":
        """
        Factory for L4 unavailable with BLOCK fallback behavior.

        Used when L4 fails and config.gate4_fallback = Gate4Fallback.BLOCK.
        The request is blocked even though L1-L2-L3 may have passed.

        NOTE: The AI's response is DISCARDED for safety.
        """
        result = cls(
            blocked=True,
            allowed=False,
            decided_by="l4_unavailable",
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            confidence=0.0,
            reasoning=f"L4 unavailable, fallback=BLOCK: {error_msg}",
            latency_ms=latency_ms,
            gate3_was_called=False,
            partial_validation=False,
            l4_error=error_msg,
        )
        if user_message:
            result._user_message = user_message
        return result

    @classmethod
    def l4_unavailable_allowed(
        cls,
        error_msg: str,
        gate1_result: Optional[InputValidationResult] = None,
        gate2_result: Optional[OutputValidationResult] = None,
        latency_ms: float = 0.0,
    ) -> "SentinelResult":
        """
        Factory for L4 unavailable with ALLOW fallback behavior.

        Used when L4 fails and config.gate4_fallback = Gate4Fallback.ALLOW
        or Gate4Fallback.ALLOW_IF_L2_PASSED (and L2 passed).

        The request is allowed with partial_validation=True to indicate
        that L4 semantic analysis was not performed.

        SECURITY NOTE: This means the response was only validated by
        L1-L2-L3 heuristics, not by semantic LLM analysis.
        """
        # Determine confidence based on L2 result
        confidence = 0.7  # Lower confidence without L4
        if gate2_result and not gate2_result.seed_failed:
            confidence = 0.8

        return cls(
            blocked=False,
            allowed=True,
            decided_by="l2_fallback",
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            confidence=confidence,
            reasoning=f"L4 unavailable, allowed by fallback policy: {error_msg}",
            latency_ms=latency_ms,
            gate3_was_called=False,
            partial_validation=True,
            l4_error=error_msg,
        )
