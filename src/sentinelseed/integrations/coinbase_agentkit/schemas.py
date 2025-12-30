"""
Pydantic schemas for Sentinel AgentKit actions.

These schemas define the input parameters for each Sentinel action,
following AgentKit's pattern of using Pydantic BaseModel for validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    OWASP_LLM = "owasp_llm"
    EU_AI_ACT = "eu_ai_act"
    CSA_AI = "csa_ai"
    NIST_RMF = "nist_rmf"


class ValidatePromptSchema(BaseModel):
    """Schema for validating prompts through THSP gates."""

    prompt: str = Field(
        ...,
        description="The prompt or text to validate for safety"
    )
    context: Optional[str] = Field(
        None,
        description="Optional context about the prompt's intended use"
    )
    strict_mode: bool = Field(
        False,
        description="If true, applies stricter validation rules"
    )


class ValidateTransactionSchema(BaseModel):
    """Schema for validating blockchain transactions."""

    to_address: str = Field(
        ...,
        description="The destination address for the transaction"
    )
    value: str = Field(
        ...,
        description="The value/amount of the transaction"
    )
    data: Optional[str] = Field(
        None,
        description="Optional transaction data (for contract calls)"
    )
    chain_id: Optional[int] = Field(
        None,
        description="The chain ID for the transaction"
    )
    check_contract: bool = Field(
        True,
        description="Whether to check if destination is a known malicious contract"
    )


class ScanSecretsSchema(BaseModel):
    """Schema for scanning content for exposed secrets."""

    content: str = Field(
        ...,
        description="The content to scan for secrets (code, logs, etc.)"
    )
    scan_types: List[str] = Field(
        default=["api_keys", "private_keys", "passwords", "tokens"],
        description="Types of secrets to scan for"
    )


class CheckComplianceSchema(BaseModel):
    """Schema for checking compliance with safety frameworks."""

    content: str = Field(
        ...,
        description="The content to check for compliance"
    )
    frameworks: List[ComplianceFramework] = Field(
        default=[ComplianceFramework.OWASP_LLM],
        description="Compliance frameworks to check against"
    )


class AnalyzeRiskSchema(BaseModel):
    """Schema for analyzing risk of agent actions."""

    action_type: str = Field(
        ...,
        description="The type of action being performed (e.g., 'transfer', 'swap', 'deploy')"
    )
    parameters: dict = Field(
        ...,
        description="The parameters of the action"
    )
    context: Optional[str] = Field(
        None,
        description="Additional context about the action"
    )


class ValidateOutputSchema(BaseModel):
    """Schema for validating agent outputs before returning to user."""

    output: str = Field(
        ...,
        description="The output content to validate"
    )
    output_type: str = Field(
        default="text",
        description="The type of output (text, code, json, etc.)"
    )
    filter_pii: bool = Field(
        True,
        description="Whether to filter personally identifiable information"
    )
