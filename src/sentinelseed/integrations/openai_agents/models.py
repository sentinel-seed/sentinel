"""
Pydantic models for OpenAI Agents SDK integration.

These models define the structure of validation outputs and internal data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import threading

# Check for Pydantic availability (comes with openai-agents)
PYDANTIC_AVAILABLE = False
try:
    from pydantic import BaseModel, Field

    PYDANTIC_AVAILABLE = True
except (ImportError, AttributeError):
    # AttributeError: Pydantic installed but with incompatible structure
    BaseModel = None
    Field = None


class PydanticNotAvailableError(ImportError):
    """
    Raised when Pydantic is required but not available.

    This typically means the openai-agents package is not installed correctly,
    since it requires Pydantic as a dependency.
    """

    def __init__(self):
        super().__init__(
            "Pydantic is required for THSPValidationOutput but is not installed. "
            "This usually means openai-agents is not installed. "
            "Install with: pip install openai-agents"
        )


def _create_thsp_validation_output():
    """
    Create the Pydantic model for THSP validation output.

    Returns None if Pydantic is not available.
    """
    if not PYDANTIC_AVAILABLE or BaseModel is None:
        return None

    class THSPValidationOutput(BaseModel):
        """
        Output model for THSP semantic validation.

        This structured output is returned by the guardrail agent
        after analyzing content against the four THSP gates.
        """

        is_safe: bool = Field(
            description="Whether the content passes all required THSP gates"
        )

        truth_passes: bool = Field(
            description="Whether content passes the Truth gate (no deception/misinformation)"
        )

        harm_passes: bool = Field(
            description="Whether content passes the Harm gate (no dangerous content)"
        )

        scope_passes: bool = Field(
            description="Whether content passes the Scope gate (appropriate boundaries)"
        )

        purpose_passes: bool = Field(
            description="Whether content passes the Purpose gate (legitimate benefit)"
        )

        violated_gate: Optional[str] = Field(
            default=None,
            description="Which gate was violated first, if any (truth/harm/scope/purpose)"
        )

        reasoning: str = Field(
            description="Explanation of the validation decision"
        )

        risk_level: str = Field(
            default="low",
            description="Risk level: low, medium, high, critical"
        )

        injection_attempt_detected: bool = Field(
            default=False,
            description="Whether a prompt injection attempt was detected in the content"
        )

    return THSPValidationOutput


# Create the model class at module level
THSPValidationOutput = _create_thsp_validation_output()


def require_thsp_validation_output():
    """
    Get THSPValidationOutput class, raising if not available.

    Raises:
        PydanticNotAvailableError: If Pydantic/THSPValidationOutput is not available
    """
    if THSPValidationOutput is None:
        raise PydanticNotAvailableError()
    return THSPValidationOutput


def get_reasoning_safe(validation: Any) -> str:
    """
    Safely extract reasoning from a validation result.

    Handles None, empty string, and missing attribute cases.

    Args:
        validation: Validation result object

    Returns:
        Reasoning string (empty string if not available)
    """
    if validation is None:
        return ""
    reasoning = getattr(validation, "reasoning", None)
    if reasoning is None:
        return ""
    return str(reasoning)


def truncate_reasoning(reasoning: str, max_length: int = 100) -> str:
    """
    Truncate reasoning string safely with ellipsis.

    Args:
        reasoning: Reasoning string to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated reasoning string
    """
    if not reasoning:
        return ""
    if len(reasoning) > max_length:
        return reasoning[:max_length] + "..."
    return reasoning


@dataclass
class ValidationMetadata:
    """
    Metadata about a validation operation.

    Stores information about timing, truncation, and injection detection.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    original_length: int = 0
    was_truncated: bool = False
    injection_detected: bool = False
    injection_reason: str = ""
    validation_model: str = ""
    validation_time_ms: float = 0.0


@dataclass
class ViolationRecord:
    """
    Record of a validation violation for logging/auditing.

    Sensitive content is NOT stored; only metadata and sanitized excerpts.
    """

    timestamp: datetime
    gate_violated: Optional[str]
    risk_level: str
    reasoning_summary: str  # Truncated, sanitized
    content_hash: str  # SHA256 of original content for deduplication
    was_input: bool  # True for input validation, False for output
    injection_detected: bool


class ViolationsLog:
    """
    Thread-safe log of recent violations with automatic size limiting.

    Does NOT store full content for privacy. Only stores metadata.
    Thread-safety is guaranteed by initializing the lock in __init__.
    """

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._violations: List[ViolationRecord] = []
        # Initialize lock immediately for thread safety
        # This avoids race conditions that could occur with lazy initialization
        self._lock = threading.Lock()

    def add(self, record: ViolationRecord) -> None:
        """Add a violation record, removing oldest if at capacity."""
        with self._lock:
            self._violations.append(record)
            while len(self._violations) > self._max_size:
                self._violations.pop(0)

    def get_recent(self, count: int = 10) -> List[ViolationRecord]:
        """Get the most recent violations."""
        with self._lock:
            return list(self._violations[-count:])

    def clear(self) -> None:
        """Clear all violation records."""
        with self._lock:
            self._violations.clear()

    def count(self) -> int:
        """Get total number of recorded violations."""
        with self._lock:
            return len(self._violations)

    def count_by_gate(self) -> Dict[str, int]:
        """Get count of violations by gate."""
        with self._lock:
            counts: Dict[str, int] = {}
            for v in self._violations:
                gate = v.gate_violated or "unknown"
                counts[gate] = counts.get(gate, 0) + 1
            return counts


# Module-level violations log with thread-safe access
_violations_log: Optional[ViolationsLog] = None
_violations_log_lock = threading.Lock()


def get_violations_log(max_size: int = 1000) -> ViolationsLog:
    """
    Get or create the module-level violations log (thread-safe).

    Uses double-checked locking pattern for efficiency.
    """
    global _violations_log
    if _violations_log is None:
        with _violations_log_lock:
            # Double-check after acquiring lock
            if _violations_log is None:
                _violations_log = ViolationsLog(max_size=max_size)
    return _violations_log
