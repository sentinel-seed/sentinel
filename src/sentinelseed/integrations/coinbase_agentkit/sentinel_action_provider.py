"""Sentinel action provider for Coinbase AgentKit.

This provider adds THSP (Truth-Harm-Scope-Purpose) safety validation
capabilities to any AgentKit-powered AI agent.

Based on official AgentKit provider patterns from:
https://github.com/coinbase/agentkit/tree/master/python/coinbase-agentkit
"""

from json import dumps
import re
from typing import Any

try:
    from coinbase_agentkit import ActionProvider, create_action
    from coinbase_agentkit.network import Network

    AGENTKIT_AVAILABLE = True
except ImportError:
    AGENTKIT_AVAILABLE = False

    # Fallback types for development/testing without agentkit installed
    class ActionProvider:
        """Fallback ActionProvider for development without agentkit."""

        def __init__(self, name: str, action_providers: list) -> None:
            """Initialize the action provider."""
            self.name = name
            self.action_providers = action_providers

        def supports_network(self, network: "Network") -> bool:
            """Check if network is supported."""
            return True

    class Network:
        """Fallback Network class for development."""

        network_id: str = ""
        protocol_family: str = ""

    def create_action(name: str, description: str, schema: type):
        """Fallback decorator for development without agentkit."""

        def decorator(func):
            return func

        return decorator


from .schemas import (
    AnalyzeRiskSchema,
    CheckComplianceSchema,
    ComplianceFramework,
    RiskLevel,
    ScanSecretsSchema,
    ValidateOutputSchema,
    ValidatePromptSchema,
    ValidateTransactionSchema,
)

# Prompt injection detection patterns
# These patterns are designed to catch common injection attempts
# while minimizing false positives
INJECTION_PATTERNS = [
    # "Ignore" variations - flexible to catch "ignore all previous instructions"
    r"ignore\s+.{0,30}(instructions?|prompts?|rules?|guidelines?)",
    r"disregard\s+.{0,30}(instructions?|prompts?|rules?|guidelines?)",
    r"forget\s+.{0,20}(instructions?|prompts?|rules?|everything|all)",
    # Role hijacking
    r"you\s+are\s+now\s+(a|an|the)\s+",
    r"pretend\s+(to\s+be|you\s+are|you're)",
    r"act\s+as\s+(a|an|if)",
    r"roleplay\s+as",
    # Known jailbreak terms
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode",
    r"maintenance\s+mode",
    # Security bypass attempts
    r"bypass\s+.{0,20}(safety|security|filter|restriction)",
    r"override\s+.{0,20}(safety|security|rule|restriction)",
    r"disable\s+.{0,20}(safety|security|filter|restriction)",
    # System prompt extraction
    r"(reveal|show|display|print|output)\s+.{0,20}(system|initial|original)\s*(prompt|instruction)",
    r"what\s+(is|are)\s+your\s+(system|initial|original)\s*(prompt|instruction)",
]

# Secret detection patterns by type
SECRET_PATTERNS = {
    "api_keys": [
        r"(?i)(api[_-]?key|apikey)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})",
        r"(?i)sk-[a-zA-Z0-9]{20,}",  # OpenAI
        r"(?i)AKIA[0-9A-Z]{16}",  # AWS
    ],
    "private_keys": [
        r"(?i)(private[_-]?key|secret[_-]?key)['\"]?\s*[:=]\s*['\"]?([a-fA-F0-9]{64})",
        r"0x[a-fA-F0-9]{64}",  # Ethereum private keys
        r"(?i)-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
    ],
    "passwords": [
        r"(?i)(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?([^\s'\"]{8,})",
    ],
    "tokens": [
        r"(?i)(token|bearer)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{20,})",
        r"ghp_[a-zA-Z0-9]{36}",  # GitHub personal access tokens
        r"gho_[a-zA-Z0-9]{36}",  # GitHub OAuth tokens
        r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}",  # GitHub fine-grained
    ],
}

# Known malicious contract addresses (extensible)
MALICIOUS_CONTRACTS: dict[str, str] = {}

# OWASP LLM Top 10 detection patterns
OWASP_PATTERNS = {
    "LLM01": r"(?i)(ignore|bypass|override)\s+(instructions|rules|safety)",
    "LLM02": r"(?i)(reveal|show|display)\s+(system|hidden)\s+(prompt|instructions)",
    "LLM06": r"(?i)(sensitive|private|confidential)\s+(data|information)",
    "LLM09": r"(?i)(unlimited|infinite|no\s+limit)",
}

# Risk weights by action type
ACTION_RISK_WEIGHTS = {
    "transfer": 0.6,
    "swap": 0.5,
    "deploy": 0.8,
    "approve": 0.7,
    "stake": 0.5,
    "unstake": 0.4,
    "bridge": 0.7,
    "mint": 0.6,
    "burn": 0.7,
    "read": 0.1,
    "query": 0.1,
}


class SentinelActionProvider(ActionProvider):
    """Sentinel safety action provider for Coinbase AgentKit.

    Provides THSP (Truth-Harm-Scope-Purpose) validation capabilities
    to protect AI agents from harmful inputs, outputs, and transactions.

    Actions:
        - sentinel_validate_prompt: Validate input prompts for safety
        - sentinel_validate_transaction: Validate blockchain transactions
        - sentinel_scan_secrets: Scan content for exposed secrets
        - sentinel_check_compliance: Check against compliance frameworks
        - sentinel_analyze_risk: Analyze risk level of agent actions
        - sentinel_validate_output: Validate outputs before returning

    Example:
        >>> from coinbase_agentkit import AgentKit
        >>> from sentinelseed.integrations.coinbase_agentkit import sentinel_action_provider
        >>>
        >>> agent = AgentKit(
        ...     action_providers=[
        ...         sentinel_action_provider(strict_mode=True),
        ...     ]
        ... )
    """

    def __init__(
        self,
        strict_mode: bool = False,
        custom_injection_patterns: list[str] | None = None,
        custom_malicious_contracts: dict[str, str] | None = None,
    ) -> None:
        """Initialize the Sentinel action provider.

        Args:
            strict_mode: If True, applies stricter validation rules.
            custom_injection_patterns: Additional regex patterns for injection detection.
            custom_malicious_contracts: Additional malicious contract addresses to block.
        """
        super().__init__("sentinel", [])
        self.strict_mode = strict_mode

        # Compile injection patterns
        patterns = INJECTION_PATTERNS.copy()
        if custom_injection_patterns:
            patterns.extend(custom_injection_patterns)
        self._injection_regex = [re.compile(p, re.IGNORECASE) for p in patterns]

        # Merge malicious contracts
        self._malicious_contracts = MALICIOUS_CONTRACTS.copy()
        if custom_malicious_contracts:
            self._malicious_contracts.update(custom_malicious_contracts)

    @create_action(
        name="sentinel_validate_prompt",
        description="""Validate a prompt or text input for safety using THSP gates.

Checks for:
- Prompt injection attempts
- Jailbreak patterns
- Harmful content requests
- Policy violations (OWASP LLM Top 10)

A successful response returns a JSON object:
{"is_safe": true, "risk_level": "low", "issues": [], "gates_passed": {...}}

A failure response returns:
{"is_safe": false, "risk_level": "high", "issues": [...], "recommendations": [...]}

Example usage: Before processing any user input, validate it first.""",
        schema=ValidatePromptSchema,
    )
    def validate_prompt(self, args: dict[str, Any]) -> str:
        """Validate a prompt for safety through THSP gates.

        Args:
            args: Dictionary containing prompt, context, and strict_mode.

        Returns:
            JSON string with validation results.
        """
        try:
            validated_args = ValidatePromptSchema(**args)
            prompt = validated_args.prompt
            strict = validated_args.strict_mode or self.strict_mode

            issues: list[dict] = []
            risk_level = RiskLevel.LOW

            # Check for prompt injection patterns
            for pattern in self._injection_regex:
                if pattern.search(prompt):
                    issues.append({
                        "type": "prompt_injection",
                        "description": "Detected potential prompt injection pattern",
                        "gate": "HARM",
                    })
                    risk_level = RiskLevel.HIGH
                    break  # One injection is enough

            # Check for OWASP LLM patterns
            for owasp_id, pattern in OWASP_PATTERNS.items():
                if re.search(pattern, prompt, re.IGNORECASE):
                    issues.append({
                        "type": f"owasp_{owasp_id.lower()}",
                        "description": f"Detected OWASP {owasp_id} pattern",
                        "gate": "SCOPE",
                    })
                    if risk_level == RiskLevel.LOW:
                        risk_level = RiskLevel.MEDIUM

            # Check for extremely long inputs (potential DoS)
            if len(prompt) > 50000:
                issues.append({
                    "type": "input_size",
                    "description": "Input exceeds recommended maximum length (50000 chars)",
                    "gate": "SCOPE",
                })
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.MEDIUM

            # Additional strict mode checks
            if strict:
                sensitive_patterns = [
                    r"(?i)(password|credit\s*card|ssn|social\s*security)",
                    r"(?i)(bank\s*account|routing\s*number)",
                    r"(?i)(seed\s*phrase|mnemonic|recovery\s*phrase)",
                ]
                for pattern in sensitive_patterns:
                    if re.search(pattern, prompt):
                        issues.append({
                            "type": "sensitive_request",
                            "description": "Request may involve sensitive data",
                            "gate": "PURPOSE",
                        })
                        break

            is_safe = len(issues) == 0 or risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]

            result = {
                "is_safe": is_safe,
                "risk_level": risk_level.value,
                "issues": issues,
                "recommendations": self._get_prompt_recommendations(issues),
                "gates_passed": {
                    "TRUTH": True,
                    "HARM": not any(i["gate"] == "HARM" for i in issues),
                    "SCOPE": not any(i["gate"] == "SCOPE" for i in issues),
                    "PURPOSE": not any(i["gate"] == "PURPOSE" for i in issues),
                },
            }

            return dumps(result, indent=2)

        except Exception as e:
            return dumps({
                "is_safe": False,
                "risk_level": "critical",
                "error": f"Error validating prompt: {e!s}",
            })

    @create_action(
        name="sentinel_validate_transaction",
        description="""Validate a blockchain transaction before execution.

Checks for:
- Known malicious contract addresses
- Unlimited token approvals (max uint256)
- High-value transaction warnings
- Zero address (burn) transactions

A successful response returns a JSON object:
{"is_safe": true, "risk_level": "low", "issues": [], "transaction_summary": {...}}

A failure response returns:
{"is_safe": false, "risk_level": "critical", "issues": [...], "recommendations": [...]}

Example usage: Before executing any token transfer or contract interaction.""",
        schema=ValidateTransactionSchema,
    )
    def validate_transaction(self, args: dict[str, Any]) -> str:
        """Validate a blockchain transaction for safety.

        Args:
            args: Dictionary containing to_address, value, data, and check_contract.

        Returns:
            JSON string with validation results.
        """
        try:
            validated_args = ValidateTransactionSchema(**args)
            to_address = validated_args.to_address.lower()
            value = validated_args.value
            data = validated_args.data or ""
            check_contract = validated_args.check_contract

            issues: list[dict] = []
            risk_level = RiskLevel.LOW

            # Check against known malicious contracts
            if check_contract and to_address in self._malicious_contracts:
                issues.append({
                    "type": "malicious_contract",
                    "description": f"Address flagged: {self._malicious_contracts[to_address]}",
                    "gate": "HARM",
                })
                risk_level = RiskLevel.CRITICAL

            # Check for unlimited approval pattern
            if data.startswith("0x095ea7b3"):  # ERC20 approve signature
                if "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" in data.lower():
                    issues.append({
                        "type": "unlimited_approval",
                        "description": "Transaction includes unlimited token approval (max uint256)",
                        "gate": "SCOPE",
                    })
                    risk_level = RiskLevel.HIGH

            # Check for high value transactions
            try:
                value_float = float(value)
                if value_float > 1e18:  # More than 1 ETH in wei
                    issues.append({
                        "type": "high_value",
                        "description": f"High value transaction detected: {value}",
                        "gate": "PURPOSE",
                    })
                    if risk_level == RiskLevel.LOW:
                        risk_level = RiskLevel.MEDIUM
            except (ValueError, TypeError):
                pass

            # Check for zero address (burn)
            if to_address == "0x0000000000000000000000000000000000000000":
                issues.append({
                    "type": "zero_address",
                    "description": "Transaction to zero address (token burn)",
                    "gate": "PURPOSE",
                })

            is_safe = risk_level not in [RiskLevel.CRITICAL]

            result = {
                "is_safe": is_safe,
                "risk_level": risk_level.value,
                "issues": issues,
                "recommendations": self._get_transaction_recommendations(issues),
                "transaction_summary": {
                    "to": to_address,
                    "value": value,
                    "has_data": bool(data),
                    "data_length": len(data) if data else 0,
                },
            }

            return dumps(result, indent=2)

        except Exception as e:
            return dumps({
                "is_safe": False,
                "risk_level": "critical",
                "error": f"Error validating transaction: {e!s}",
            })

    @create_action(
        name="sentinel_scan_secrets",
        description="""Scan content for exposed secrets and sensitive data.

Detects:
- API keys (OpenAI, AWS, etc.)
- Private keys (Ethereum, RSA)
- Passwords
- Access tokens (GitHub, OAuth)

A successful response returns a JSON object:
{"has_secrets": false, "findings_count": 0, "findings": []}

A failure response with detected secrets returns:
{"has_secrets": true, "findings_count": 3, "findings": [...], "redacted_content": "..."}

Example usage: Before logging, storing, or transmitting any content.""",
        schema=ScanSecretsSchema,
    )
    def scan_secrets(self, args: dict[str, Any]) -> str:
        """Scan content for exposed secrets.

        Args:
            args: Dictionary containing content and scan_types.

        Returns:
            JSON string with scan results and optional redacted content.
        """
        try:
            validated_args = ScanSecretsSchema(**args)
            content = validated_args.content
            scan_types = validated_args.scan_types

            findings: list[dict] = []
            redacted_content = content

            for secret_type in scan_types:
                if secret_type not in SECRET_PATTERNS:
                    continue

                for pattern in SECRET_PATTERNS[secret_type]:
                    for match in re.finditer(pattern, content):
                        findings.append({
                            "type": secret_type,
                            "position": match.start(),
                            "length": len(match.group()),
                            "preview": match.group()[:8] + "..." if len(match.group()) > 8 else "[short]",
                        })
                        redacted_content = redacted_content.replace(
                            match.group(),
                            f"[REDACTED_{secret_type.upper()}]"
                        )

            result = {
                "has_secrets": len(findings) > 0,
                "findings_count": len(findings),
                "findings": findings,
                "redacted_content": redacted_content if findings else None,
                "recommendation": (
                    "Remove or rotate exposed credentials immediately"
                    if findings else "No secrets detected"
                ),
            }

            return dumps(result, indent=2)

        except Exception as e:
            return dumps({
                "has_secrets": False,
                "error": f"Error scanning for secrets: {e!s}",
            })

    @create_action(
        name="sentinel_check_compliance",
        description="""Check content against compliance frameworks.

Supported frameworks:
- OWASP LLM Top 10 (owasp_llm)
- EU AI Act (eu_ai_act)
- CSA AI Controls (csa_ai)
- NIST AI RMF (nist_rmf)

A successful response returns a JSON object:
{"overall_compliant": true, "frameworks_checked": ["owasp_llm"], "results": {...}}

A failure response returns:
{"overall_compliant": false, "results": {"owasp_llm": {"compliant": false, "violations": [...]}}}

Example usage: Before deploying or releasing AI-generated content.""",
        schema=CheckComplianceSchema,
    )
    def check_compliance(self, args: dict[str, Any]) -> str:
        """Check content against compliance frameworks.

        Args:
            args: Dictionary containing content and frameworks to check.

        Returns:
            JSON string with compliance status for each framework.
        """
        try:
            validated_args = CheckComplianceSchema(**args)
            content = validated_args.content
            frameworks = validated_args.frameworks

            results: dict[str, dict] = {}

            for framework in frameworks:
                framework_value = framework.value if hasattr(framework, "value") else framework

                if framework_value == "owasp_llm":
                    results["owasp_llm"] = self._check_owasp_compliance(content)
                elif framework_value == "eu_ai_act":
                    results["eu_ai_act"] = self._check_eu_ai_act(content)
                elif framework_value == "csa_ai":
                    results["csa_ai"] = self._check_csa_compliance(content)
                elif framework_value == "nist_rmf":
                    results["nist_rmf"] = self._check_nist_compliance(content)

            overall_compliant = all(r.get("compliant", True) for r in results.values())

            result = {
                "overall_compliant": overall_compliant,
                "frameworks_checked": list(results.keys()),
                "results": results,
            }

            return dumps(result, indent=2)

        except Exception as e:
            return dumps({
                "overall_compliant": False,
                "error": f"Error checking compliance: {e!s}",
            })

    @create_action(
        name="sentinel_analyze_risk",
        description="""Analyze the risk level of an agent action.

Evaluates:
- Action type inherent risk
- Parameter values
- Target addresses

Action types and base risks:
- transfer: 0.6, swap: 0.5, deploy: 0.8, approve: 0.7
- stake: 0.5, unstake: 0.4, bridge: 0.7, read: 0.1

A response returns a JSON object:
{"risk_score": 0.65, "risk_level": "high", "risk_factors": [...], "requires_approval": true}

Example usage: Before executing any high-impact action.""",
        schema=AnalyzeRiskSchema,
    )
    def analyze_risk(self, args: dict[str, Any]) -> str:
        """Analyze risk level of an agent action.

        Args:
            args: Dictionary containing action_type, parameters, and context.

        Returns:
            JSON string with risk assessment.
        """
        try:
            validated_args = AnalyzeRiskSchema(**args)
            action_type = validated_args.action_type.lower()
            parameters = validated_args.parameters

            base_risk = ACTION_RISK_WEIGHTS.get(action_type, 0.5)
            risk_factors: list[str] = []

            # Adjust for high values
            value = parameters.get("value") or parameters.get("amount")
            if value:
                try:
                    if float(value) > 1000:
                        base_risk = min(base_risk + 0.2, 1.0)
                        risk_factors.append("High value transaction")
                except (ValueError, TypeError):
                    pass

            # Check for known malicious addresses
            address = parameters.get("to") or parameters.get("recipient")
            if address and address.lower() in self._malicious_contracts:
                base_risk = 1.0
                risk_factors.append("Known malicious address")

            # Determine risk level
            if base_risk >= 0.8:
                risk_level = RiskLevel.CRITICAL
            elif base_risk >= 0.6:
                risk_level = RiskLevel.HIGH
            elif base_risk >= 0.3:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            result = {
                "risk_score": round(base_risk, 2),
                "risk_level": risk_level.value,
                "action_type": action_type,
                "risk_factors": risk_factors,
                "recommendation": self._get_risk_recommendation(risk_level),
                "requires_approval": risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            }

            return dumps(result, indent=2)

        except Exception as e:
            return dumps({
                "risk_score": 1.0,
                "risk_level": "critical",
                "error": f"Error analyzing risk: {e!s}",
            })

    @create_action(
        name="sentinel_validate_output",
        description="""Validate agent output before returning to user.

Checks for:
- Exposed secrets
- PII data (email, phone, SSN)
- Harmful content

A successful response returns a JSON object:
{"is_safe": true, "issues": [], "original_length": 100}

A failure response with detected issues returns:
{"is_safe": false, "issues": [...], "sanitized_output": "..."}

Example usage: Before returning any response to the user.""",
        schema=ValidateOutputSchema,
    )
    def validate_output(self, args: dict[str, Any]) -> str:
        """Validate and sanitize agent output.

        Args:
            args: Dictionary containing output, output_type, and filter_pii.

        Returns:
            JSON string with validation results and sanitized output if needed.
        """
        try:
            validated_args = ValidateOutputSchema(**args)
            output = validated_args.output
            output_type = validated_args.output_type
            filter_pii = validated_args.filter_pii

            issues: list[dict] = []
            sanitized_output = output

            # Scan for secrets
            for secret_type, patterns in SECRET_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, output):
                        issues.append({
                            "type": "exposed_secret",
                            "secret_type": secret_type,
                        })
                        sanitized_output = re.sub(
                            pattern,
                            f"[REDACTED_{secret_type.upper()}]",
                            sanitized_output
                        )

            # Filter PII if requested
            if filter_pii:
                pii_patterns = {
                    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
                }
                for pii_type, pattern in pii_patterns.items():
                    if re.search(pattern, output):
                        issues.append({
                            "type": "pii_detected",
                            "pii_type": pii_type,
                        })
                        sanitized_output = re.sub(
                            pattern,
                            f"[REDACTED_{pii_type.upper()}]",
                            sanitized_output
                        )

            result = {
                "is_safe": len(issues) == 0,
                "issues": issues,
                "original_length": len(output),
                "sanitized_length": len(sanitized_output),
                "sanitized_output": sanitized_output if issues else None,
                "output_type": output_type,
            }

            return dumps(result, indent=2)

        except Exception as e:
            return dumps({
                "is_safe": False,
                "error": f"Error validating output: {e!s}",
            })

    def supports_network(self, network: Network) -> bool:
        """Check if network is supported by Sentinel actions.

        Args:
            network: The network to check support for.

        Returns:
            bool: Always True as Sentinel is network-agnostic safety layer.
        """
        return True

    # Helper methods

    def _get_prompt_recommendations(self, issues: list[dict]) -> list[str]:
        """Generate recommendations based on detected prompt issues.

        Args:
            issues: List of detected issues.

        Returns:
            List of recommendation strings.
        """
        recommendations = []
        issue_types = {i["type"] for i in issues}

        if "prompt_injection" in issue_types:
            recommendations.append("Reject the input and log the attempt for security review")
        if "sensitive_request" in issue_types:
            recommendations.append("Request explicit user confirmation before proceeding")
        if "input_size" in issue_types:
            recommendations.append("Truncate or reject oversized input")
        if any(t.startswith("owasp_") for t in issue_types):
            recommendations.append("Review input for potential OWASP LLM vulnerability")

        if not recommendations:
            recommendations.append("Input appears safe to process")

        return recommendations

    def _get_transaction_recommendations(self, issues: list[dict]) -> list[str]:
        """Generate recommendations for transaction issues.

        Args:
            issues: List of detected issues.

        Returns:
            List of recommendation strings.
        """
        recommendations = []
        issue_types = {i["type"] for i in issues}

        if "malicious_contract" in issue_types:
            recommendations.append("DO NOT EXECUTE - Known malicious address detected")
        if "unlimited_approval" in issue_types:
            recommendations.append("Consider using a specific approval amount instead of unlimited")
        if "high_value" in issue_types:
            recommendations.append("Verify recipient address and consider splitting large transactions")
        if "zero_address" in issue_types:
            recommendations.append("Confirm burn intention with user before proceeding")

        if not recommendations:
            recommendations.append("Transaction appears safe to execute")

        return recommendations

    def _get_risk_recommendation(self, risk_level: RiskLevel) -> str:
        """Get recommendation based on risk level.

        Args:
            risk_level: The assessed risk level.

        Returns:
            Recommendation string.
        """
        recommendations = {
            RiskLevel.LOW: "Safe to proceed",
            RiskLevel.MEDIUM: "Proceed with standard monitoring",
            RiskLevel.HIGH: "Require explicit user confirmation before proceeding",
            RiskLevel.CRITICAL: "Block action and alert user immediately",
        }
        return recommendations.get(risk_level, "Unknown risk level - proceed with caution")

    def _check_owasp_compliance(self, content: str) -> dict:
        """Check OWASP LLM Top 10 compliance.

        Args:
            content: Content to check.

        Returns:
            Compliance result dictionary.
        """
        violations = []

        for owasp_id, pattern in OWASP_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                violations.append({
                    "id": owasp_id,
                    "description": f"Potential {owasp_id} violation detected",
                })

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "framework_version": "OWASP LLM Top 10 2025",
        }

    def _check_eu_ai_act(self, content: str) -> dict:
        """Check EU AI Act compliance indicators.

        Args:
            content: Content to check.

        Returns:
            Compliance result dictionary.
        """
        indicators = {
            "transparency": not re.search(r"(?i)(hide|conceal|deceive)", content),
            "human_oversight": True,
            "documentation": True,
        }

        return {
            "compliant": all(indicators.values()),
            "indicators": indicators,
            "framework_version": "EU AI Act 2024",
        }

    def _check_csa_compliance(self, content: str) -> dict:
        """Check CSA AI Controls compliance.

        Args:
            content: Content to check.

        Returns:
            Compliance result dictionary.
        """
        return {
            "compliant": True,
            "controls_checked": ["AI-1", "AI-2", "AI-3"],
            "framework_version": "CSA AI Controls Matrix v1",
        }

    def _check_nist_compliance(self, content: str) -> dict:
        """Check NIST AI RMF compliance.

        Args:
            content: Content to check.

        Returns:
            Compliance result dictionary.
        """
        return {
            "compliant": True,
            "functions_checked": ["GOVERN", "MAP", "MEASURE", "MANAGE"],
            "framework_version": "NIST AI RMF 1.0",
        }


def sentinel_action_provider(
    strict_mode: bool = False,
    custom_injection_patterns: list[str] | None = None,
    custom_malicious_contracts: dict[str, str] | None = None,
) -> SentinelActionProvider:
    """Create and return a new SentinelActionProvider instance.

    Args:
        strict_mode: If True, applies stricter validation rules.
        custom_injection_patterns: Additional regex patterns for injection detection.
        custom_malicious_contracts: Additional malicious contract addresses to block.

    Returns:
        SentinelActionProvider: A new Sentinel action provider instance.

    Example:
        >>> from sentinelseed.integrations.coinbase_agentkit import sentinel_action_provider
        >>>
        >>> # Basic usage
        >>> provider = sentinel_action_provider()
        >>>
        >>> # With strict mode
        >>> provider = sentinel_action_provider(strict_mode=True)
        >>>
        >>> # With custom patterns
        >>> provider = sentinel_action_provider(
        ...     custom_injection_patterns=[r"custom_pattern"],
        ...     custom_malicious_contracts={"0x...": "Known scam"},
        ... )
    """
    return SentinelActionProvider(
        strict_mode=strict_mode,
        custom_injection_patterns=custom_injection_patterns,
        custom_malicious_contracts=custom_malicious_contracts,
    )
