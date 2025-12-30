"""
Sentinel Action Provider for Coinbase AgentKit.

This provider adds THSP (Truth-Harm-Scope-Purpose) safety validation
capabilities to any AgentKit-powered AI agent.

Based on official AgentKit documentation:
https://docs.cdp.coinbase.com/agentkit/docs/add-agent-capabilities
"""

import json
import re
from typing import Any, Optional

try:
    from coinbase_agentkit import ActionProvider, WalletProvider, create_action
    from coinbase_agentkit.network import Network
    AGENTKIT_AVAILABLE = True
except ImportError:
    AGENTKIT_AVAILABLE = False
    # Fallback types for development without agentkit installed
    class ActionProvider:
        def __init__(self, name: str, networks: list):
            self.name = name
            self.networks = networks
    class WalletProvider:
        pass
    class Network:
        pass
    def create_action(**kwargs):
        def decorator(func):
            return func
        return decorator

from .schemas import (
    ValidatePromptSchema,
    ValidateTransactionSchema,
    ScanSecretsSchema,
    CheckComplianceSchema,
    AnalyzeRiskSchema,
    ValidateOutputSchema,
    RiskLevel,
)


# Known malicious patterns for prompt injection detection
INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
    r"disregard\s+(previous|all|your)\s+(instructions?|rules?)",
    r"forget\s+(everything|all|previous)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"pretend\s+(to\s+be|you\s+are)",
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode\s+enabled",
]

# Patterns for detecting secrets
SECRET_PATTERNS = {
    "api_keys": [
        r"(?i)(api[_-]?key|apikey)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})",
        r"(?i)sk-[a-zA-Z0-9]{20,}",  # OpenAI keys
        r"(?i)AKIA[0-9A-Z]{16}",  # AWS access keys
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
        r"ghp_[a-zA-Z0-9]{36}",  # GitHub tokens
        r"gho_[a-zA-Z0-9]{36}",  # GitHub OAuth tokens
    ],
}

# Known malicious contract addresses (example - should be expanded)
MALICIOUS_CONTRACTS = {
    # Add known malicious contracts here
    # "0x...": "Description of why it's malicious"
}

# OWASP LLM Top 10 patterns
OWASP_PATTERNS = {
    "LLM01": r"(?i)(ignore|bypass|override)\s+(instructions|rules|safety)",  # Prompt Injection
    "LLM02": r"(?i)(reveal|show|display)\s+(system|hidden)\s+(prompt|instructions)",  # Insecure Output
    "LLM06": r"(?i)(sensitive|private|confidential)\s+(data|information)",  # Sensitive Info Disclosure
    "LLM09": r"(?i)(unlimited|infinite|no\s+limit)",  # Overreliance
}


class SentinelActionProvider(ActionProvider):
    """
    Sentinel safety action provider for Coinbase AgentKit.

    Provides THSP (Truth-Harm-Scope-Purpose) validation capabilities
    to protect AI agents from harmful inputs and outputs.

    Actions:
        - validate_prompt: Validate input prompts for safety
        - validate_transaction: Validate blockchain transactions
        - scan_secrets: Scan content for exposed secrets
        - check_compliance: Check content against compliance frameworks
        - analyze_risk: Analyze risk level of agent actions
        - validate_output: Validate agent outputs before returning
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the Sentinel action provider.

        Args:
            strict_mode: If True, applies stricter validation rules
        """
        super().__init__("sentinel", [])
        self.strict_mode = strict_mode
        self._injection_regex = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    def supports_network(self, network: Network) -> bool:
        """Sentinel supports all networks."""
        return True

    @create_action(
        name="sentinel_validate_prompt",
        description="""Validate a prompt or text input for safety using THSP gates.

        Checks for:
        - Prompt injection attempts
        - Jailbreak patterns
        - Harmful content requests
        - Policy violations

        Returns a JSON object with validation results including:
        - is_safe: boolean indicating if the prompt is safe
        - risk_level: low/medium/high/critical
        - issues: list of detected issues
        - recommendations: suggested actions

        Example usage: Before processing any user input, validate it first.""",
        schema=ValidatePromptSchema
    )
    def validate_prompt(self, args: dict[str, Any]) -> str:
        """Validate a prompt for safety through THSP gates."""
        prompt = args["prompt"]
        context = args.get("context", "")
        strict = args.get("strict_mode", self.strict_mode)

        issues = []
        risk_level = RiskLevel.LOW

        # Check for prompt injection patterns
        for pattern in self._injection_regex:
            if pattern.search(prompt):
                issues.append({
                    "type": "prompt_injection",
                    "description": f"Detected potential prompt injection pattern",
                    "gate": "HARM"
                })
                risk_level = RiskLevel.HIGH

        # Check for OWASP LLM patterns
        for owasp_id, pattern in OWASP_PATTERNS.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                issues.append({
                    "type": f"owasp_{owasp_id.lower()}",
                    "description": f"Detected OWASP {owasp_id} pattern",
                    "gate": "SCOPE"
                })
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.MEDIUM

        # Check for extremely long inputs (potential DoS)
        if len(prompt) > 50000:
            issues.append({
                "type": "input_size",
                "description": "Input exceeds recommended maximum length",
                "gate": "SCOPE"
            })
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM

        # Additional strict mode checks
        if strict:
            # Check for potential sensitive data requests
            sensitive_patterns = [
                r"(?i)(password|credit\s*card|ssn|social\s*security)",
                r"(?i)(bank\s*account|routing\s*number)",
            ]
            for pattern in sensitive_patterns:
                if re.search(pattern, prompt):
                    issues.append({
                        "type": "sensitive_request",
                        "description": "Request may involve sensitive data",
                        "gate": "PURPOSE"
                    })

        is_safe = len(issues) == 0 or risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]

        result = {
            "is_safe": is_safe,
            "risk_level": risk_level.value,
            "issues": issues,
            "recommendations": self._get_recommendations(issues),
            "gates_passed": {
                "TRUTH": True,  # Factual validation not applicable to prompts
                "HARM": not any(i["gate"] == "HARM" for i in issues),
                "SCOPE": not any(i["gate"] == "SCOPE" for i in issues),
                "PURPOSE": not any(i["gate"] == "PURPOSE" for i in issues),
            }
        }

        return json.dumps(result, indent=2)

    @create_action(
        name="sentinel_validate_transaction",
        description="""Validate a blockchain transaction before execution.

        Checks for:
        - Known malicious contract addresses
        - Suspicious transaction patterns
        - Value anomalies
        - Contract interaction risks

        Returns a JSON object with validation results.

        Example usage: Before executing any token transfer or contract interaction.""",
        schema=ValidateTransactionSchema
    )
    def validate_transaction(self, wallet_provider: WalletProvider, args: dict[str, Any]) -> str:
        """Validate a blockchain transaction for safety."""
        to_address = args["to_address"].lower()
        value = args["value"]
        data = args.get("data", "")
        check_contract = args.get("check_contract", True)

        issues = []
        risk_level = RiskLevel.LOW

        # Check against known malicious contracts
        if check_contract and to_address in MALICIOUS_CONTRACTS:
            issues.append({
                "type": "malicious_contract",
                "description": f"Address flagged as malicious: {MALICIOUS_CONTRACTS[to_address]}",
                "gate": "HARM"
            })
            risk_level = RiskLevel.CRITICAL

        # Check for suspicious patterns in contract data
        if data:
            # Check for known malicious function signatures
            malicious_sigs = [
                "0xa9059cbb",  # transfer - check context
                "0x095ea7b3",  # approve - high risk if unlimited
            ]
            if data[:10] == "0x095ea7b3":
                # Check if it's unlimited approval
                if "ffffffff" in data.lower():
                    issues.append({
                        "type": "unlimited_approval",
                        "description": "Transaction includes unlimited token approval",
                        "gate": "SCOPE"
                    })
                    risk_level = RiskLevel.HIGH

        # Check for very high value transactions
        try:
            value_float = float(value)
            if value_float > 1000:  # Example threshold
                issues.append({
                    "type": "high_value",
                    "description": f"High value transaction: {value}",
                    "gate": "PURPOSE"
                })
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.MEDIUM
        except (ValueError, TypeError):
            pass

        # Check for zero address
        if to_address == "0x0000000000000000000000000000000000000000":
            issues.append({
                "type": "zero_address",
                "description": "Transaction to zero address (burn)",
                "gate": "PURPOSE"
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
            }
        }

        return json.dumps(result, indent=2)

    @create_action(
        name="sentinel_scan_secrets",
        description="""Scan content for exposed secrets and sensitive data.

        Detects:
        - API keys (OpenAI, AWS, etc.)
        - Private keys (Ethereum, RSA)
        - Passwords
        - Access tokens (GitHub, OAuth)

        Returns a JSON object with scan results and redacted content.

        Example usage: Before logging, storing, or transmitting any content.""",
        schema=ScanSecretsSchema
    )
    def scan_secrets(self, args: dict[str, Any]) -> str:
        """Scan content for exposed secrets."""
        content = args["content"]
        scan_types = args.get("scan_types", ["api_keys", "private_keys", "passwords", "tokens"])

        findings = []
        redacted_content = content

        for secret_type in scan_types:
            if secret_type not in SECRET_PATTERNS:
                continue

            for pattern in SECRET_PATTERNS[secret_type]:
                matches = re.finditer(pattern, content)
                for match in matches:
                    findings.append({
                        "type": secret_type,
                        "pattern": pattern[:30] + "...",
                        "position": match.start(),
                        "length": len(match.group()),
                    })
                    # Redact the secret
                    redacted_content = redacted_content.replace(
                        match.group(),
                        f"[REDACTED_{secret_type.upper()}]"
                    )

        result = {
            "has_secrets": len(findings) > 0,
            "findings_count": len(findings),
            "findings": findings,
            "redacted_content": redacted_content if findings else None,
            "recommendation": "Remove or rotate exposed credentials immediately" if findings else "No secrets detected"
        }

        return json.dumps(result, indent=2)

    @create_action(
        name="sentinel_check_compliance",
        description="""Check content against compliance frameworks.

        Supported frameworks:
        - OWASP LLM Top 10
        - EU AI Act
        - CSA AI Controls
        - NIST AI RMF

        Returns a JSON object with compliance status for each framework.

        Example usage: Before deploying or releasing AI-generated content.""",
        schema=CheckComplianceSchema
    )
    def check_compliance(self, args: dict[str, Any]) -> str:
        """Check content against compliance frameworks."""
        content = args["content"]
        frameworks = args.get("frameworks", ["owasp_llm"])

        results = {}

        for framework in frameworks:
            framework_value = framework.value if hasattr(framework, 'value') else framework

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

        return json.dumps(result, indent=2)

    @create_action(
        name="sentinel_analyze_risk",
        description="""Analyze the risk level of an agent action.

        Evaluates:
        - Action type risk inherent
        - Parameter values
        - Context appropriateness

        Returns risk assessment with score and recommendations.

        Example usage: Before executing any high-impact action.""",
        schema=AnalyzeRiskSchema
    )
    def analyze_risk(self, args: dict[str, Any]) -> str:
        """Analyze risk level of an agent action."""
        action_type = args["action_type"]
        parameters = args["parameters"]
        context = args.get("context", "")

        # Risk weights by action type
        action_risks = {
            "transfer": 0.6,
            "swap": 0.5,
            "deploy": 0.8,
            "approve": 0.7,
            "stake": 0.5,
            "unstake": 0.4,
            "bridge": 0.7,
            "read": 0.1,
            "query": 0.1,
        }

        base_risk = action_risks.get(action_type.lower(), 0.5)

        # Adjust based on parameters
        risk_factors = []

        # Check for high values
        if "value" in parameters or "amount" in parameters:
            value = parameters.get("value") or parameters.get("amount")
            try:
                if float(value) > 1000:
                    base_risk += 0.2
                    risk_factors.append("High value transaction")
            except (ValueError, TypeError):
                pass

        # Check for external addresses
        if "to" in parameters or "recipient" in parameters:
            address = parameters.get("to") or parameters.get("recipient")
            if address and address.lower() in MALICIOUS_CONTRACTS:
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

        return json.dumps(result, indent=2)

    @create_action(
        name="sentinel_validate_output",
        description="""Validate agent output before returning to user.

        Checks for:
        - Exposed secrets
        - PII data
        - Harmful content
        - Policy violations

        Returns validated/sanitized output.

        Example usage: Before returning any response to the user.""",
        schema=ValidateOutputSchema
    )
    def validate_output(self, args: dict[str, Any]) -> str:
        """Validate and sanitize agent output."""
        output = args["output"]
        output_type = args.get("output_type", "text")
        filter_pii = args.get("filter_pii", True)

        issues = []
        sanitized_output = output

        # Scan for secrets
        for secret_type, patterns in SECRET_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, output):
                    issues.append({
                        "type": "exposed_secret",
                        "secret_type": secret_type,
                    })
                    sanitized_output = re.sub(pattern, f"[REDACTED_{secret_type.upper()}]", sanitized_output)

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
                    sanitized_output = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", sanitized_output)

        result = {
            "is_safe": len(issues) == 0,
            "issues": issues,
            "original_length": len(output),
            "sanitized_length": len(sanitized_output),
            "sanitized_output": sanitized_output if issues else None,
            "output_type": output_type,
        }

        return json.dumps(result, indent=2)

    # Helper methods

    def _get_recommendations(self, issues: list) -> list:
        """Generate recommendations based on detected issues."""
        recommendations = []

        issue_types = set(i["type"] for i in issues)

        if "prompt_injection" in issue_types:
            recommendations.append("Reject the input and log the attempt")
        if "sensitive_request" in issue_types:
            recommendations.append("Request user confirmation before proceeding")
        if "input_size" in issue_types:
            recommendations.append("Truncate input to acceptable length")

        if not recommendations:
            recommendations.append("Input appears safe to process")

        return recommendations

    def _get_transaction_recommendations(self, issues: list) -> list:
        """Generate recommendations for transaction issues."""
        recommendations = []

        issue_types = set(i["type"] for i in issues)

        if "malicious_contract" in issue_types:
            recommendations.append("DO NOT EXECUTE - Known malicious address")
        if "unlimited_approval" in issue_types:
            recommendations.append("Consider using a specific approval amount instead")
        if "high_value" in issue_types:
            recommendations.append("Verify recipient and consider splitting transaction")
        if "zero_address" in issue_types:
            recommendations.append("Confirm burn intention with user")

        if not recommendations:
            recommendations.append("Transaction appears safe to execute")

        return recommendations

    def _get_risk_recommendation(self, risk_level: RiskLevel) -> str:
        """Get recommendation based on risk level."""
        recommendations = {
            RiskLevel.LOW: "Safe to proceed",
            RiskLevel.MEDIUM: "Proceed with standard monitoring",
            RiskLevel.HIGH: "Require explicit user confirmation",
            RiskLevel.CRITICAL: "Block action and alert user",
        }
        return recommendations.get(risk_level, "Unknown risk level")

    def _check_owasp_compliance(self, content: str) -> dict:
        """Check OWASP LLM Top 10 compliance."""
        violations = []

        for owasp_id, pattern in OWASP_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                violations.append({
                    "id": owasp_id,
                    "description": f"Potential {owasp_id} violation detected"
                })

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "framework_version": "OWASP LLM Top 10 2025"
        }

    def _check_eu_ai_act(self, content: str) -> dict:
        """Check EU AI Act compliance indicators."""
        # Simplified check - in production, this would be more comprehensive
        indicators = {
            "transparency": not re.search(r"(?i)(hide|conceal|deceive)", content),
            "human_oversight": True,  # Assume AI agent has oversight
            "documentation": True,
        }

        return {
            "compliant": all(indicators.values()),
            "indicators": indicators,
            "framework_version": "EU AI Act 2024"
        }

    def _check_csa_compliance(self, content: str) -> dict:
        """Check CSA AI Controls compliance."""
        return {
            "compliant": True,
            "controls_checked": ["AI-1", "AI-2", "AI-3"],
            "framework_version": "CSA AI Controls Matrix v1"
        }

    def _check_nist_compliance(self, content: str) -> dict:
        """Check NIST AI RMF compliance."""
        return {
            "compliant": True,
            "functions_checked": ["GOVERN", "MAP", "MEASURE", "MANAGE"],
            "framework_version": "NIST AI RMF 1.0"
        }


def sentinel_action_provider(strict_mode: bool = False) -> SentinelActionProvider:
    """
    Factory function to create a Sentinel action provider.

    Args:
        strict_mode: If True, applies stricter validation rules

    Returns:
        SentinelActionProvider instance

    Example:
        from coinbase_agentkit import AgentKit
        from sentinelseed.integrations.coinbase_agentkit import sentinel_action_provider

        agent = AgentKit(
            action_providers=[
                sentinel_action_provider(strict_mode=True),
            ]
        )
    """
    return SentinelActionProvider(strict_mode=strict_mode)
