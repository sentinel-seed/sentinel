"""
Specialized analyzers for pre-flight transaction simulation.

Provides modular risk analysis components:
- JupiterAnalyzer: Swap quotes and slippage analysis
- GoPlusAnalyzer: Token security via GoPlus API
- TokenRiskAnalyzer: Comprehensive token risk assessment
- SlippageAnalyzer: Slippage calculation and recommendations
- LiquidityAnalyzer: Pool liquidity analysis

References:
- Jupiter API: https://dev.jup.ag/docs/swap-api
- GoPlus API: https://docs.gopluslabs.io/reference/solanatokensecurityusingget
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

from .simulator import (
    RiskLevel,
    RiskFactor,
    RiskAssessment,
    TokenSecurityResult,
)

logger = logging.getLogger("sentinelseed.preflight.analyzers")


@dataclass
class QuoteResult:
    """Result from Jupiter quote."""
    success: bool
    input_mint: str
    output_mint: str
    input_amount: int
    output_amount: int
    minimum_output: int
    slippage_bps: int
    price_impact_pct: float
    route_plan: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LiquidityInfo:
    """Liquidity information for a token pair."""
    pool_address: str
    token_a: str
    token_b: str
    reserve_a: int
    reserve_b: int
    liquidity_usd: float
    volume_24h_usd: float
    fee_pct: float
    is_healthy: bool
    risks: List[RiskAssessment] = field(default_factory=list)


class JupiterAnalyzer:
    """
    Analyzer for Jupiter swap quotes.

    Provides detailed analysis of swap routes, slippage, and price impact.

    Example:
        analyzer = JupiterAnalyzer()
        quote = await analyzer.get_quote(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1_000_000_000,
        )
        print(f"Expected output: {quote.output_amount}")
    """

    QUOTE_URL = "https://api.jup.ag/quote"

    # Slippage thresholds (basis points)
    SLIPPAGE_LOW = 50      # 0.5%
    SLIPPAGE_MEDIUM = 200  # 2%
    SLIPPAGE_HIGH = 500    # 5%
    SLIPPAGE_CRITICAL = 1000  # 10%

    # Price impact thresholds (percentage)
    IMPACT_LOW = 0.5
    IMPACT_MEDIUM = 1.0
    IMPACT_HIGH = 3.0
    IMPACT_CRITICAL = 10.0

    def __init__(self, http_client: Optional[Any] = None):
        """
        Initialize Jupiter analyzer.

        Args:
            http_client: Optional HTTP client (httpx or aiohttp)
        """
        self._http_client = http_client

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(timeout=30.0)
            except (ImportError, AttributeError):
                import aiohttp
                self._http_client = aiohttp.ClientSession()
        return self._http_client

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        only_direct_routes: bool = False,
    ) -> QuoteResult:
        """
        Get swap quote from Jupiter.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Input amount in smallest units
            slippage_bps: Slippage tolerance in basis points
            only_direct_routes: Only use direct routes (no intermediate tokens)

        Returns:
            QuoteResult with quote details
        """
        client = await self._get_client()

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
        }
        if only_direct_routes:
            params["onlyDirectRoutes"] = "true"

        url = f"{self.QUOTE_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

        try:
            if hasattr(client, "get"):
                response = await client.get(url)
                data = response.json()
            else:
                async with client.get(url) as response:
                    data = await response.json()

            # Check for errors - Jupiter API returns "error" OR "code" field
            if "error" in data or "code" in data:
                error_msg = (
                    data.get("error")
                    or data.get("message")
                    or f"API error code: {data.get('code')}"
                )
                return QuoteResult(
                    success=False,
                    input_mint=input_mint,
                    output_mint=output_mint,
                    input_amount=amount,
                    output_amount=0,
                    minimum_output=0,
                    slippage_bps=slippage_bps,
                    price_impact_pct=0,
                    error=error_msg,
                    raw_data=data,
                )

            return QuoteResult(
                success=True,
                input_mint=input_mint,
                output_mint=output_mint,
                input_amount=amount,
                output_amount=int(data.get("outAmount", 0)),
                minimum_output=int(data.get("otherAmountThreshold", 0)),
                slippage_bps=int(data.get("slippageBps", slippage_bps)),
                price_impact_pct=float(data.get("priceImpactPct", 0)),
                route_plan=data.get("routePlan", []),
                raw_data=data,
            )

        except Exception as e:
            logger.error(f"Jupiter quote failed: {e}")
            return QuoteResult(
                success=False,
                input_mint=input_mint,
                output_mint=output_mint,
                input_amount=amount,
                output_amount=0,
                minimum_output=0,
                slippage_bps=slippage_bps,
                price_impact_pct=0,
                error=str(e),
            )

    def analyze_quote(self, quote: QuoteResult) -> List[RiskAssessment]:
        """
        Analyze a quote for risks.

        Args:
            quote: QuoteResult from get_quote

        Returns:
            List of RiskAssessment for identified risks
        """
        risks = []

        if not quote.success:
            risks.append(RiskAssessment(
                factor=RiskFactor.SIMULATION_FAILED,
                level=RiskLevel.CRITICAL,
                description=f"Quote failed: {quote.error}",
            ))
            return risks

        # Analyze slippage
        if quote.slippage_bps >= self.SLIPPAGE_CRITICAL:
            risks.append(RiskAssessment(
                factor=RiskFactor.HIGH_SLIPPAGE,
                level=RiskLevel.CRITICAL,
                description=f"Critical slippage: {quote.slippage_bps / 100:.2f}%",
                raw_data={"slippage_bps": quote.slippage_bps},
            ))
        elif quote.slippage_bps >= self.SLIPPAGE_HIGH:
            risks.append(RiskAssessment(
                factor=RiskFactor.HIGH_SLIPPAGE,
                level=RiskLevel.HIGH,
                description=f"High slippage: {quote.slippage_bps / 100:.2f}%",
                raw_data={"slippage_bps": quote.slippage_bps},
            ))
        elif quote.slippage_bps >= self.SLIPPAGE_MEDIUM:
            risks.append(RiskAssessment(
                factor=RiskFactor.HIGH_SLIPPAGE,
                level=RiskLevel.MEDIUM,
                description=f"Moderate slippage: {quote.slippage_bps / 100:.2f}%",
                raw_data={"slippage_bps": quote.slippage_bps},
            ))

        # Analyze price impact
        if quote.price_impact_pct >= self.IMPACT_CRITICAL:
            risks.append(RiskAssessment(
                factor=RiskFactor.PRICE_IMPACT,
                level=RiskLevel.CRITICAL,
                description=f"Critical price impact: {quote.price_impact_pct:.2f}%",
                raw_data={"price_impact_pct": quote.price_impact_pct},
            ))
        elif quote.price_impact_pct >= self.IMPACT_HIGH:
            risks.append(RiskAssessment(
                factor=RiskFactor.PRICE_IMPACT,
                level=RiskLevel.HIGH,
                description=f"High price impact: {quote.price_impact_pct:.2f}%",
                raw_data={"price_impact_pct": quote.price_impact_pct},
            ))
        elif quote.price_impact_pct >= self.IMPACT_MEDIUM:
            risks.append(RiskAssessment(
                factor=RiskFactor.PRICE_IMPACT,
                level=RiskLevel.MEDIUM,
                description=f"Moderate price impact: {quote.price_impact_pct:.2f}%",
                raw_data={"price_impact_pct": quote.price_impact_pct},
            ))

        return risks

    def get_optimal_slippage(
        self,
        quote: QuoteResult,
        trade_urgency: str = "normal",
    ) -> int:
        """
        Calculate optimal slippage for a trade.

        Args:
            quote: QuoteResult from get_quote
            trade_urgency: "low", "normal", or "high"

        Returns:
            Recommended slippage in basis points
        """
        base_slippage = quote.slippage_bps

        # Adjust based on price impact
        if quote.price_impact_pct > self.IMPACT_HIGH:
            base_slippage = max(base_slippage, self.SLIPPAGE_HIGH)
        elif quote.price_impact_pct > self.IMPACT_MEDIUM:
            base_slippage = max(base_slippage, self.SLIPPAGE_MEDIUM)

        # Adjust based on urgency
        if trade_urgency == "high":
            return int(base_slippage * 1.5)
        elif trade_urgency == "low":
            return int(base_slippage * 0.8)

        return base_slippage


class GoPlusAnalyzer:
    """
    Analyzer for GoPlus token security API.

    Provides detailed security analysis for Solana tokens including
    honeypot detection, authority checks, and tax analysis.

    Example:
        analyzer = GoPlusAnalyzer()
        result = await analyzer.check_token("TokenMintAddress...")
        if result.is_honeypot:
            print("Warning: Token is a honeypot!")
    """

    API_URL = "https://api.gopluslabs.io/api/v1/solana/token_security"

    def __init__(
        self,
        api_key: Optional[str] = None,
        http_client: Optional[Any] = None,
    ):
        """
        Initialize GoPlus analyzer.

        Args:
            api_key: Optional API key for higher rate limits
            http_client: Optional HTTP client
        """
        self.api_key = api_key
        self._http_client = http_client

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(timeout=30.0)
            except (ImportError, AttributeError):
                import aiohttp
                self._http_client = aiohttp.ClientSession()
        return self._http_client

    async def check_token(self, token_address: str) -> TokenSecurityResult:
        """
        Check token security via GoPlus API.

        Args:
            token_address: Token mint address

        Returns:
            TokenSecurityResult with security analysis
        """
        client = await self._get_client()

        url = f"{self.API_URL}?contract_addresses={token_address}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if hasattr(client, "get"):
                response = await client.get(url, headers=headers)
                data = response.json()
            else:
                async with client.get(url, headers=headers) as response:
                    data = await response.json()

            # Check for API errors - GoPlus returns {"code": 1} for success, {"code": 0} for error
            if data.get("code") == 0 or "error" in data:
                error_msg = data.get("message") or data.get("error") or "Unknown GoPlus error"
                return TokenSecurityResult(
                    token_address=token_address,
                    is_safe=False,
                    risk_level=RiskLevel.MEDIUM,
                    risks=[RiskAssessment(
                        factor=RiskFactor.SIMULATION_FAILED,
                        level=RiskLevel.MEDIUM,
                        description=f"Security check API error: {error_msg}",
                    )],
                )

            # Handle None result gracefully
            result = data.get("result") or {}
            result_data = result.get(token_address.lower(), {})

            if not result_data:
                return TokenSecurityResult(
                    token_address=token_address,
                    is_safe=True,
                    risk_level=RiskLevel.LOW,
                    risks=[RiskAssessment(
                        factor=RiskFactor.LOW_LIQUIDITY,
                        level=RiskLevel.LOW,
                        description="Token not in GoPlus database",
                    )],
                )

            risks = self._analyze_security_data(result_data)

            # Extract properties
            freeze_authority = result_data.get("freeze_authority")
            mint_authority = result_data.get("mint_authority")
            is_honeypot = result_data.get("is_honeypot", False)

            max_risk = RiskLevel.NONE
            for risk in risks:
                if risk.level > max_risk:
                    max_risk = risk.level

            return TokenSecurityResult(
                token_address=token_address,
                is_safe=max_risk < RiskLevel.HIGH and not is_honeypot,
                risk_level=max_risk,
                risks=risks,
                has_freeze_authority=bool(freeze_authority),
                has_mint_authority=bool(mint_authority),
                freeze_authority_address=freeze_authority,
                mint_authority_address=mint_authority,
                buy_tax_pct=float(result_data.get("buy_tax", 0)),
                sell_tax_pct=float(result_data.get("sell_tax", 0)),
                transfer_tax_pct=float(result_data.get("transfer_tax", 0)),
                total_supply=int(result_data.get("total_supply", 0)),
                holder_count=int(result_data.get("holder_count", 0)),
                lp_locked_pct=float(result_data.get("lp_locked_pct", 0)),
                is_honeypot=is_honeypot,
                honeypot_reason=result_data.get("honeypot_reason"),
                raw_data=result_data,
            )

        except Exception as e:
            logger.error(f"GoPlus check failed: {e}")
            return TokenSecurityResult(
                token_address=token_address,
                is_safe=False,
                risk_level=RiskLevel.MEDIUM,
                risks=[RiskAssessment(
                    factor=RiskFactor.SIMULATION_FAILED,
                    level=RiskLevel.MEDIUM,
                    description=f"Security check error: {e}",
                )],
            )

    def _analyze_security_data(
        self,
        data: Dict[str, Any],
    ) -> List[RiskAssessment]:
        """Analyze GoPlus security data for risks."""
        risks = []

        # Honeypot check
        if data.get("is_honeypot"):
            reason = data.get("honeypot_reason", "Unknown")
            risks.append(RiskAssessment(
                factor=RiskFactor.HONEYPOT,
                level=RiskLevel.CRITICAL,
                description=f"Token is a honeypot: {reason}",
                raw_data={"reason": reason},
            ))

        # Freeze authority
        if data.get("freeze_authority"):
            risks.append(RiskAssessment(
                factor=RiskFactor.FREEZE_AUTHORITY,
                level=RiskLevel.HIGH,
                description="Token has freeze authority - funds can be frozen",
                raw_data={"authority": data["freeze_authority"]},
            ))

        # Mint authority
        if data.get("mint_authority"):
            risks.append(RiskAssessment(
                factor=RiskFactor.MINT_AUTHORITY,
                level=RiskLevel.MEDIUM,
                description="Token has mint authority - supply can increase",
                raw_data={"authority": data["mint_authority"]},
            ))

        # Tax analysis
        sell_tax = float(data.get("sell_tax", 0))
        if sell_tax >= 50:
            risks.append(RiskAssessment(
                factor=RiskFactor.TRANSFER_TAX,
                level=RiskLevel.CRITICAL,
                description=f"Extreme sell tax: {sell_tax}%",
                raw_data={"sell_tax": sell_tax},
            ))
        elif sell_tax >= 10:
            risks.append(RiskAssessment(
                factor=RiskFactor.TRANSFER_TAX,
                level=RiskLevel.HIGH,
                description=f"High sell tax: {sell_tax}%",
                raw_data={"sell_tax": sell_tax},
            ))
        elif sell_tax >= 5:
            risks.append(RiskAssessment(
                factor=RiskFactor.TRANSFER_TAX,
                level=RiskLevel.MEDIUM,
                description=f"Moderate sell tax: {sell_tax}%",
                raw_data={"sell_tax": sell_tax},
            ))

        # LP locked check
        lp_locked = float(data.get("lp_locked_pct", 0))
        if lp_locked < 50:
            risks.append(RiskAssessment(
                factor=RiskFactor.RUG_PULL,
                level=RiskLevel.HIGH,
                description=f"Low LP locked: {lp_locked}%",
                raw_data={"lp_locked_pct": lp_locked},
            ))
        elif lp_locked < 80:
            risks.append(RiskAssessment(
                factor=RiskFactor.RUG_PULL,
                level=RiskLevel.MEDIUM,
                description=f"Moderate LP locked: {lp_locked}%",
                raw_data={"lp_locked_pct": lp_locked},
            ))

        return risks


class TokenRiskAnalyzer:
    """
    Comprehensive token risk analyzer.

    Combines multiple data sources to provide a complete risk assessment.

    Example:
        analyzer = TokenRiskAnalyzer()
        assessment = await analyzer.analyze("TokenMintAddress...")
        print(f"Risk level: {assessment.risk_level}")
    """

    def __init__(
        self,
        goplus_api_key: Optional[str] = None,
        http_client: Optional[Any] = None,
    ):
        """
        Initialize token risk analyzer.

        Args:
            goplus_api_key: Optional GoPlus API key
            http_client: Optional HTTP client
        """
        self.goplus = GoPlusAnalyzer(
            api_key=goplus_api_key,
            http_client=http_client,
        )

    async def analyze(
        self,
        token_address: str,
        include_liquidity: bool = True,
    ) -> TokenSecurityResult:
        """
        Perform comprehensive token analysis.

        Args:
            token_address: Token mint address
            include_liquidity: Whether to include liquidity analysis

        Returns:
            TokenSecurityResult with complete analysis
        """
        # Get GoPlus security data
        security = await self.goplus.check_token(token_address)

        # Add additional analysis if needed
        if include_liquidity and security.holder_count < 100:
            security.risks.append(RiskAssessment(
                factor=RiskFactor.LOW_LIQUIDITY,
                level=RiskLevel.MEDIUM,
                description=f"Low holder count: {security.holder_count}",
                raw_data={"holder_count": security.holder_count},
            ))

        return security


class SlippageAnalyzer:
    """
    Analyzer for slippage calculation and recommendations.

    Provides slippage estimation and optimal settings based on
    market conditions and trade parameters.
    """

    # Default thresholds
    LOW_THRESHOLD = 50      # 0.5%
    MEDIUM_THRESHOLD = 200  # 2%
    HIGH_THRESHOLD = 500    # 5%

    def __init__(self, max_slippage_bps: int = 500):
        """
        Initialize slippage analyzer.

        Args:
            max_slippage_bps: Maximum acceptable slippage
        """
        self.max_slippage = max_slippage_bps

    def analyze(
        self,
        quoted_slippage: int,
        price_impact: float,
        trade_size_usd: float = 0,
    ) -> Tuple[RiskLevel, List[RiskAssessment]]:
        """
        Analyze slippage and price impact.

        Args:
            quoted_slippage: Slippage from quote (basis points)
            price_impact: Price impact percentage
            trade_size_usd: Trade size in USD for context

        Returns:
            Tuple of (RiskLevel, List[RiskAssessment])
        """
        risks = []
        max_risk = RiskLevel.NONE

        # Slippage analysis
        if quoted_slippage > self.max_slippage:
            level = RiskLevel.HIGH if quoted_slippage > self.HIGH_THRESHOLD else RiskLevel.MEDIUM
            risks.append(RiskAssessment(
                factor=RiskFactor.HIGH_SLIPPAGE,
                level=level,
                description=f"Slippage {quoted_slippage / 100:.2f}% exceeds threshold",
                raw_data={"slippage_bps": quoted_slippage, "max": self.max_slippage},
            ))
            if level > max_risk:
                max_risk = level

        # Price impact analysis
        if price_impact > 5.0:
            risks.append(RiskAssessment(
                factor=RiskFactor.PRICE_IMPACT,
                level=RiskLevel.HIGH,
                description=f"High price impact: {price_impact:.2f}%",
                raw_data={"price_impact_pct": price_impact},
            ))
            if RiskLevel.HIGH > max_risk:
                max_risk = RiskLevel.HIGH
        elif price_impact > 1.0:
            risks.append(RiskAssessment(
                factor=RiskFactor.PRICE_IMPACT,
                level=RiskLevel.MEDIUM,
                description=f"Moderate price impact: {price_impact:.2f}%",
                raw_data={"price_impact_pct": price_impact},
            ))
            if RiskLevel.MEDIUM > max_risk:
                max_risk = RiskLevel.MEDIUM

        return max_risk, risks

    def recommend_slippage(
        self,
        price_impact: float,
        volatility: str = "normal",
    ) -> int:
        """
        Recommend optimal slippage setting.

        Args:
            price_impact: Current price impact
            volatility: Market volatility ("low", "normal", "high")

        Returns:
            Recommended slippage in basis points
        """
        base = self.LOW_THRESHOLD

        # Adjust for price impact
        if price_impact > 5.0:
            base = self.HIGH_THRESHOLD
        elif price_impact > 1.0:
            base = self.MEDIUM_THRESHOLD

        # Adjust for volatility
        multipliers = {"low": 0.8, "normal": 1.0, "high": 1.5}
        multiplier = multipliers.get(volatility, 1.0)

        return min(int(base * multiplier), self.max_slippage)


class LiquidityAnalyzer:
    """
    Analyzer for pool liquidity.

    Provides liquidity depth analysis and risk assessment
    for DEX trading pairs.
    """

    # Liquidity thresholds (USD)
    LOW_LIQUIDITY = 10_000      # $10k
    MEDIUM_LIQUIDITY = 100_000  # $100k
    HEALTHY_LIQUIDITY = 500_000  # $500k

    def analyze_liquidity(
        self,
        liquidity_usd: float,
        trade_size_usd: float,
        volume_24h_usd: float = 0,
    ) -> Tuple[RiskLevel, List[RiskAssessment]]:
        """
        Analyze pool liquidity relative to trade size.

        Args:
            liquidity_usd: Total pool liquidity in USD
            trade_size_usd: Proposed trade size in USD
            volume_24h_usd: 24h trading volume in USD

        Returns:
            Tuple of (RiskLevel, List[RiskAssessment])
        """
        risks = []
        max_risk = RiskLevel.NONE

        # Check absolute liquidity
        if liquidity_usd < self.LOW_LIQUIDITY:
            risks.append(RiskAssessment(
                factor=RiskFactor.LOW_LIQUIDITY,
                level=RiskLevel.HIGH,
                description=f"Very low liquidity: ${liquidity_usd:,.0f}",
                raw_data={"liquidity_usd": liquidity_usd},
            ))
            max_risk = RiskLevel.HIGH
        elif liquidity_usd < self.MEDIUM_LIQUIDITY:
            risks.append(RiskAssessment(
                factor=RiskFactor.LOW_LIQUIDITY,
                level=RiskLevel.MEDIUM,
                description=f"Low liquidity: ${liquidity_usd:,.0f}",
                raw_data={"liquidity_usd": liquidity_usd},
            ))
            if RiskLevel.MEDIUM > max_risk:
                max_risk = RiskLevel.MEDIUM

        # Check trade size relative to liquidity
        if liquidity_usd > 0:
            trade_ratio = trade_size_usd / liquidity_usd
            if trade_ratio > 0.1:  # Trade > 10% of liquidity
                risks.append(RiskAssessment(
                    factor=RiskFactor.ILLIQUID_POOL,
                    level=RiskLevel.HIGH,
                    description=f"Trade is {trade_ratio * 100:.1f}% of pool liquidity",
                    raw_data={"trade_ratio": trade_ratio},
                ))
                if RiskLevel.HIGH > max_risk:
                    max_risk = RiskLevel.HIGH
            elif trade_ratio > 0.01:  # Trade > 1% of liquidity
                risks.append(RiskAssessment(
                    factor=RiskFactor.ILLIQUID_POOL,
                    level=RiskLevel.MEDIUM,
                    description=f"Trade is {trade_ratio * 100:.1f}% of pool liquidity",
                    raw_data={"trade_ratio": trade_ratio},
                ))
                if RiskLevel.MEDIUM > max_risk:
                    max_risk = RiskLevel.MEDIUM

        # Check volume (if available)
        if volume_24h_usd > 0 and liquidity_usd > 0:
            turnover = volume_24h_usd / liquidity_usd
            if turnover < 0.01:  # Less than 1% turnover
                risks.append(RiskAssessment(
                    factor=RiskFactor.STALE_PRICE,
                    level=RiskLevel.LOW,
                    description=f"Low trading activity (turnover: {turnover * 100:.2f}%)",
                    raw_data={"turnover": turnover},
                ))

        return max_risk, risks

    def is_healthy(
        self,
        liquidity_usd: float,
        trade_size_usd: float,
    ) -> bool:
        """
        Check if liquidity is healthy for the trade.

        Args:
            liquidity_usd: Pool liquidity in USD
            trade_size_usd: Trade size in USD

        Returns:
            True if liquidity is healthy for the trade
        """
        if liquidity_usd < self.HEALTHY_LIQUIDITY:
            return False
        if trade_size_usd / liquidity_usd > 0.01:  # More than 1%
            return False
        return True
