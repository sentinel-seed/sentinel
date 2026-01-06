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
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sentinelseed.detection.input_validator import InputValidationResult
from sentinelseed.detection.output_validator import OutputValidationResult


@dataclass
class ObservationResult:
    """
    Result from SentinelObserver (Gate 3).

    The observer analyzes a transcript of user-AI interaction
    and evaluates two dimensions:
    1. Was the input malicious?
    2. Did the AI respond appropriately?

    Attributes:
        is_safe: Overall safety assessment
        input_malicious: Whether the input was a malicious request
        ai_complied: Whether the AI complied with the request
        reasoning: Explanation of the assessment
        raw_response: Raw LLM response (for debugging)
        latency_ms: Time taken for the observation
    """

    is_safe: bool
    input_malicious: bool = False
    ai_complied: bool = False
    reasoning: str = ""
    raw_response: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_safe": self.is_safe,
            "input_malicious": self.input_malicious,
            "ai_complied": self.ai_complied,
            "reasoning": self.reasoning,
            "latency_ms": self.latency_ms,
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
        reasoning: Explanation of the decision
        violated_gates: List of THSP gates that were violated
        evidence: Evidence supporting the decision
        latency_ms: Total time for validation
        gate3_was_called: Whether Gate 3 was invoked
    """

    # Overall decision
    blocked: bool
    allowed: bool

    # Gate that made the decision
    decided_by: str  # "gate1", "gate2", "gate3", "error"

    # Details from each gate
    gate1_result: Optional[InputValidationResult] = None
    gate2_result: Optional[OutputValidationResult] = None
    gate3_result: Optional[ObservationResult] = None

    # Aggregated info
    confidence: float = 0.0
    reasoning: str = ""
    violated_gates: List[str] = field(default_factory=list)
    evidence: str = ""

    # Metadata
    latency_ms: float = 0.0
    gate3_was_called: bool = False

    def __post_init__(self) -> None:
        """Validate result state."""
        if self.blocked == self.allowed:
            raise ValueError("blocked and allowed cannot have the same value")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "blocked": self.blocked,
            "allowed": self.allowed,
            "decided_by": self.decided_by,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "violated_gates": self.violated_gates,
            "evidence": self.evidence,
            "latency_ms": self.latency_ms,
            "gate3_was_called": self.gate3_was_called,
        }

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
    ) -> "SentinelResult":
        """Factory for Gate 1 block (input attack detected)."""
        return cls(
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

    @classmethod
    def blocked_by_gate2(
        cls,
        gate2_result: OutputValidationResult,
        gate1_result: Optional[InputValidationResult] = None,
        latency_ms: float = 0.0,
    ) -> "SentinelResult":
        """Factory for Gate 2 block (seed failure detected)."""
        return cls(
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

    @classmethod
    def blocked_by_gate3(
        cls,
        gate3_result: ObservationResult,
        gate1_result: Optional[InputValidationResult] = None,
        gate2_result: Optional[OutputValidationResult] = None,
        latency_ms: float = 0.0,
    ) -> "SentinelResult":
        """Factory for Gate 3 block (observer detected issue)."""
        return cls(
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
    ) -> "SentinelResult":
        """Factory for error case."""
        return cls(
            blocked=fail_closed,
            allowed=not fail_closed,
            decided_by="error",
            reasoning=f"Validation error: {error_msg}",
            confidence=0.0,
        )
