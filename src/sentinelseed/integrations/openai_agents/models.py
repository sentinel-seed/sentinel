"""
Pydantic models for OpenAI Agents SDK integration.

These models define the structure of validation outputs and internal data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Check for Pydantic availability (comes with openai-agents)
PYDANTIC_AVAILABLE = False
try:
    from pydantic import BaseModel, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = None
    Field = None


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


@dataclass
class ValidationMetadata:
    """
    Metadata about a validation operation.

    Stores information about timing, truncation, and injection detection.
    """

    timestamp: datetime = field(default_factory=datetime.utcnow)
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
    """

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._violations: List[ViolationRecord] = []
        self._lock = None  # Lazy import threading

    def _get_lock(self):
        """Lazily create lock to avoid import overhead."""
        if self._lock is None:
            import threading
            self._lock = threading.Lock()
        return self._lock

    def add(self, record: ViolationRecord) -> None:
        """Add a violation record, removing oldest if at capacity."""
        with self._get_lock():
            self._violations.append(record)
            while len(self._violations) > self._max_size:
                self._violations.pop(0)

    def get_recent(self, count: int = 10) -> List[ViolationRecord]:
        """Get the most recent violations."""
        with self._get_lock():
            return list(self._violations[-count:])

    def clear(self) -> None:
        """Clear all violation records."""
        with self._get_lock():
            self._violations.clear()

    def count(self) -> int:
        """Get total number of recorded violations."""
        with self._get_lock():
            return len(self._violations)

    def count_by_gate(self) -> Dict[str, int]:
        """Get count of violations by gate."""
        with self._get_lock():
            counts: Dict[str, int] = {}
            for v in self._violations:
                gate = v.gate_violated or "unknown"
                counts[gate] = counts.get(gate, 0) + 1
            return counts


# Module-level violations log
_violations_log: Optional[ViolationsLog] = None


def get_violations_log(max_size: int = 1000) -> ViolationsLog:
    """Get or create the module-level violations log."""
    global _violations_log
    if _violations_log is None:
        _violations_log = ViolationsLog(max_size=max_size)
    return _violations_log
