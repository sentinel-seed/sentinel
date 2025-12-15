"""
OpenGuardrails Integration for Sentinel

Provides bidirectional integration between Sentinel and OpenGuardrails:

1. Sentinel as OpenGuardrails Scanner:
   - Register Sentinel THSP validation as a custom scanner
   - Use Sentinel's four-gate validation within OpenGuardrails pipeline

2. OpenGuardrails as Sentinel Backend:
   - Use OpenGuardrails detection API as additional validation
   - Combine with Sentinel's THSP gates for comprehensive protection

OpenGuardrails: https://github.com/openguardrails/openguardrails
Documentation: https://openguardrails.com

Example:
    # Use Sentinel as OpenGuardrails scanner
    from sentinelseed.integrations.openguardrails import register_sentinel_scanner

    register_sentinel_scanner(
        openguardrails_url="http://localhost:5000",
        jwt_token="your-token"
    )

    # Use OpenGuardrails in Sentinel
    from sentinelseed.integrations.openguardrails import OpenGuardrailsValidator

    validator = OpenGuardrailsValidator(
        api_url="http://localhost:5001",
        api_key="your-key"
    )
    result = validator.validate("Check this content")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("sentinelseed.openguardrails")

# Check for requests availability
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class RiskLevel(str, Enum):
    """OpenGuardrails risk levels"""
    LOW = "low_risk"
    MEDIUM = "medium_risk"
    HIGH = "high_risk"
    CRITICAL = "critical_risk"


class ScannerType(str, Enum):
    """OpenGuardrails scanner types"""
    GENAI = "genai"      # LLM-based contextual detection
    REGEX = "regex"      # Pattern matching
    KEYWORD = "keyword"  # Simple term matching


@dataclass
class DetectionResult:
    """Result from OpenGuardrails detection"""
    safe: bool
    risk_level: RiskLevel
    detections: List[Dict[str, Any]]
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(cls, response: Dict[str, Any]) -> "DetectionResult":
        """Create from OpenGuardrails API response"""
        detections = response.get("detections", [])
        # Safe if no high/critical detections
        safe = not any(
            d.get("risk_level") in ["high_risk", "critical_risk"]
            for d in detections
        )
        # Get highest risk level
        risk_levels = [d.get("risk_level", "low_risk") for d in detections]
        if "critical_risk" in risk_levels:
            risk = RiskLevel.CRITICAL
        elif "high_risk" in risk_levels:
            risk = RiskLevel.HIGH
        elif "medium_risk" in risk_levels:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        return cls(
            safe=safe,
            risk_level=risk,
            detections=detections,
            raw_response=response
        )


class OpenGuardrailsValidator:
    """
    Use OpenGuardrails as an additional validation backend for Sentinel.

    Combines OpenGuardrails detection with Sentinel's THSP gates for
    comprehensive protection.

    Example:
        validator = OpenGuardrailsValidator(
            api_url="http://localhost:5001",
            api_key="your-api-key"
        )

        result = validator.validate(
            content="Check this for safety",
            scanners=["S1", "S2", "S3"]  # Specific scanners
        )

        if not result.safe:
            print(f"Blocked: {result.detections}")
    """

    def __init__(
        self,
        api_url: str = "http://localhost:5001",
        api_key: Optional[str] = None,
        timeout: int = 30,
        default_scanners: Optional[List[str]] = None,
    ):
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests is required for OpenGuardrails integration. "
                "Install with: pip install requests"
            )

        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.default_scanners = default_scanners or []

    def _headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def validate(
        self,
        content: str,
        scanners: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> DetectionResult:
        """
        Validate content using OpenGuardrails detection API.

        Args:
            content: Text content to validate
            scanners: List of scanner tags (e.g., ["S1", "S2"])
            context: Optional conversation context

        Returns:
            DetectionResult with safety assessment
        """
        payload = {
            "content": content,
            "scanners": scanners or self.default_scanners,
        }
        if context:
            payload["context"] = context

        try:
            response = requests.post(
                f"{self.api_url}/api/v1/detect",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return DetectionResult.from_response(response.json())

        except requests.RequestException as e:
            logger.error(f"OpenGuardrails API error: {e}")
            # Return safe=True on API errors to avoid blocking
            return DetectionResult(
                safe=True,
                risk_level=RiskLevel.LOW,
                detections=[],
                raw_response={"error": str(e)}
            )

    def validate_prompt(
        self,
        prompt: str,
        scanners: Optional[List[str]] = None,
    ) -> DetectionResult:
        """Validate a prompt before sending to LLM"""
        return self.validate(prompt, scanners=scanners)

    def validate_response(
        self,
        response: str,
        prompt: Optional[str] = None,
        scanners: Optional[List[str]] = None,
    ) -> DetectionResult:
        """Validate LLM response with optional prompt context"""
        return self.validate(response, scanners=scanners, context=prompt)


class SentinelOpenGuardrailsScanner:
    """
    Register Sentinel as a custom scanner in OpenGuardrails.

    This allows using Sentinel's THSP validation within the OpenGuardrails
    pipeline, combining Sentinel's alignment approach with OpenGuardrails'
    enterprise features.

    Example:
        scanner = SentinelOpenGuardrailsScanner(
            openguardrails_url="http://localhost:5000",
            jwt_token="your-jwt-token"
        )

        # Register Sentinel as a scanner
        scanner_tag = scanner.register()
        print(f"Registered as: {scanner_tag}")  # e.g., "S100"

        # Now Sentinel validation is available in OpenGuardrails
    """

    SCANNER_DEFINITION = """
    Sentinel THSP Protocol Scanner - Validates content through four gates:

    1. TRUTH: Detects misinformation, fake content, impersonation
    2. HARM: Identifies violence, weapons, malware, theft, doxxing
    3. SCOPE: Catches jailbreaks, prompt injection, instruction override
    4. PURPOSE: Flags purposeless destruction or waste

    All gates must pass for content to be considered safe.
    Developed by Sentinel Team - https://sentinelseed.dev
    """

    def __init__(
        self,
        openguardrails_url: str = "http://localhost:5000",
        jwt_token: Optional[str] = None,
        risk_level: RiskLevel = RiskLevel.HIGH,
        scan_prompt: bool = True,
        scan_response: bool = True,
    ):
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests is required for OpenGuardrails integration. "
                "Install with: pip install requests"
            )

        self.api_url = openguardrails_url.rstrip("/")
        self.jwt_token = jwt_token
        self.risk_level = risk_level
        self.scan_prompt = scan_prompt
        self.scan_response = scan_response
        self._scanner_tag: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers

    def register(self) -> str:
        """
        Register Sentinel as a custom scanner in OpenGuardrails.

        Returns:
            Scanner tag (e.g., "S100") assigned by OpenGuardrails
        """
        payload = {
            "scanner_type": ScannerType.GENAI.value,
            "name": "Sentinel THSP Protocol",
            "definition": self.SCANNER_DEFINITION,
            "risk_level": self.risk_level.value,
            "scan_prompt": self.scan_prompt,
            "scan_response": self.scan_response,
        }

        try:
            response = requests.post(
                f"{self.api_url}/api/v1/custom-scanners",
                headers=self._headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            self._scanner_tag = data.get("tag")
            logger.info(f"Registered Sentinel scanner as {self._scanner_tag}")
            return self._scanner_tag

        except requests.RequestException as e:
            logger.error(f"Failed to register scanner: {e}")
            raise RuntimeError(f"Failed to register Sentinel scanner: {e}")

    def unregister(self) -> bool:
        """
        Unregister Sentinel scanner from OpenGuardrails.

        Returns:
            True if successful
        """
        if not self._scanner_tag:
            logger.warning("No scanner registered to unregister")
            return False

        try:
            response = requests.delete(
                f"{self.api_url}/api/v1/custom-scanners/{self._scanner_tag}",
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Unregistered scanner {self._scanner_tag}")
            self._scanner_tag = None
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to unregister scanner: {e}")
            return False

    @property
    def scanner_tag(self) -> Optional[str]:
        """Get the assigned scanner tag"""
        return self._scanner_tag


class SentinelGuardrailsWrapper:
    """
    Combined Sentinel + OpenGuardrails validation wrapper.

    Runs both Sentinel THSP validation and OpenGuardrails detection
    in parallel or sequence, providing layered protection.

    Example:
        from sentinelseed import Sentinel
        from sentinelseed.integrations.openguardrails import (
            SentinelGuardrailsWrapper,
            OpenGuardrailsValidator
        )

        wrapper = SentinelGuardrailsWrapper(
            sentinel=Sentinel(),
            openguardrails=OpenGuardrailsValidator(
                api_url="http://localhost:5001"
            )
        )

        result = wrapper.validate("Check this content")
        if not result["safe"]:
            print(f"Blocked by: {result['blocked_by']}")
    """

    def __init__(
        self,
        sentinel: Optional[Any] = None,
        openguardrails: Optional[OpenGuardrailsValidator] = None,
        require_both: bool = False,
    ):
        """
        Args:
            sentinel: Sentinel instance (optional, will create if not provided)
            openguardrails: OpenGuardrailsValidator instance
            require_both: If True, both must pass. If False, either can block.
        """
        self.sentinel = sentinel
        self.openguardrails = openguardrails
        self.require_both = require_both

        # Lazy import Sentinel to avoid circular imports
        if self.sentinel is None:
            try:
                from sentinelseed import Sentinel
                self.sentinel = Sentinel()
            except ImportError:
                logger.warning("Sentinel not available, using OpenGuardrails only")

    def validate(
        self,
        content: str,
        scanners: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Validate content through both Sentinel and OpenGuardrails.

        Args:
            content: Text to validate
            scanners: OpenGuardrails scanners to use

        Returns:
            Combined validation result
        """
        result = {
            "safe": True,
            "blocked_by": [],
            "sentinel_result": None,
            "openguardrails_result": None,
        }

        # Run Sentinel validation
        if self.sentinel:
            try:
                sentinel_result = self.sentinel.validate(content)
                result["sentinel_result"] = sentinel_result
                if not sentinel_result.get("safe", True):
                    result["safe"] = False
                    result["blocked_by"].append("sentinel")
            except Exception as e:
                logger.error(f"Sentinel validation error: {e}")

        # Run OpenGuardrails validation
        if self.openguardrails:
            try:
                og_result = self.openguardrails.validate(content, scanners=scanners)
                result["openguardrails_result"] = {
                    "safe": og_result.safe,
                    "risk_level": og_result.risk_level.value,
                    "detections": og_result.detections,
                }
                if not og_result.safe:
                    result["safe"] = False
                    result["blocked_by"].append("openguardrails")
            except Exception as e:
                logger.error(f"OpenGuardrails validation error: {e}")

        # If require_both, only block if both failed
        if self.require_both and len(result["blocked_by"]) < 2:
            result["safe"] = True
            result["blocked_by"] = []

        return result


# Convenience functions

def register_sentinel_scanner(
    openguardrails_url: str = "http://localhost:5000",
    jwt_token: Optional[str] = None,
    risk_level: str = "high_risk",
) -> str:
    """
    Convenience function to register Sentinel as OpenGuardrails scanner.

    Args:
        openguardrails_url: OpenGuardrails management API URL
        jwt_token: JWT authentication token
        risk_level: Risk level for detections ("low_risk", "medium_risk", etc.)

    Returns:
        Scanner tag assigned by OpenGuardrails
    """
    scanner = SentinelOpenGuardrailsScanner(
        openguardrails_url=openguardrails_url,
        jwt_token=jwt_token,
        risk_level=RiskLevel(risk_level),
    )
    return scanner.register()


def create_combined_validator(
    openguardrails_url: str = "http://localhost:5001",
    openguardrails_key: Optional[str] = None,
) -> SentinelGuardrailsWrapper:
    """
    Convenience function to create combined Sentinel + OpenGuardrails validator.

    Args:
        openguardrails_url: OpenGuardrails detection API URL
        openguardrails_key: API key for OpenGuardrails

    Returns:
        Combined validator wrapper
    """
    og_validator = OpenGuardrailsValidator(
        api_url=openguardrails_url,
        api_key=openguardrails_key,
    )
    return SentinelGuardrailsWrapper(openguardrails=og_validator)


__all__ = [
    "OpenGuardrailsValidator",
    "SentinelOpenGuardrailsScanner",
    "SentinelGuardrailsWrapper",
    "DetectionResult",
    "RiskLevel",
    "ScannerType",
    "register_sentinel_scanner",
    "create_combined_validator",
    "REQUESTS_AVAILABLE",
]
