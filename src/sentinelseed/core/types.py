"""
Sentinel Core Types - TypedDicts for type-safe function returns.

This module defines TypedDicts for the various return types used throughout
the Sentinel library. Using TypedDicts instead of Dict[str, Any] provides:
- Better IDE autocompletion
- Static type checking with mypy
- Self-documenting code
- Clearer API contracts

Usage:
    from sentinelseed.core.types import ChatResponse, ValidationInfo

    def process_response(response: ChatResponse) -> None:
        print(response["response"])
        if response.get("validation"):
            print(response["validation"]["is_safe"])
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union
from typing_extensions import TypedDict, NotRequired


class ValidationInfo(TypedDict):
    """
    Validation result information returned from chat() when validate_response=True.

    Attributes:
        is_safe: Whether the response passed validation
        violations: List of violation messages if unsafe
        layer: Which validation layer made the decision (heuristic, semantic, both)
        risk_level: Assessed risk level (low, medium, high, critical)
    """
    is_safe: bool
    violations: List[str]
    layer: str
    risk_level: str


class ChatResponse(TypedDict):
    """
    Response from Sentinel.chat() method.

    Attributes:
        response: The LLM response text
        model: Model used for the response
        provider: Provider used (openai, anthropic)
        seed_level: Seed level used (minimal, standard, full)
        validation: Validation info if validate_response=True
    """
    response: str
    model: str
    provider: str
    seed_level: str
    validation: NotRequired[ValidationInfo]


class ValidatorStats(TypedDict, total=False):
    """
    Statistics from LayeredValidator.

    Attributes:
        total_validations: Total number of validations performed
        heuristic_blocks: Number blocked by heuristic layer
        semantic_blocks: Number blocked by semantic layer
        allowed: Number of validations that passed
        errors: Number of validation errors
        timeouts: Number of validation timeouts
        total_latency_ms: Total latency in milliseconds
        avg_latency_ms: Average latency in milliseconds
        block_rate: Percentage of validations blocked
        semantic_enabled: Whether semantic validation is enabled
        heuristic_enabled: Whether heuristic validation is enabled
    """
    total_validations: int
    heuristic_blocks: int
    semantic_blocks: int
    allowed: int
    errors: int
    timeouts: int
    total_latency_ms: float
    avg_latency_ms: float
    block_rate: float
    semantic_enabled: bool
    heuristic_enabled: bool


class THSPResultDict(TypedDict):
    """
    Dictionary representation of THSPResult for serialization.

    Attributes:
        is_safe: Overall safety assessment
        truth_passes: Whether content passes Truth gate
        harm_passes: Whether content passes Harm gate
        scope_passes: Whether content passes Scope gate
        purpose_passes: Whether content passes Purpose gate
        violated_gate: Which gate failed first (if any)
        reasoning: Explanation of the decision
        risk_level: Assessed risk level
        gate_results: Dict of all gate results
        failed_gates: List of gates that failed
    """
    is_safe: bool
    truth_passes: bool
    harm_passes: bool
    scope_passes: bool
    purpose_passes: bool
    violated_gate: Optional[str]
    reasoning: str
    risk_level: str
    gate_results: Dict[str, bool]
    failed_gates: List[str]


class LegacyValidationDict(TypedDict):
    """
    Legacy validation result format for backwards compatibility.

    This format was used by validate_request() in earlier versions.

    Attributes:
        should_proceed: Whether to proceed with the request
        concerns: List of concerns about the content
        risk_level: Assessed risk level
    """
    should_proceed: bool
    concerns: List[str]
    risk_level: str


# Provider types for better type hints on chat providers
ProviderName = Union[str, None]  # "openai" or "anthropic"


__all__ = [
    "ValidationInfo",
    "ChatResponse",
    "ValidatorStats",
    "THSPResultDict",
    "LegacyValidationDict",
    "ProviderName",
]
