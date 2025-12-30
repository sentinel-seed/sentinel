"""
DeFi Risk Assessment for Coinbase AgentKit.

Provides risk assessment for DeFi protocol interactions including:
- Compound (lending/borrowing)
- Aave (lending/borrowing)
- Morpho (lending optimization)
- Superfluid (token streaming)
- WOW (token creation/trading)

Risk factors considered:
- Protocol maturity and audit status
- Liquidation risk for lending/borrowing
- Impermanent loss for liquidity provision
- Smart contract risk
- Market volatility

KNOWN LIMITATION - ARBITRARY RISK SCORES
=========================================
The risk scores in this module (protocol base risks, action weights, thresholds)
are heuristic values chosen based on general industry knowledge, NOT derived from:
- Empirical analysis of historical exploits/hacks
- Statistical analysis of liquidation events
- Formal risk assessment methodologies (S&P, Moody's, etc.)
- Peer-reviewed research on DeFi risk

Current values are reasonable defaults but should be calibrated based on:
- Real-world incident data (DeFi Llama, Rekt News)
- Protocol-specific audit reports
- TVL and time-in-market metrics
- Insurance coverage availability

TODO: Implement data-driven risk scoring based on:
- https://defillama.com/hacks (historical exploit data)
- Protocol audit status from Trail of Bits, OpenZeppelin, etc.
- Real liquidation statistics from on-chain data
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config import DEFI_PROTOCOL_RISK, RiskLevel

logger = logging.getLogger("sentinelseed.coinbase.defi")


class DeFiProtocol(Enum):
    """Supported DeFi protocols in AgentKit."""

    COMPOUND = "compound"
    AAVE = "aave"
    MORPHO = "morpho"
    SUPERFLUID = "superfluid"
    UNISWAP = "uniswap"
    WOW = "wow"
    UNKNOWN = "unknown"


class DeFiActionType(Enum):
    """Types of DeFi actions."""

    # Lending/Borrowing
    SUPPLY = "supply"
    WITHDRAW = "withdraw"
    BORROW = "borrow"
    REPAY = "repay"

    # Trading
    SWAP = "swap"
    TRADE = "trade"

    # Liquidity
    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"

    # Token creation
    CREATE_TOKEN = "create_token"
    BUY_TOKEN = "buy_token"
    SELL_TOKEN = "sell_token"

    # Streaming
    CREATE_FLOW = "create_flow"
    DELETE_FLOW = "delete_flow"

    # Other
    GET_PORTFOLIO = "get_portfolio"
    GET_FLOW = "get_flow"
    OTHER = "other"


# Risk weights for different action types
# NOTE: These weights are HEURISTIC values, not empirically derived.
# See module docstring for known limitations.
ACTION_RISK_WEIGHTS: Dict[DeFiActionType, float] = {
    # High risk - potential for significant loss
    DeFiActionType.BORROW: 1.5,        # Arbitrary: liquidation risk
    DeFiActionType.ADD_LIQUIDITY: 1.3, # Arbitrary: impermanent loss risk
    DeFiActionType.CREATE_TOKEN: 1.4,  # Arbitrary: rug pull/scam risk
    DeFiActionType.CREATE_FLOW: 1.2,   # Arbitrary: stream drain risk

    # Medium risk - direct value transfer
    DeFiActionType.SUPPLY: 1.0,        # Baseline (1.0)
    DeFiActionType.SWAP: 1.0,          # Baseline
    DeFiActionType.TRADE: 1.0,         # Baseline
    DeFiActionType.BUY_TOKEN: 1.1,     # Arbitrary: slightly higher
    DeFiActionType.SELL_TOKEN: 1.1,    # Arbitrary: slightly higher

    # Lower risk - recovering assets
    DeFiActionType.WITHDRAW: 0.8,           # Arbitrary: lower risk
    DeFiActionType.REPAY: 0.8,              # Arbitrary: lower risk
    DeFiActionType.REMOVE_LIQUIDITY: 0.9,   # Arbitrary: lower risk
    DeFiActionType.DELETE_FLOW: 0.7,        # Arbitrary: lower risk

    # Read-only - no risk
    DeFiActionType.GET_PORTFOLIO: 0.0,
    DeFiActionType.GET_FLOW: 0.0,
    DeFiActionType.OTHER: 0.5,
}


@dataclass
class DeFiRiskAssessment:
    """
    Result of DeFi risk assessment.

    Attributes:
        protocol: The DeFi protocol involved
        action_type: Type of action being performed
        risk_level: Overall risk level
        risk_score: Numeric risk score (0-100)
        risk_factors: Identified risk factors
        recommendations: Risk mitigation recommendations
        warnings: Critical warnings
        details: Additional assessment details
    """

    protocol: DeFiProtocol
    action_type: DeFiActionType
    risk_level: RiskLevel
    risk_score: float
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_risk(self) -> bool:
        """Check if this is a high-risk operation."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


class DeFiValidator:
    """
    DeFi risk assessment validator.

    Analyzes DeFi operations for potential risks and provides
    recommendations for safer execution.

    Example:
        from sentinelseed.integrations.coinbase.validators import DeFiValidator

        validator = DeFiValidator()

        # Assess a borrow operation
        assessment = validator.assess(
            protocol="compound",
            action="borrow",
            amount=1000.0,
            collateral_ratio=1.5,
        )

        if assessment.is_high_risk:
            print(f"High risk: {assessment.risk_factors}")
    """

    def __init__(
        self,
        min_collateral_ratio: float = 1.5,
        max_borrow_utilization: float = 0.75,
        warn_on_new_protocols: bool = True,
    ):
        """
        Initialize the DeFi validator.

        Args:
            min_collateral_ratio: Minimum safe collateral ratio for borrowing
            max_borrow_utilization: Maximum safe borrow utilization
            warn_on_new_protocols: Whether to warn on newer/less audited protocols
        """
        self.min_collateral_ratio = min_collateral_ratio
        self.max_borrow_utilization = max_borrow_utilization
        self.warn_on_new_protocols = warn_on_new_protocols

    def assess(
        self,
        protocol: str,
        action: str,
        amount: float = 0.0,
        collateral_ratio: Optional[float] = None,
        apy: Optional[float] = None,
        token_address: Optional[str] = None,
        **kwargs: Any,
    ) -> DeFiRiskAssessment:
        """
        Assess the risk of a DeFi operation.

        Args:
            protocol: The DeFi protocol (compound, aave, morpho, etc.)
            action: The action type (supply, borrow, etc.)
            amount: The transaction amount in USD
            collateral_ratio: Current collateral ratio (for borrowing)
            apy: Expected APY (for yield operations)
            token_address: Token contract address
            **kwargs: Additional parameters

        Returns:
            DeFiRiskAssessment with risk analysis
        """
        # Parse protocol and action
        protocol_enum = self._parse_protocol(protocol)
        action_enum = self._parse_action(action)

        risk_factors: List[str] = []
        recommendations: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {
            "protocol": protocol,
            "action": action,
            "amount": amount,
        }

        # Base risk from protocol
        base_risk = self._get_protocol_risk(protocol_enum)
        risk_score = base_risk * 25  # Convert to 0-100 scale

        # Apply action weight
        action_weight = ACTION_RISK_WEIGHTS.get(action_enum, 1.0)
        risk_score *= action_weight

        # Amount-based risk adjustment
        if amount > 0:
            if amount > 10000:
                risk_score += 30
                risk_factors.append(f"Large amount: ${amount:,.2f}")
                recommendations.append("Consider splitting into smaller transactions")
            elif amount > 1000:
                risk_score += 15
                risk_factors.append(f"Significant amount: ${amount:,.2f}")

        # Collateral ratio risk (for borrowing)
        if action_enum == DeFiActionType.BORROW:
            if collateral_ratio is not None:
                details["collateral_ratio"] = collateral_ratio

                if collateral_ratio < 1.0:
                    risk_score += 50
                    warnings.append("CRITICAL: Under-collateralized position")
                    risk_factors.append("Collateral ratio below 1.0 - immediate liquidation risk")
                elif collateral_ratio < self.min_collateral_ratio:
                    risk_score += 30
                    warnings.append(f"Low collateral ratio: {collateral_ratio:.2f}")
                    risk_factors.append(f"Collateral ratio below safe threshold ({self.min_collateral_ratio})")
                    recommendations.append("Add more collateral before borrowing")
            else:
                risk_score += 20
                risk_factors.append("Collateral ratio not provided - unable to assess liquidation risk")
                recommendations.append("Always monitor collateral ratio when borrowing")

        # APY risk assessment
        if apy is not None:
            details["apy"] = apy
            if apy > 100:
                risk_score += 40
                warnings.append(f"Extremely high APY ({apy:.1f}%) - likely unsustainable or scam")
                risk_factors.append("APY above 100% indicates high risk or fraud")
            elif apy > 50:
                risk_score += 20
                risk_factors.append(f"High APY ({apy:.1f}%) - may be unsustainable")
                recommendations.append("Research the source of yield before investing")

        # Protocol-specific risks
        if protocol_enum == DeFiProtocol.WOW:
            risk_score += 25
            risk_factors.append("WOW protocol - higher risk for new token launches")
            if action_enum == DeFiActionType.CREATE_TOKEN:
                warnings.append("Token creation requires careful consideration of tokenomics")

        if protocol_enum == DeFiProtocol.SUPERFLUID:
            if action_enum == DeFiActionType.CREATE_FLOW:
                risk_factors.append("Token streaming requires ongoing token balance")
                recommendations.append("Ensure sufficient token balance for stream duration")

        if protocol_enum == DeFiProtocol.MORPHO:
            risk_factors.append("Morpho optimizes across lending markets - additional smart contract risk")

        # New protocol warning
        if self.warn_on_new_protocols and protocol_enum == DeFiProtocol.UNKNOWN:
            risk_score += 30
            warnings.append("Unknown protocol - exercise extreme caution")
            risk_factors.append("Protocol not in known list - may lack audits or track record")

        # Determine risk level
        risk_level = self._score_to_level(risk_score)

        # Add general recommendations
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recommendations.append("Consider consulting with a DeFi expert before proceeding")
            recommendations.append("Only invest what you can afford to lose")

        return DeFiRiskAssessment(
            protocol=protocol_enum,
            action_type=action_enum,
            risk_level=risk_level,
            risk_score=min(100, risk_score),
            risk_factors=risk_factors,
            recommendations=recommendations,
            warnings=warnings,
            details=details,
        )

    def _parse_protocol(self, protocol: str) -> DeFiProtocol:
        """Parse protocol string to enum."""
        protocol_lower = protocol.lower().strip()

        protocol_map = {
            "compound": DeFiProtocol.COMPOUND,
            "aave": DeFiProtocol.AAVE,
            "morpho": DeFiProtocol.MORPHO,
            "superfluid": DeFiProtocol.SUPERFLUID,
            "uniswap": DeFiProtocol.UNISWAP,
            "wow": DeFiProtocol.WOW,
        }

        return protocol_map.get(protocol_lower, DeFiProtocol.UNKNOWN)

    def _parse_action(self, action: str) -> DeFiActionType:
        """Parse action string to enum."""
        action_lower = action.lower().strip().replace("_", " ").replace("-", " ")

        action_map = {
            "supply": DeFiActionType.SUPPLY,
            "deposit": DeFiActionType.SUPPLY,
            "withdraw": DeFiActionType.WITHDRAW,
            "borrow": DeFiActionType.BORROW,
            "repay": DeFiActionType.REPAY,
            "swap": DeFiActionType.SWAP,
            "trade": DeFiActionType.TRADE,
            "add liquidity": DeFiActionType.ADD_LIQUIDITY,
            "remove liquidity": DeFiActionType.REMOVE_LIQUIDITY,
            "create token": DeFiActionType.CREATE_TOKEN,
            "buy token": DeFiActionType.BUY_TOKEN,
            "sell token": DeFiActionType.SELL_TOKEN,
            "create flow": DeFiActionType.CREATE_FLOW,
            "delete flow": DeFiActionType.DELETE_FLOW,
            "get portfolio": DeFiActionType.GET_PORTFOLIO,
            "get flow": DeFiActionType.GET_FLOW,
        }

        return action_map.get(action_lower, DeFiActionType.OTHER)

    def _get_protocol_risk(self, protocol: DeFiProtocol) -> float:
        """
        Get base risk level for a protocol (1-4 scale).

        NOTE: These values are HEURISTIC estimates, not data-driven.
        See module docstring for known limitations and improvement path.
        """
        # Risk scale: 1.0 (safest) to 4.0 (riskiest)
        # Values are arbitrary heuristics based on general reputation
        risk_map = {
            DeFiProtocol.COMPOUND: 2.0,    # Heuristic: established, audited
            DeFiProtocol.AAVE: 2.0,        # Heuristic: established, audited
            DeFiProtocol.UNISWAP: 2.0,     # Heuristic: established, audited
            DeFiProtocol.MORPHO: 2.5,      # Heuristic: newer, but audited
            DeFiProtocol.SUPERFLUID: 2.5,  # Heuristic: innovative, some risk
            DeFiProtocol.WOW: 3.5,         # Heuristic: new token launches
            DeFiProtocol.UNKNOWN: 4.0,     # Default: max risk for unknown
        }

        return risk_map.get(protocol, 4.0)

    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= 75:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


def assess_defi_risk(
    protocol: str,
    action: str,
    amount: float = 0.0,
    **kwargs: Any,
) -> DeFiRiskAssessment:
    """
    Convenience function for one-off DeFi risk assessment.

    Args:
        protocol: The DeFi protocol
        action: The action type
        amount: The transaction amount in USD
        **kwargs: Additional parameters

    Returns:
        DeFiRiskAssessment

    Example:
        assessment = assess_defi_risk(
            protocol="compound",
            action="borrow",
            amount=500.0,
            collateral_ratio=1.8,
        )
    """
    validator = DeFiValidator()
    return validator.assess(
        protocol=protocol,
        action=action,
        amount=amount,
        **kwargs,
    )


__all__ = [
    "DeFiProtocol",
    "DeFiActionType",
    "DeFiRiskAssessment",
    "DeFiValidator",
    "assess_defi_risk",
    "ACTION_RISK_WEIGHTS",
]
