"""Schemas for Sentinel AgentKit action provider.

These schemas define the input parameters for each Sentinel action,
following AgentKit's pattern of using Pydantic BaseModel for validation.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level classification for safety assessments."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks for validation."""

    OWASP_LLM = "owasp_llm"
    EU_AI_ACT = "eu_ai_act"
    CSA_AI = "csa_ai"
    NIST_RMF = "nist_rmf"


class ValidatePromptSchema(BaseModel):
    """Input schema for validating prompts through THSP gates."""

    prompt: str = Field(
        ...,
        description="The prompt or text input to validate for safety"
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
    """Input schema for validating blockchain transactions."""

    to_address: str = Field(
        ...,
        description="The destination address for the transaction"
    )
    value: str = Field(
        ...,
        description="The value/amount of the transaction in wei or smallest unit"
    )
    data: Optional[str] = Field(
        None,
        description="Optional transaction data for contract calls (hex encoded)"
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
    """Input schema for scanning content for exposed secrets."""

    content: str = Field(
        ...,
        description="The content to scan for secrets (code, logs, config, etc.)"
    )
    scan_types: list[str] = Field(
        default=["api_keys", "private_keys", "passwords", "tokens"],
        description="Types of secrets to scan for"
    )


class CheckComplianceSchema(BaseModel):
    """Input schema for checking compliance with safety frameworks."""

    content: str = Field(
        ...,
        description="The content to check for compliance"
    )
    frameworks: list[ComplianceFramework] = Field(
        default=[ComplianceFramework.OWASP_LLM],
        description="Compliance frameworks to check against"
    )


class AnalyzeRiskSchema(BaseModel):
    """Input schema for analyzing risk of agent actions."""

    action_type: str = Field(
        ...,
        description="The type of action (e.g., 'transfer', 'swap', 'deploy', 'approve')"
    )
    parameters: dict = Field(
        ...,
        description="The parameters of the action being performed"
    )
    context: Optional[str] = Field(
        None,
        description="Additional context about the action"
    )


class ValidateOutputSchema(BaseModel):
    """Input schema for validating agent outputs before returning to user."""

    output: str = Field(
        ...,
        description="The output content to validate"
    )
    output_type: str = Field(
        default="text",
        description="The type of output (text, code, json, markdown, etc.)"
    )
    filter_pii: bool = Field(
        True,
        description="Whether to filter personally identifiable information"
    )
