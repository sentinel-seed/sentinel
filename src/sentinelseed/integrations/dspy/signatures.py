"""
DSPy Signatures for Sentinel THSP validation.

These signatures define input/output contracts for safety validation tasks.
They follow DSPy conventions and can be used with any DSPy module.

Usage:
    import dspy
    from sentinelseed.integrations.dspy import THSPCheckSignature

    # Use with Predict
    checker = dspy.Predict(THSPCheckSignature)
    result = checker(content="Some content to validate")
"""

from typing import Literal, Optional

try:
    import dspy
    from dspy import InputField, OutputField, Signature
except (ImportError, AttributeError):
    raise ImportError(
        "dspy is required for this integration. "
        "Install with: pip install dspy"
    )


class THSPCheckSignature(Signature):
    """
    Signature for THSP (Truth-Harm-Scope-Purpose) safety validation.

    Evaluates content through the four THSP gates and returns
    structured safety assessment.
    """

    content: str = InputField(
        desc="The content to validate for safety"
    )
    context: Optional[str] = InputField(
        desc="Optional context about the content",
        default=None
    )

    is_safe: bool = OutputField(
        desc="Whether the content passes all THSP gates"
    )
    truth_gate: Literal["pass", "fail"] = OutputField(
        desc="Truth gate result - fails if content involves deception"
    )
    harm_gate: Literal["pass", "fail"] = OutputField(
        desc="Harm gate result - fails if content could enable harm"
    )
    scope_gate: Literal["pass", "fail"] = OutputField(
        desc="Scope gate result - fails if content exceeds boundaries"
    )
    purpose_gate: Literal["pass", "fail"] = OutputField(
        desc="Purpose gate result - fails if no legitimate purpose"
    )
    reasoning: str = OutputField(
        desc="Explanation of the safety assessment"
    )


class SafetyFilterSignature(Signature):
    """
    Signature for filtering unsafe content.

    Takes content and returns either the original (if safe) or
    a sanitized/refused version (if unsafe).
    """

    content: str = InputField(
        desc="The content to filter for safety"
    )

    is_safe: bool = OutputField(
        desc="Whether the original content is safe"
    )
    output: str = OutputField(
        desc="Original content if safe, or refusal message if unsafe"
    )
    blocked_reason: Optional[str] = OutputField(
        desc="Reason for blocking, if content was unsafe",
        default=None
    )


class ContentClassificationSignature(Signature):
    """
    Signature for classifying content risk level.

    Provides detailed risk assessment without binary pass/fail.
    """

    content: str = InputField(
        desc="The content to classify"
    )

    risk_level: Literal["low", "medium", "high", "critical"] = OutputField(
        desc="Overall risk level of the content"
    )
    categories: list[str] = OutputField(
        desc="List of risk categories detected (e.g., 'deception', 'harm', 'scope_violation')"
    )
    confidence: float = OutputField(
        desc="Confidence in the assessment (0.0 to 1.0)"
    )
    summary: str = OutputField(
        desc="Brief summary of the risk assessment"
    )


# THSP validation instructions for use with inline signatures
THSP_INSTRUCTIONS = """Analyze content through the THSP Protocol safety gates:

TRUTH: Does this involve deception or misinformation?
HARM: Could this enable harm to people, systems, or society?
SCOPE: Is this within appropriate operational boundaries?
PURPOSE: Does this serve a legitimate, beneficial purpose?

All gates must pass for content to be considered safe."""
