"""
Wrapper that integrates Pre-flight Simulator with Solana Agent Kit.

Provides a unified interface for transaction validation that combines:
- Pre-flight simulation (RPC, Jupiter, GoPlus)
- Sentinel THSP validation
- Solana Agent Kit safety checks

Usage:
    from sentinelseed.integrations.preflight import PreflightValidator

    # Initialize with pre-flight simulation
    validator = PreflightValidator(
        rpc_url="https://api.mainnet-beta.solana.com",
        max_transfer=100.0,
    )

    # Validate with simulation
    result = await validator.validate_with_simulation(
        action="swap",
        input_mint="So11111111111111111111111111111111111111112",
        output_mint="TokenMintAddress...",
        amount=1_000_000_000,
    )

    if result.should_proceed:
        print("Transaction is safe to execute")
    else:
        print(f"Risks: {result.simulation_risks}")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import asyncio
import logging

from .simulator import (
    TransactionSimulator,
    SimulationResult,
    SwapSimulationResult,
    TokenSecurityResult,
    RiskLevel,
    RiskAssessment,
)

# Import Solana Agent Kit validator (optional)
try:
    from sentinelseed.integrations.solana_agent_kit import (
        SentinelValidator,
        TransactionSafetyResult,
    )
    HAS_SOLANA_AGENT_KIT = True
except (ImportError, AttributeError):
    HAS_SOLANA_AGENT_KIT = False
    SentinelValidator = None
    TransactionSafetyResult = None

logger = logging.getLogger("sentinelseed.preflight.wrapper")


@dataclass
class PreflightResult:
    """Combined result from pre-flight and validation."""
    # Overall
    should_proceed: bool
    risk_level: str
    is_safe: bool

    # Validation result
    validation_passed: bool
    validation_concerns: List[str] = field(default_factory=list)

    # Simulation result
    simulation_passed: bool = True
    simulation_risks: List[str] = field(default_factory=list)

    # Swap-specific
    expected_output: Optional[int] = None
    slippage_bps: Optional[int] = None
    price_impact_pct: Optional[float] = None

    # Token security
    token_security_passed: bool = True
    token_risks: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Raw results
    raw_validation: Optional[Any] = None
    raw_simulation: Optional[Any] = None
    raw_token_security: Optional[Any] = None


class PreflightValidator:
    """
    Unified validator with pre-flight simulation.

    Combines Sentinel THSP validation with transaction simulation
    for comprehensive safety checks before execution.

    Example:
        from sentinelseed.integrations.preflight import PreflightValidator

        validator = PreflightValidator(
            rpc_url="https://api.mainnet-beta.solana.com"
        )

        # Check a swap
        result = await validator.validate_swap(
            input_mint="So11...",
            output_mint="Token...",
            amount=1_000_000_000,
        )

        if result.should_proceed:
            print(f"Safe to swap. Expected output: {result.expected_output}")
        else:
            print(f"Blocked: {result.simulation_risks}")
    """

    def __init__(
        self,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        goplus_api_key: Optional[str] = None,
        max_transfer: float = 100.0,
        max_slippage_bps: int = 500,
        require_purpose: bool = True,
        strict_mode: bool = False,
    ):
        """
        Initialize pre-flight validator.

        Args:
            rpc_url: Solana RPC endpoint
            goplus_api_key: Optional GoPlus API key
            max_transfer: Maximum transfer amount (SOL)
            max_slippage_bps: Maximum acceptable slippage
            require_purpose: Require purpose for financial actions
            strict_mode: Block on any risk detected
        """
        self.strict_mode = strict_mode

        # Initialize simulator
        self.simulator = TransactionSimulator(
            rpc_url=rpc_url,
            goplus_api_key=goplus_api_key,
            max_slippage_bps=max_slippage_bps,
        )

        # Initialize Solana Agent Kit validator (if available)
        self._validator = None
        if HAS_SOLANA_AGENT_KIT:
            self._validator = SentinelValidator(
                max_transfer=max_transfer,
                require_purpose_for=["transfer", "swap", "stake", "bridge"] if require_purpose else [],
                strict_mode=strict_mode,
            )

        logger.debug(f"PreflightValidator initialized (SAK: {HAS_SOLANA_AGENT_KIT})")

    async def validate_with_simulation(
        self,
        action: str,
        **kwargs,
    ) -> PreflightResult:
        """
        Validate action with pre-flight simulation.

        Args:
            action: Action type (swap, transfer, stake, etc.)
            **kwargs: Action parameters

        Returns:
            PreflightResult with combined validation and simulation
        """
        action_lower = action.lower()

        if action_lower == "swap":
            return await self.validate_swap(
                input_mint=kwargs.get("input_mint", kwargs.get("from_token", "")),
                output_mint=kwargs.get("output_mint", kwargs.get("to_token", "")),
                amount=kwargs.get("amount", 0),
                slippage_bps=kwargs.get("slippage_bps", 50),
                purpose=kwargs.get("purpose", ""),
            )

        elif action_lower == "transfer":
            return await self.validate_transfer(
                amount=kwargs.get("amount", 0),
                recipient=kwargs.get("recipient", kwargs.get("to", "")),
                token=kwargs.get("token", kwargs.get("mint", "")),
                purpose=kwargs.get("purpose", ""),
            )

        else:
            # Generic validation
            return await self._validate_generic(action, kwargs)

    async def validate_swap(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        purpose: str = "",
    ) -> PreflightResult:
        """
        Validate a swap with full simulation.

        Args:
            input_mint: Input token mint
            output_mint: Output token mint
            amount: Amount in smallest units
            slippage_bps: Slippage tolerance
            purpose: Purpose of the swap

        Returns:
            PreflightResult with swap analysis
        """
        validation_passed = True
        validation_concerns = []
        recommendations = []

        # Run Sentinel validation (if available)
        raw_validation = None
        if self._validator:
            raw_validation = self._validator.check(
                action="swap",
                amount=amount / 1e9,  # Convert lamports to SOL for validator
                purpose=purpose,
            )
            validation_passed = raw_validation.should_proceed
            validation_concerns = raw_validation.concerns

        # Run simulation
        simulation = await self.simulator.simulate_swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=slippage_bps,
            check_token_security=True,
        )

        # Extract simulation risks
        simulation_risks = [r.description for r in simulation.risks]
        token_risks = []

        # Separate token security risks
        for risk in simulation.risks:
            if risk.factor.value in ("honeypot", "freeze_authority", "mint_authority", "transfer_tax"):
                token_risks.append(risk.description)

        # Generate recommendations
        if simulation.slippage_bps > 200:
            recommendations.append(f"Consider smaller trade size to reduce slippage")
        if simulation.price_impact_pct > 1.0:
            recommendations.append(f"High price impact - consider splitting trade")

        # Determine overall safety
        simulation_passed = simulation.is_safe
        token_security_passed = not any(
            r.level >= RiskLevel.HIGH
            for r in simulation.risks
            if r.factor.value in ("honeypot", "freeze_authority")
        )

        should_proceed = validation_passed and simulation_passed
        if self.strict_mode:
            should_proceed = should_proceed and token_security_passed

        # Map risk level
        risk_level = "LOW"
        if simulation.risk_level >= RiskLevel.CRITICAL:
            risk_level = "CRITICAL"
        elif simulation.risk_level >= RiskLevel.HIGH:
            risk_level = "HIGH"
        elif simulation.risk_level >= RiskLevel.MEDIUM:
            risk_level = "MEDIUM"

        return PreflightResult(
            should_proceed=should_proceed,
            risk_level=risk_level,
            is_safe=simulation.is_safe,
            validation_passed=validation_passed,
            validation_concerns=validation_concerns,
            simulation_passed=simulation_passed,
            simulation_risks=simulation_risks,
            expected_output=simulation.expected_output,
            slippage_bps=simulation.slippage_bps,
            price_impact_pct=simulation.price_impact_pct,
            token_security_passed=token_security_passed,
            token_risks=token_risks,
            recommendations=recommendations,
            raw_validation=raw_validation,
            raw_simulation=simulation,
        )

    async def validate_transfer(
        self,
        amount: float,
        recipient: str,
        token: str = "",
        purpose: str = "",
    ) -> PreflightResult:
        """
        Validate a transfer with token security check.

        Args:
            amount: Transfer amount
            recipient: Recipient address
            token: Token mint (empty for SOL)
            purpose: Purpose of transfer

        Returns:
            PreflightResult with transfer analysis
        """
        validation_passed = True
        validation_concerns = []
        recommendations = []

        # Run Sentinel validation
        raw_validation = None
        if self._validator:
            raw_validation = self._validator.check(
                action="transfer",
                amount=amount,
                recipient=recipient,
                purpose=purpose,
            )
            validation_passed = raw_validation.should_proceed
            validation_concerns = raw_validation.concerns

        # Check token security (if not SOL)
        token_security_passed = True
        token_risks = []
        raw_token_security = None

        if token and token not in self.simulator.SAFE_TOKENS:
            raw_token_security = await self.simulator.check_token_security(token)
            token_security_passed = raw_token_security.is_safe
            token_risks = [r.description for r in raw_token_security.risks]

            if raw_token_security.is_honeypot:
                recommendations.append("Token is a honeypot - do not proceed")
            if raw_token_security.has_freeze_authority:
                recommendations.append("Token has freeze authority - funds can be frozen")

        should_proceed = validation_passed
        if self.strict_mode:
            should_proceed = should_proceed and token_security_passed

        # Determine risk level
        risk_level = "LOW"
        if raw_token_security and raw_token_security.risk_level >= RiskLevel.HIGH:
            risk_level = "HIGH"
        elif raw_validation and len(validation_concerns) > 0:
            risk_level = "MEDIUM"

        return PreflightResult(
            should_proceed=should_proceed,
            risk_level=risk_level,
            is_safe=validation_passed and token_security_passed,
            validation_passed=validation_passed,
            validation_concerns=validation_concerns,
            simulation_passed=True,  # No simulation for transfers
            token_security_passed=token_security_passed,
            token_risks=token_risks,
            recommendations=recommendations,
            raw_validation=raw_validation,
            raw_token_security=raw_token_security,
        )

    async def _validate_generic(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> PreflightResult:
        """Validate a generic action."""
        validation_passed = True
        validation_concerns = []

        # Run Sentinel validation
        raw_validation = None
        if self._validator:
            raw_validation = self._validator.check(
                action=action,
                amount=params.get("amount", 0),
                purpose=params.get("purpose", ""),
            )
            validation_passed = raw_validation.should_proceed
            validation_concerns = raw_validation.concerns

        risk_level = "LOW"
        if not validation_passed:
            risk_level = "MEDIUM"

        return PreflightResult(
            should_proceed=validation_passed,
            risk_level=risk_level,
            is_safe=validation_passed,
            validation_passed=validation_passed,
            validation_concerns=validation_concerns,
            raw_validation=raw_validation,
        )

    async def check_token(self, token_address: str) -> TokenSecurityResult:
        """
        Check token security.

        Args:
            token_address: Token mint address

        Returns:
            TokenSecurityResult with security analysis
        """
        return await self.simulator.check_token_security(token_address)

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        stats = {
            "simulator": self.simulator.get_stats(),
        }
        if self._validator:
            stats["validator"] = self._validator.get_stats()
        return stats

    async def close(self):
        """Close resources."""
        await self.simulator.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def create_preflight_tools(
    validator: Optional[PreflightValidator] = None,
    rpc_url: str = "https://api.mainnet-beta.solana.com",
) -> List[Any]:
    """
    Create LangChain tools for pre-flight validation.

    Args:
        validator: Optional existing validator
        rpc_url: Solana RPC endpoint

    Returns:
        List of LangChain Tool objects
    """
    try:
        from langchain.tools import Tool
    except (ImportError, AttributeError):
        raise ImportError("langchain is required: pip install langchain")

    if validator is None:
        validator = PreflightValidator(rpc_url=rpc_url)

    async def check_swap_safety(input_str: str) -> str:
        """
        Check if a swap is safe before executing.

        Format: "input_mint output_mint amount_lamports"
        Example: "So11... EPjF... 1000000000"
        """
        parts = input_str.strip().split()
        if len(parts) < 3:
            return "ERROR: Format: 'input_mint output_mint amount_lamports'"

        input_mint, output_mint = parts[0], parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            return f"ERROR: Invalid amount: {parts[2]}"

        result = await validator.validate_swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
        )

        if result.should_proceed:
            return (
                f"SAFE: Expected output: {result.expected_output}, "
                f"Slippage: {result.slippage_bps}bps, "
                f"Impact: {result.price_impact_pct:.2f}%"
            )
        else:
            return f"BLOCKED: {', '.join(result.simulation_risks)}"

    async def check_token_security(token_address: str) -> str:
        """
        Check token security before interacting.

        Input: Token mint address
        """
        result = await validator.check_token(token_address.strip())

        if result.is_safe:
            return "SAFE: Token passed security checks"
        else:
            risks = [r.description for r in result.risks]
            return f"WARNING: {', '.join(risks)}"

    def sync_check_swap(input_str: str) -> str:
        """Sync wrapper for async check."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(check_swap_safety(input_str))

    def sync_check_token(token_address: str) -> str:
        """Sync wrapper for async check."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(check_token_security(token_address))

    return [
        Tool(
            name="preflight_check_swap",
            description=(
                "Simulate a swap before executing. "
                "Input: 'input_mint output_mint amount_lamports'. "
                "Returns expected output, slippage, and risks."
            ),
            func=sync_check_swap,
        ),
        Tool(
            name="preflight_check_token",
            description=(
                "Check token security before interacting. "
                "Input: Token mint address. "
                "Detects honeypots, freeze authority, and other risks."
            ),
            func=sync_check_token,
        ),
    ]
