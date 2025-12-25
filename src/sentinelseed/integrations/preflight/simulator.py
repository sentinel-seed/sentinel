"""
Pre-flight Transaction Simulator.

Provides transaction simulation capabilities for Solana blockchain operations.
Supports direct RPC simulation, Jupiter swap quotes, and security analysis.

References:
- Solana RPC simulateTransaction: https://solana.com/docs/rpc/http/simulatetransaction
- Jupiter Swap API: https://dev.jup.ag/docs/swap-api
- GoPlus Security API: https://docs.gopluslabs.io/reference/solanatokensecurityusingget
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import logging
import time

logger = logging.getLogger("sentinelseed.preflight")


class RiskLevel(Enum):
    """Risk levels for simulation results."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def __lt__(self, other):
        if isinstance(other, RiskLevel):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, RiskLevel):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, RiskLevel):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, RiskLevel):
            return self.value >= other.value
        return NotImplemented


class RiskFactor(Enum):
    """Types of risks that can be detected."""
    # Token risks
    HONEYPOT = "honeypot"
    FREEZE_AUTHORITY = "freeze_authority"
    MINT_AUTHORITY = "mint_authority"
    TRANSFER_TAX = "transfer_tax"
    LOW_LIQUIDITY = "low_liquidity"
    RUG_PULL = "rug_pull"

    # Transaction risks
    HIGH_SLIPPAGE = "high_slippage"
    SIMULATION_FAILED = "simulation_failed"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    PROGRAM_ERROR = "program_error"
    COMPUTE_EXCEEDED = "compute_exceeded"

    # Market risks
    PRICE_IMPACT = "price_impact"
    STALE_PRICE = "stale_price"
    ILLIQUID_POOL = "illiquid_pool"


class SimulationError(Exception):
    """Raised when simulation fails."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


@dataclass
class RiskAssessment:
    """Individual risk assessment."""
    factor: RiskFactor
    level: RiskLevel
    description: str
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Result of a transaction simulation."""
    success: bool
    is_safe: bool
    risk_level: RiskLevel
    risks: List[RiskAssessment] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    compute_units: int = 0
    error: Optional[str] = None
    error_code: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)
    simulation_time_ms: float = 0

    @property
    def recommendations(self) -> List[str]:
        """Generate recommendations based on risks."""
        recs = []
        for risk in self.risks:
            if risk.level >= RiskLevel.HIGH:
                if risk.factor == RiskFactor.HONEYPOT:
                    recs.append("Token may be a honeypot - cannot sell after purchase")
                elif risk.factor == RiskFactor.HIGH_SLIPPAGE:
                    recs.append("High slippage detected - consider smaller trade size")
                elif risk.factor == RiskFactor.FREEZE_AUTHORITY:
                    recs.append("Token has freeze authority - funds can be frozen")
                elif risk.factor == RiskFactor.LOW_LIQUIDITY:
                    recs.append("Low liquidity - may have difficulty selling")
        return recs


@dataclass
class SwapSimulationResult(SimulationResult):
    """Result of a swap simulation including quote data."""
    input_mint: str = ""
    output_mint: str = ""
    input_amount: int = 0
    expected_output: int = 0
    minimum_output: int = 0
    slippage_bps: int = 0
    price_impact_pct: float = 0.0
    route_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenSecurityResult:
    """Token security analysis result."""
    token_address: str
    is_safe: bool
    risk_level: RiskLevel
    risks: List[RiskAssessment] = field(default_factory=list)

    # Token properties
    has_freeze_authority: bool = False
    has_mint_authority: bool = False
    freeze_authority_address: Optional[str] = None
    mint_authority_address: Optional[str] = None

    # Tax info
    buy_tax_pct: float = 0.0
    sell_tax_pct: float = 0.0
    transfer_tax_pct: float = 0.0

    # Liquidity info
    total_supply: int = 0
    holder_count: int = 0
    lp_locked_pct: float = 0.0

    # Honeypot detection
    is_honeypot: bool = False
    honeypot_reason: Optional[str] = None

    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)


class TransactionSimulator:
    """
    Pre-flight Transaction Simulator for Solana.

    Simulates transactions before execution to detect:
    - Transaction failures and errors
    - High slippage in swaps
    - Token security risks (honeypots, freeze authority)
    - Liquidity issues

    Example:
        from sentinelseed.integrations.preflight import TransactionSimulator

        simulator = TransactionSimulator(
            rpc_url="https://api.mainnet-beta.solana.com"
        )

        # Simulate swap
        result = await simulator.simulate_swap(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="TokenMintAddress...",
            amount=1_000_000_000,  # 1 SOL in lamports
        )

        if result.is_safe:
            print(f"Expected: {result.expected_output}")
        else:
            print(f"Risks: {result.risks}")
    """

    # Default RPC endpoints
    DEFAULT_MAINNET_RPC = "https://api.mainnet-beta.solana.com"
    DEFAULT_DEVNET_RPC = "https://api.devnet.solana.com"

    # Jupiter API endpoints
    JUPITER_QUOTE_URL = "https://api.jup.ag/quote"
    JUPITER_SWAP_URL = "https://api.jup.ag/swap/v1/swap"

    # GoPlus API endpoint
    GOPLUS_SOLANA_URL = "https://api.gopluslabs.io/api/v1/solana/token_security"

    # Well-known safe tokens (mainnet)
    SAFE_TOKENS = {
        "So11111111111111111111111111111111111111112",  # Wrapped SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",  # stSOL
        "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
        "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  # JUP
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # WETH
        "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",  # PYTH
    }

    def __init__(
        self,
        rpc_url: str = DEFAULT_MAINNET_RPC,
        goplus_api_key: Optional[str] = None,
        http_client: Optional[Any] = None,
        max_slippage_bps: int = 500,  # 5% default max slippage
        cache_ttl_seconds: int = 300,  # 5 minute cache for token security
    ):
        """
        Initialize the transaction simulator.

        Args:
            rpc_url: Solana RPC endpoint URL
            goplus_api_key: Optional GoPlus API key (free tier available)
            http_client: Optional custom HTTP client (httpx or aiohttp)
            max_slippage_bps: Maximum acceptable slippage in basis points
            cache_ttl_seconds: Cache TTL for token security results
        """
        self.rpc_url = rpc_url
        self.goplus_api_key = goplus_api_key
        self._http_client = http_client
        self.max_slippage_bps = max_slippage_bps
        self.cache_ttl = cache_ttl_seconds

        # Cache for token security results
        self._token_cache: Dict[str, Tuple[TokenSecurityResult, float]] = {}

        # Statistics
        self._stats = {
            "simulations": 0,
            "successful": 0,
            "failed": 0,
            "risks_detected": 0,
        }

        logger.debug(f"TransactionSimulator initialized with RPC: {rpc_url}")

    async def _get_http_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(timeout=30.0)
            except (ImportError, AttributeError):
                try:
                    import aiohttp
                    self._http_client = aiohttp.ClientSession()
                except (ImportError, AttributeError):
                    raise ImportError(
                        "Either httpx or aiohttp is required: "
                        "pip install httpx  # or pip install aiohttp"
                    )
        return self._http_client

    async def _rpc_request(
        self,
        method: str,
        params: List[Any],
    ) -> Dict[str, Any]:
        """Make RPC request to Solana node."""
        client = await self._get_http_client()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        try:
            # Handle both httpx and aiohttp
            if hasattr(client, "post"):
                # httpx
                response = await client.post(self.rpc_url, json=payload)
                data = response.json()
            else:
                # aiohttp
                async with client.post(self.rpc_url, json=payload) as response:
                    data = await response.json()

            if "error" in data:
                raise SimulationError(
                    data["error"].get("message", "RPC error"),
                    data["error"].get("code"),
                )

            return data.get("result", {})

        except Exception as e:
            logger.error(f"RPC request failed: {e}")
            raise SimulationError(f"RPC request failed: {e}")

    async def simulate_transaction(
        self,
        transaction_base64: str,
        commitment: str = "confirmed",
        replace_blockhash: bool = True,
    ) -> SimulationResult:
        """
        Simulate a serialized transaction.

        Args:
            transaction_base64: Base64-encoded transaction
            commitment: Commitment level (processed, confirmed, finalized)
            replace_blockhash: Replace blockhash with recent one

        Returns:
            SimulationResult with simulation outcome

        Reference:
            https://solana.com/docs/rpc/http/simulatetransaction
        """
        start_time = time.time()
        self._stats["simulations"] += 1

        config = {
            "commitment": commitment,
            "encoding": "base64",
            "replaceRecentBlockhash": replace_blockhash,
        }

        try:
            result = await self._rpc_request(
                "simulateTransaction",
                [transaction_base64, config]
            )

            elapsed = (time.time() - start_time) * 1000
            value = result.get("value", {})

            # Check for errors
            err = value.get("err")
            logs = value.get("logs", [])
            compute_units = value.get("unitsConsumed", 0)

            risks = []
            if err is not None:
                self._stats["failed"] += 1
                risks.append(RiskAssessment(
                    factor=RiskFactor.SIMULATION_FAILED,
                    level=RiskLevel.CRITICAL,
                    description=f"Transaction simulation failed: {err}",
                    raw_data={"error": err},
                ))

                # Analyze error type
                if "InsufficientFunds" in str(err):
                    risks.append(RiskAssessment(
                        factor=RiskFactor.INSUFFICIENT_FUNDS,
                        level=RiskLevel.CRITICAL,
                        description="Insufficient funds for transaction",
                    ))
                elif "ComputationalBudgetExceeded" in str(err):
                    risks.append(RiskAssessment(
                        factor=RiskFactor.COMPUTE_EXCEEDED,
                        level=RiskLevel.HIGH,
                        description="Compute budget exceeded",
                    ))
            else:
                self._stats["successful"] += 1

            # Determine overall risk level
            max_risk = RiskLevel.NONE
            for risk in risks:
                if risk.level > max_risk:
                    max_risk = risk.level

            is_safe = err is None and max_risk < RiskLevel.HIGH

            return SimulationResult(
                success=err is None,
                is_safe=is_safe,
                risk_level=max_risk,
                risks=risks,
                logs=logs,
                compute_units=compute_units,
                error=str(err) if err else None,
                raw_response=result,
                simulation_time_ms=elapsed,
            )

        except SimulationError:
            raise
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            self._stats["failed"] += 1
            return SimulationResult(
                success=False,
                is_safe=False,
                risk_level=RiskLevel.CRITICAL,
                risks=[RiskAssessment(
                    factor=RiskFactor.SIMULATION_FAILED,
                    level=RiskLevel.CRITICAL,
                    description=f"Simulation error: {e}",
                )],
                error=str(e),
                simulation_time_ms=(time.time() - start_time) * 1000,
            )

    async def simulate_swap(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        check_token_security: bool = True,
    ) -> SwapSimulationResult:
        """
        Simulate a token swap using Jupiter.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Input amount in smallest units (lamports for SOL)
            slippage_bps: Slippage tolerance in basis points
            check_token_security: Whether to check token security via GoPlus

        Returns:
            SwapSimulationResult with quote and risk analysis

        Reference:
            https://dev.jup.ag/docs/swap-api
        """
        start_time = time.time()
        self._stats["simulations"] += 1
        risks: List[RiskAssessment] = []

        try:
            # Get Jupiter quote
            client = await self._get_http_client()

            quote_params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": str(slippage_bps),
                "restrictIntermediateTokens": "true",
            }

            quote_url = f"{self.JUPITER_QUOTE_URL}?{'&'.join(f'{k}={v}' for k, v in quote_params.items())}"

            if hasattr(client, "get"):
                response = await client.get(quote_url)
                quote_data = response.json()
            else:
                async with client.get(quote_url) as response:
                    quote_data = await response.json()

            # Check for quote errors - Jupiter API returns "error" OR "code" field
            if "error" in quote_data or "code" in quote_data:
                error_msg = (
                    quote_data.get("error")
                    or quote_data.get("message")
                    or f"API error code: {quote_data.get('code')}"
                )
                return SwapSimulationResult(
                    success=False,
                    is_safe=False,
                    risk_level=RiskLevel.CRITICAL,
                    risks=[RiskAssessment(
                        factor=RiskFactor.SIMULATION_FAILED,
                        level=RiskLevel.CRITICAL,
                        description=f"Quote failed: {error_msg}",
                    )],
                    error=error_msg,
                    input_mint=input_mint,
                    output_mint=output_mint,
                    input_amount=amount,
                    raw_response=quote_data,
                    simulation_time_ms=(time.time() - start_time) * 1000,
                )

            # Extract quote info
            out_amount = int(quote_data.get("outAmount", 0))
            other_amount_threshold = int(quote_data.get("otherAmountThreshold", 0))
            price_impact_pct = float(quote_data.get("priceImpactPct", 0))
            slippage_bps_actual = int(quote_data.get("slippageBps", slippage_bps))

            # Analyze slippage
            if slippage_bps_actual > self.max_slippage_bps:
                risks.append(RiskAssessment(
                    factor=RiskFactor.HIGH_SLIPPAGE,
                    level=RiskLevel.HIGH,
                    description=f"High slippage: {slippage_bps_actual} bps (max: {self.max_slippage_bps})",
                    raw_data={"slippage_bps": slippage_bps_actual},
                ))

            # Analyze price impact
            if price_impact_pct > 5.0:
                risks.append(RiskAssessment(
                    factor=RiskFactor.PRICE_IMPACT,
                    level=RiskLevel.HIGH,
                    description=f"High price impact: {price_impact_pct:.2f}%",
                    raw_data={"price_impact_pct": price_impact_pct},
                ))
            elif price_impact_pct > 1.0:
                risks.append(RiskAssessment(
                    factor=RiskFactor.PRICE_IMPACT,
                    level=RiskLevel.MEDIUM,
                    description=f"Moderate price impact: {price_impact_pct:.2f}%",
                    raw_data={"price_impact_pct": price_impact_pct},
                ))

            # Check token security for output token
            if check_token_security and output_mint not in self.SAFE_TOKENS:
                token_security = await self.check_token_security(output_mint)
                risks.extend(token_security.risks)

            # Determine overall risk
            max_risk = RiskLevel.NONE
            for risk in risks:
                if risk.level > max_risk:
                    max_risk = risk.level

            if risks:
                self._stats["risks_detected"] += len(risks)

            is_safe = max_risk < RiskLevel.HIGH
            self._stats["successful"] += 1

            return SwapSimulationResult(
                success=True,
                is_safe=is_safe,
                risk_level=max_risk,
                risks=risks,
                input_mint=input_mint,
                output_mint=output_mint,
                input_amount=amount,
                expected_output=out_amount,
                minimum_output=other_amount_threshold,
                slippage_bps=slippage_bps_actual,
                price_impact_pct=price_impact_pct,
                route_info=quote_data.get("routePlan", {}),
                raw_response=quote_data,
                simulation_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Swap simulation failed: {e}")
            self._stats["failed"] += 1
            return SwapSimulationResult(
                success=False,
                is_safe=False,
                risk_level=RiskLevel.CRITICAL,
                risks=[RiskAssessment(
                    factor=RiskFactor.SIMULATION_FAILED,
                    level=RiskLevel.CRITICAL,
                    description=f"Swap simulation error: {e}",
                )],
                error=str(e),
                input_mint=input_mint,
                output_mint=output_mint,
                input_amount=amount,
                simulation_time_ms=(time.time() - start_time) * 1000,
            )

    async def check_token_security(
        self,
        token_address: str,
        use_cache: bool = True,
    ) -> TokenSecurityResult:
        """
        Check token security using GoPlus API.

        Args:
            token_address: Token mint address
            use_cache: Whether to use cached results

        Returns:
            TokenSecurityResult with security analysis

        Reference:
            https://docs.gopluslabs.io/reference/solanatokensecurityusingget
        """
        # Check cache first
        if use_cache and token_address in self._token_cache:
            cached, timestamp = self._token_cache[token_address]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Using cached security result for {token_address[:8]}...")
                return cached

        # Skip check for known safe tokens
        if token_address in self.SAFE_TOKENS:
            result = TokenSecurityResult(
                token_address=token_address,
                is_safe=True,
                risk_level=RiskLevel.NONE,
            )
            self._token_cache[token_address] = (result, time.time())
            return result

        try:
            client = await self._get_http_client()

            url = f"{self.GOPLUS_SOLANA_URL}?contract_addresses={token_address}"
            headers = {}
            if self.goplus_api_key:
                headers["Authorization"] = f"Bearer {self.goplus_api_key}"

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
                    raw_data=data,
                )

            # Parse response - handle None result gracefully
            result = data.get("result") or {}
            result_data = result.get(token_address.lower(), {})

            if not result_data:
                # Token not found in GoPlus database
                return TokenSecurityResult(
                    token_address=token_address,
                    is_safe=True,  # Assume safe if not in database
                    risk_level=RiskLevel.LOW,
                    risks=[RiskAssessment(
                        factor=RiskFactor.LOW_LIQUIDITY,
                        level=RiskLevel.LOW,
                        description="Token not found in security database",
                    )],
                )

            risks: List[RiskAssessment] = []

            # Check freeze authority
            freeze_authority = result_data.get("freeze_authority")
            has_freeze = freeze_authority is not None and freeze_authority != ""

            if has_freeze:
                risks.append(RiskAssessment(
                    factor=RiskFactor.FREEZE_AUTHORITY,
                    level=RiskLevel.HIGH,
                    description="Token has active freeze authority - funds can be frozen",
                    raw_data={"freeze_authority": freeze_authority},
                ))

            # Check mint authority
            mint_authority = result_data.get("mint_authority")
            has_mint = mint_authority is not None and mint_authority != ""

            if has_mint:
                risks.append(RiskAssessment(
                    factor=RiskFactor.MINT_AUTHORITY,
                    level=RiskLevel.MEDIUM,
                    description="Token has active mint authority - supply can increase",
                    raw_data={"mint_authority": mint_authority},
                ))

            # Check for honeypot indicators
            is_honeypot = result_data.get("is_honeypot", False)
            honeypot_reason = None

            if is_honeypot:
                honeypot_reason = result_data.get("honeypot_reason", "Unknown")
                risks.append(RiskAssessment(
                    factor=RiskFactor.HONEYPOT,
                    level=RiskLevel.CRITICAL,
                    description=f"Token is a honeypot: {honeypot_reason}",
                    raw_data={"reason": honeypot_reason},
                ))

            # Check taxes
            buy_tax = float(result_data.get("buy_tax", 0))
            sell_tax = float(result_data.get("sell_tax", 0))
            transfer_tax = float(result_data.get("transfer_tax", 0))

            if sell_tax > 10:
                risks.append(RiskAssessment(
                    factor=RiskFactor.TRANSFER_TAX,
                    level=RiskLevel.HIGH,
                    description=f"High sell tax: {sell_tax}%",
                    raw_data={"sell_tax": sell_tax},
                ))
            elif sell_tax > 5:
                risks.append(RiskAssessment(
                    factor=RiskFactor.TRANSFER_TAX,
                    level=RiskLevel.MEDIUM,
                    description=f"Moderate sell tax: {sell_tax}%",
                    raw_data={"sell_tax": sell_tax},
                ))

            # Determine overall risk
            max_risk = RiskLevel.NONE
            for risk in risks:
                if risk.level > max_risk:
                    max_risk = risk.level

            result = TokenSecurityResult(
                token_address=token_address,
                is_safe=max_risk < RiskLevel.HIGH and not is_honeypot,
                risk_level=max_risk,
                risks=risks,
                has_freeze_authority=has_freeze,
                has_mint_authority=has_mint,
                freeze_authority_address=freeze_authority if has_freeze else None,
                mint_authority_address=mint_authority if has_mint else None,
                buy_tax_pct=buy_tax,
                sell_tax_pct=sell_tax,
                transfer_tax_pct=transfer_tax,
                total_supply=int(result_data.get("total_supply", 0)),
                holder_count=int(result_data.get("holder_count", 0)),
                lp_locked_pct=float(result_data.get("lp_locked_pct", 0)),
                is_honeypot=is_honeypot,
                honeypot_reason=honeypot_reason,
                raw_data=result_data,
            )

            # Cache result
            self._token_cache[token_address] = (result, time.time())

            return result

        except Exception as e:
            logger.error(f"Token security check failed: {e}")
            return TokenSecurityResult(
                token_address=token_address,
                is_safe=False,
                risk_level=RiskLevel.MEDIUM,
                risks=[RiskAssessment(
                    factor=RiskFactor.SIMULATION_FAILED,
                    level=RiskLevel.MEDIUM,
                    description=f"Security check failed: {e}",
                )],
            )

    async def pre_flight_check(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> SimulationResult:
        """
        High-level pre-flight check for common operations.

        Args:
            action: Action type (swap, transfer, stake, etc.)
            params: Action parameters

        Returns:
            SimulationResult with safety assessment
        """
        action_lower = action.lower()

        if action_lower == "swap":
            return await self.simulate_swap(
                input_mint=params.get("input_mint", params.get("from_token", "")),
                output_mint=params.get("output_mint", params.get("to_token", "")),
                amount=params.get("amount", 0),
                slippage_bps=params.get("slippage_bps", 50),
            )

        elif action_lower == "transfer":
            # For transfers, just check recipient token security
            recipient_token = params.get("token", params.get("mint", ""))
            if recipient_token and recipient_token not in self.SAFE_TOKENS:
                security = await self.check_token_security(recipient_token)
                return SimulationResult(
                    success=True,
                    is_safe=security.is_safe,
                    risk_level=security.risk_level,
                    risks=security.risks,
                )
            return SimulationResult(
                success=True,
                is_safe=True,
                risk_level=RiskLevel.NONE,
            )

        elif action_lower in ("stake", "unstake"):
            # Basic validation for staking
            return SimulationResult(
                success=True,
                is_safe=True,
                risk_level=RiskLevel.LOW,
            )

        else:
            # Unknown action - return neutral result
            return SimulationResult(
                success=True,
                is_safe=True,
                risk_level=RiskLevel.LOW,
                risks=[RiskAssessment(
                    factor=RiskFactor.SIMULATION_FAILED,
                    level=RiskLevel.LOW,
                    description=f"Unknown action type: {action}",
                )],
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        return {
            **self._stats,
            "cache_size": len(self._token_cache),
        }

    def clear_cache(self) -> None:
        """Clear token security cache."""
        self._token_cache.clear()
        logger.debug("Token security cache cleared")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client is not None:
            if hasattr(self._http_client, "aclose"):
                await self._http_client.aclose()
            elif hasattr(self._http_client, "close"):
                await self._http_client.close()
            self._http_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
