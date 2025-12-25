"""
Unit tests for Pre-flight Transaction Simulator integration.

Tests cover:
- TransactionSimulator (simulate_swap, check_token_security)
- PreflightValidator (validate_swap, validate_transfer)
- JupiterAnalyzer, GoPlusAnalyzer
- API error handling (401, 500, etc.)
- RiskLevel and RiskFactor enums
- SlippageAnalyzer, LiquidityAnalyzer
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict


class TestImports:
    """Test module imports and exports."""

    def test_main_imports(self):
        """Test that main module imports work."""
        from sentinelseed.integrations.preflight import (
            TransactionSimulator,
            SimulationResult,
            SwapSimulationResult,
            TokenSecurityResult,
            SimulationError,
            RiskLevel,
            RiskFactor,
        )
        assert TransactionSimulator is not None
        assert SimulationResult is not None
        assert RiskLevel is not None

    def test_analyzer_imports(self):
        """Test that analyzer imports work."""
        from sentinelseed.integrations.preflight import (
            JupiterAnalyzer,
            GoPlusAnalyzer,
            TokenRiskAnalyzer,
            SlippageAnalyzer,
            LiquidityAnalyzer,
        )
        assert JupiterAnalyzer is not None
        assert GoPlusAnalyzer is not None

    def test_wrapper_imports(self):
        """Test that wrapper imports work."""
        from sentinelseed.integrations.preflight import (
            PreflightValidator,
            PreflightResult,
            create_preflight_tools,
        )
        assert PreflightValidator is not None
        assert PreflightResult is not None

    def test_version(self):
        """Test that version is defined."""
        from sentinelseed.integrations.preflight import __version__
        assert __version__ == "1.0.0"


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        from sentinelseed.integrations.preflight import RiskLevel
        assert RiskLevel.NONE.value == 0
        assert RiskLevel.LOW.value == 1
        assert RiskLevel.MEDIUM.value == 2
        assert RiskLevel.HIGH.value == 3
        assert RiskLevel.CRITICAL.value == 4

    def test_risk_level_comparison(self):
        """Test RiskLevel comparison operators."""
        from sentinelseed.integrations.preflight import RiskLevel
        assert RiskLevel.LOW < RiskLevel.HIGH
        assert RiskLevel.HIGH > RiskLevel.LOW
        assert RiskLevel.MEDIUM <= RiskLevel.HIGH
        assert RiskLevel.CRITICAL >= RiskLevel.HIGH


class TestRiskFactor:
    """Test RiskFactor enum."""

    def test_risk_factor_values(self):
        """Test RiskFactor enum values."""
        from sentinelseed.integrations.preflight import RiskFactor
        assert RiskFactor.HONEYPOT.value == "honeypot"
        assert RiskFactor.HIGH_SLIPPAGE.value == "high_slippage"
        assert RiskFactor.SIMULATION_FAILED.value == "simulation_failed"


class TestTransactionSimulator:
    """Test TransactionSimulator class."""

    def test_init_default(self):
        """Test default initialization."""
        from sentinelseed.integrations.preflight import TransactionSimulator
        sim = TransactionSimulator()
        assert sim.rpc_url == TransactionSimulator.DEFAULT_MAINNET_RPC
        assert sim.max_slippage_bps == 500
        assert sim.cache_ttl == 300

    def test_init_custom(self):
        """Test custom initialization."""
        from sentinelseed.integrations.preflight import TransactionSimulator
        sim = TransactionSimulator(
            rpc_url="https://custom.rpc.com",
            max_slippage_bps=100,
            cache_ttl_seconds=60,
        )
        assert sim.rpc_url == "https://custom.rpc.com"
        assert sim.max_slippage_bps == 100
        assert sim.cache_ttl == 60

    def test_safe_tokens_exist(self):
        """Test that safe tokens list exists."""
        from sentinelseed.integrations.preflight import TransactionSimulator
        assert len(TransactionSimulator.SAFE_TOKENS) > 0
        assert "So11111111111111111111111111111111111111112" in TransactionSimulator.SAFE_TOKENS

    def test_get_stats(self):
        """Test get_stats method."""
        from sentinelseed.integrations.preflight import TransactionSimulator
        sim = TransactionSimulator()
        stats = sim.get_stats()
        assert "simulations" in stats
        assert "successful" in stats
        assert "failed" in stats
        assert "cache_size" in stats

    def test_clear_cache(self):
        """Test clear_cache method."""
        from sentinelseed.integrations.preflight import TransactionSimulator
        sim = TransactionSimulator()
        sim._token_cache["test"] = ("value", 0)
        assert len(sim._token_cache) == 1
        sim.clear_cache()
        assert len(sim._token_cache) == 0


class TestSimulateSwapMocked:
    """Test simulate_swap with mocked HTTP client."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        mock = MagicMock()
        mock.get = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_simulate_swap_success(self, mock_http_client):
        """Test successful swap simulation."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel

        # Mock successful Jupiter response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "outAmount": "195000000",
            "otherAmountThreshold": "194000000",
            "slippageBps": 50,
            "priceImpactPct": "0.1",
            "routePlan": [],
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client)
        result = await sim.simulate_swap(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1_000_000_000,
            check_token_security=False,
        )

        assert result.success is True
        assert result.expected_output == 195000000
        assert result.slippage_bps == 50

    @pytest.mark.asyncio
    async def test_simulate_swap_api_error_code(self, mock_http_client):
        """Test swap simulation with API error code (C002 bug fix verification)."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel

        # Mock Jupiter API returning error with "code" field
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 401,
            "message": "Unauthorized",
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client)
        result = await sim.simulate_swap(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1_000_000_000,
            check_token_security=False,
        )

        # CRITICAL: Must return success=False and is_safe=False for API errors
        assert result.success is False
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert "Unauthorized" in result.error

    @pytest.mark.asyncio
    async def test_simulate_swap_api_error_field(self, mock_http_client):
        """Test swap simulation with API error field."""
        from sentinelseed.integrations.preflight import TransactionSimulator

        # Mock Jupiter API returning error with "error" field
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "No route found",
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client)
        result = await sim.simulate_swap(
            input_mint="INVALID",
            output_mint="INVALID",
            amount=1_000_000_000,
            check_token_security=False,
        )

        assert result.success is False
        assert result.is_safe is False
        assert "No route found" in result.error

    @pytest.mark.asyncio
    async def test_simulate_swap_high_slippage(self, mock_http_client):
        """Test swap simulation with high slippage."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "outAmount": "100000000",
            "slippageBps": 1000,  # 10% slippage
            "priceImpactPct": "0.5",
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client, max_slippage_bps=500)
        result = await sim.simulate_swap(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1_000_000_000,
            check_token_security=False,
        )

        assert result.success is True
        assert result.is_safe is False  # High slippage should mark as unsafe
        assert result.risk_level >= RiskLevel.HIGH


class TestCheckTokenSecurityMocked:
    """Test check_token_security with mocked HTTP client."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        mock = MagicMock()
        mock.get = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_safe_token_bypass(self):
        """Test that safe tokens skip API check."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel

        sim = TransactionSimulator()
        # USDC is in SAFE_TOKENS
        result = await sim.check_token_security(
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        )

        assert result.is_safe is True
        assert result.risk_level == RiskLevel.NONE

    @pytest.mark.asyncio
    async def test_token_security_honeypot(self, mock_http_client):
        """Test detection of honeypot token."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel, RiskFactor

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "testtoken123": {
                    "is_honeypot": True,
                    "honeypot_reason": "Sell disabled",
                }
            }
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client)
        result = await sim.check_token_security("TestToken123")

        assert result.is_safe is False
        assert result.is_honeypot is True
        assert any(r.factor == RiskFactor.HONEYPOT for r in result.risks)

    @pytest.mark.asyncio
    async def test_token_security_none_result(self, mock_http_client):
        """Test handling of None result from API (M007 bug fix verification)."""
        from sentinelseed.integrations.preflight import TransactionSimulator

        mock_response = MagicMock()
        # API returns None for result field
        mock_response.json.return_value = {
            "result": None
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client)
        # Should not raise AttributeError
        result = await sim.check_token_security("UNKNOWN_TOKEN")

        assert result.token_address == "UNKNOWN_TOKEN"
        assert result.is_safe is True  # Not in database = assume safe

    @pytest.mark.asyncio
    async def test_token_with_freeze_authority(self, mock_http_client):
        """Test detection of freeze authority."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel, RiskFactor

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "testtoken": {
                    "freeze_authority": "AuthorityAddress123",
                }
            }
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client)
        result = await sim.check_token_security("TestToken")

        assert result.has_freeze_authority is True
        assert any(r.factor == RiskFactor.FREEZE_AUTHORITY for r in result.risks)

    @pytest.mark.asyncio
    async def test_caching(self):
        """Test token security caching for safe tokens."""
        from sentinelseed.integrations.preflight import TransactionSimulator

        sim = TransactionSimulator()

        # Use a known safe token (USDC) - will be cached without HTTP call
        usdc = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

        # First call
        result1 = await sim.check_token_security(usdc, use_cache=True)
        assert usdc in sim._token_cache

        # Second call should use cache
        result2 = await sim.check_token_security(usdc, use_cache=True)

        # Results should be equivalent
        assert result1.is_safe == result2.is_safe
        assert result1.token_address == result2.token_address

    @pytest.mark.asyncio
    async def test_check_token_goplus_api_error(self, mock_http_client):
        """Test GoPlus API error in TransactionSimulator (N003 bug fix verification)."""
        from sentinelseed.integrations.preflight import TransactionSimulator

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "message": "Rate limit exceeded",
        }
        mock_http_client.get.return_value = mock_response

        sim = TransactionSimulator(http_client=mock_http_client)
        result = await sim.check_token_security("SOME_TOKEN")

        # CRITICAL: Must return is_safe=False for API errors
        assert result.is_safe is False
        assert "Rate limit exceeded" in result.risks[0].description


class TestJupiterAnalyzer:
    """Test JupiterAnalyzer class."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        mock = MagicMock()
        mock.get = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_get_quote_success(self, mock_http_client):
        """Test successful quote."""
        from sentinelseed.integrations.preflight import JupiterAnalyzer

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "outAmount": "195000000",
            "otherAmountThreshold": "194000000",
            "slippageBps": 50,
            "priceImpactPct": "0.1",
        }
        mock_http_client.get.return_value = mock_response

        analyzer = JupiterAnalyzer(http_client=mock_http_client)
        result = await analyzer.get_quote(
            input_mint="SOL",
            output_mint="USDC",
            amount=1_000_000_000,
        )

        assert result.success is True
        assert result.output_amount == 195000000

    @pytest.mark.asyncio
    async def test_get_quote_api_error_code(self, mock_http_client):
        """Test quote with API error code (N002 bug fix verification)."""
        from sentinelseed.integrations.preflight import JupiterAnalyzer

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 500,
            "message": "Internal Server Error",
        }
        mock_http_client.get.return_value = mock_response

        analyzer = JupiterAnalyzer(http_client=mock_http_client)
        result = await analyzer.get_quote(
            input_mint="SOL",
            output_mint="USDC",
            amount=1_000_000_000,
        )

        # CRITICAL: Must return success=False for API errors
        assert result.success is False
        assert "Internal Server Error" in result.error

    def test_analyze_quote_high_slippage(self):
        """Test slippage analysis."""
        from sentinelseed.integrations.preflight import JupiterAnalyzer, RiskLevel, RiskFactor
        from sentinelseed.integrations.preflight.analyzers import QuoteResult

        analyzer = JupiterAnalyzer()
        quote = QuoteResult(
            success=True,
            input_mint="SOL",
            output_mint="USDC",
            input_amount=1000,
            output_amount=100,
            minimum_output=95,
            slippage_bps=1000,  # 10% - CRITICAL
            price_impact_pct=0.1,
        )

        risks = analyzer.analyze_quote(quote)
        assert len(risks) > 0
        assert any(r.factor == RiskFactor.HIGH_SLIPPAGE for r in risks)
        assert any(r.level >= RiskLevel.HIGH for r in risks)

    def test_get_optimal_slippage(self):
        """Test optimal slippage recommendation."""
        from sentinelseed.integrations.preflight import JupiterAnalyzer
        from sentinelseed.integrations.preflight.analyzers import QuoteResult

        analyzer = JupiterAnalyzer()
        quote = QuoteResult(
            success=True,
            input_mint="SOL",
            output_mint="USDC",
            input_amount=1000,
            output_amount=100,
            minimum_output=95,
            slippage_bps=50,
            price_impact_pct=0.1,
        )

        slippage = analyzer.get_optimal_slippage(quote, trade_urgency="high")
        assert slippage > quote.slippage_bps  # Should increase for high urgency


class TestGoPlusAnalyzer:
    """Test GoPlusAnalyzer class."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        mock = MagicMock()
        mock.get = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_check_token_none_result(self, mock_http_client):
        """Test handling of None result (N001 bug fix verification)."""
        from sentinelseed.integrations.preflight import GoPlusAnalyzer

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": None}
        mock_http_client.get.return_value = mock_response

        analyzer = GoPlusAnalyzer(http_client=mock_http_client)
        # Should not raise AttributeError
        result = await analyzer.check_token("UNKNOWN")

        assert result.is_safe is True  # Default safe if not in database

    @pytest.mark.asyncio
    async def test_check_token_high_sell_tax(self, mock_http_client):
        """Test detection of high sell tax."""
        from sentinelseed.integrations.preflight import GoPlusAnalyzer, RiskFactor

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "scamtoken": {
                    "sell_tax": 50,  # 50% sell tax
                }
            }
        }
        mock_http_client.get.return_value = mock_response

        analyzer = GoPlusAnalyzer(http_client=mock_http_client)
        result = await analyzer.check_token("ScamToken")

        assert result.sell_tax_pct == 50
        assert any(r.factor == RiskFactor.TRANSFER_TAX for r in result.risks)

    @pytest.mark.asyncio
    async def test_check_token_api_error_code_zero(self, mock_http_client):
        """Test GoPlus API error with code=0 (N003 bug fix verification)."""
        from sentinelseed.integrations.preflight import GoPlusAnalyzer

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "message": "Invalid token address",
        }
        mock_http_client.get.return_value = mock_response

        analyzer = GoPlusAnalyzer(http_client=mock_http_client)
        result = await analyzer.check_token("INVALID")

        # CRITICAL: Must return is_safe=False for API errors
        assert result.is_safe is False
        assert "Invalid token address" in result.risks[0].description


class TestSlippageAnalyzer:
    """Test SlippageAnalyzer class."""

    def test_analyze_high_slippage(self):
        """Test high slippage detection."""
        from sentinelseed.integrations.preflight import SlippageAnalyzer, RiskLevel

        analyzer = SlippageAnalyzer(max_slippage_bps=500)
        risk_level, risks = analyzer.analyze(
            quoted_slippage=600,  # Above max
            price_impact=0.5,
        )

        assert risk_level >= RiskLevel.MEDIUM
        assert len(risks) > 0

    def test_analyze_high_price_impact(self):
        """Test high price impact detection."""
        from sentinelseed.integrations.preflight import SlippageAnalyzer, RiskLevel, RiskFactor

        analyzer = SlippageAnalyzer()
        risk_level, risks = analyzer.analyze(
            quoted_slippage=50,
            price_impact=10.0,  # Very high
        )

        assert risk_level == RiskLevel.HIGH
        assert any(r.factor == RiskFactor.PRICE_IMPACT for r in risks)

    def test_recommend_slippage(self):
        """Test slippage recommendation."""
        from sentinelseed.integrations.preflight import SlippageAnalyzer

        analyzer = SlippageAnalyzer(max_slippage_bps=500)

        # Low price impact = low slippage recommendation
        low_rec = analyzer.recommend_slippage(price_impact=0.1)
        assert low_rec <= 100

        # High price impact = higher slippage recommendation
        high_rec = analyzer.recommend_slippage(price_impact=6.0)
        assert high_rec >= 200


class TestLiquidityAnalyzer:
    """Test LiquidityAnalyzer class."""

    def test_analyze_low_liquidity(self):
        """Test low liquidity detection."""
        from sentinelseed.integrations.preflight import LiquidityAnalyzer, RiskLevel, RiskFactor

        analyzer = LiquidityAnalyzer()
        risk_level, risks = analyzer.analyze_liquidity(
            liquidity_usd=5000,  # Very low
            trade_size_usd=1000,
        )

        assert risk_level == RiskLevel.HIGH
        assert any(r.factor == RiskFactor.LOW_LIQUIDITY for r in risks)

    def test_analyze_large_trade_ratio(self):
        """Test large trade vs liquidity detection."""
        from sentinelseed.integrations.preflight import LiquidityAnalyzer, RiskLevel, RiskFactor

        analyzer = LiquidityAnalyzer()
        risk_level, risks = analyzer.analyze_liquidity(
            liquidity_usd=100_000,
            trade_size_usd=15_000,  # 15% of pool
        )

        assert risk_level == RiskLevel.HIGH
        assert any(r.factor == RiskFactor.ILLIQUID_POOL for r in risks)

    def test_is_healthy(self):
        """Test is_healthy check."""
        from sentinelseed.integrations.preflight import LiquidityAnalyzer

        analyzer = LiquidityAnalyzer()

        # Healthy pool
        assert analyzer.is_healthy(
            liquidity_usd=1_000_000,
            trade_size_usd=5_000,
        ) is True

        # Unhealthy - low liquidity
        assert analyzer.is_healthy(
            liquidity_usd=100_000,
            trade_size_usd=5_000,
        ) is False


class TestPreflightValidator:
    """Test PreflightValidator class."""

    def test_init(self):
        """Test initialization."""
        from sentinelseed.integrations.preflight import PreflightValidator

        validator = PreflightValidator(
            max_transfer=50.0,
            max_slippage_bps=300,
        )
        assert validator.strict_mode is False
        assert validator.simulator is not None

    @pytest.mark.asyncio
    async def test_validate_swap_with_mock(self):
        """Test validate_swap with mocked simulator."""
        from sentinelseed.integrations.preflight import PreflightValidator, RiskLevel
        from sentinelseed.integrations.preflight.simulator import SwapSimulationResult

        validator = PreflightValidator()

        # Mock simulator
        mock_result = SwapSimulationResult(
            success=True,
            is_safe=True,
            risk_level=RiskLevel.LOW,
            input_mint="SOL",
            output_mint="USDC",
            input_amount=1000,
            expected_output=195,
            slippage_bps=50,
            price_impact_pct=0.1,
        )
        validator.simulator.simulate_swap = AsyncMock(return_value=mock_result)

        result = await validator.validate_swap(
            input_mint="SOL",
            output_mint="USDC",
            amount=1000,
            purpose="Test swap",
        )

        assert result.should_proceed is True
        assert result.simulation_passed is True
        assert result.expected_output == 195

    @pytest.mark.asyncio
    async def test_validate_with_simulation_dispatch(self):
        """Test validate_with_simulation dispatches correctly."""
        from sentinelseed.integrations.preflight import PreflightValidator, RiskLevel
        from sentinelseed.integrations.preflight.simulator import SwapSimulationResult

        validator = PreflightValidator()

        # Mock simulator for swap
        mock_result = SwapSimulationResult(
            success=True,
            is_safe=True,
            risk_level=RiskLevel.LOW,
            input_mint="SOL",
            output_mint="USDC",
            input_amount=1000,
            expected_output=195,
        )
        validator.simulator.simulate_swap = AsyncMock(return_value=mock_result)

        result = await validator.validate_with_simulation(
            action="swap",
            input_mint="SOL",
            output_mint="USDC",
            amount=1000,
        )

        assert result.should_proceed is True
        validator.simulator.simulate_swap.assert_awaited_once()


class TestPreflightResult:
    """Test PreflightResult dataclass."""

    def test_preflight_result_fields(self):
        """Test PreflightResult has all expected fields."""
        from sentinelseed.integrations.preflight import PreflightResult

        result = PreflightResult(
            should_proceed=True,
            risk_level="LOW",
            is_safe=True,
            validation_passed=True,
        )

        assert result.should_proceed is True
        assert result.risk_level == "LOW"
        assert result.validation_concerns == []
        assert result.simulation_risks == []
        assert result.recommendations == []


class TestSimulationResult:
    """Test SimulationResult and SwapSimulationResult dataclasses."""

    def test_simulation_result_recommendations(self):
        """Test recommendations property."""
        from sentinelseed.integrations.preflight import (
            SimulationResult,
            RiskLevel,
            RiskFactor,
        )
        from sentinelseed.integrations.preflight.simulator import RiskAssessment

        result = SimulationResult(
            success=True,
            is_safe=False,
            risk_level=RiskLevel.HIGH,
            risks=[
                RiskAssessment(
                    factor=RiskFactor.HONEYPOT,
                    level=RiskLevel.HIGH,
                    description="Token is honeypot",
                ),
                RiskAssessment(
                    factor=RiskFactor.HIGH_SLIPPAGE,
                    level=RiskLevel.HIGH,
                    description="High slippage",
                ),
            ],
        )

        recs = result.recommendations
        assert len(recs) == 2
        assert any("honeypot" in r.lower() for r in recs)
        assert any("slippage" in r.lower() for r in recs)


class TestSimulationError:
    """Test SimulationError exception."""

    def test_simulation_error(self):
        """Test SimulationError with code."""
        from sentinelseed.integrations.preflight import SimulationError

        error = SimulationError("Test error", error_code="ERR001")
        assert str(error) == "Test error"
        assert error.error_code == "ERR001"


class TestContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    async def test_simulator_context_manager(self):
        """Test TransactionSimulator as context manager."""
        from sentinelseed.integrations.preflight import TransactionSimulator

        async with TransactionSimulator() as sim:
            assert sim is not None
            assert isinstance(sim, TransactionSimulator)

    @pytest.mark.asyncio
    async def test_validator_context_manager(self):
        """Test PreflightValidator as context manager."""
        from sentinelseed.integrations.preflight import PreflightValidator

        async with PreflightValidator() as validator:
            assert validator is not None
            assert isinstance(validator, PreflightValidator)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_simulate_swap_network_error(self):
        """Test handling of network errors."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        sim = TransactionSimulator(http_client=mock_client)
        result = await sim.simulate_swap(
            input_mint="SOL",
            output_mint="USDC",
            amount=1000,
            check_token_security=False,
        )

        assert result.success is False
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_check_token_network_error(self):
        """Test handling of network errors in token check."""
        from sentinelseed.integrations.preflight import TransactionSimulator, RiskLevel

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

        sim = TransactionSimulator(http_client=mock_client)
        result = await sim.check_token_security("UNKNOWN_TOKEN")

        assert result.is_safe is False
        assert result.risk_level == RiskLevel.MEDIUM
        assert "Connection refused" in str(result.risks[0].description)

    def test_zero_liquidity_analysis(self):
        """Test liquidity analysis with zero liquidity."""
        from sentinelseed.integrations.preflight import LiquidityAnalyzer

        analyzer = LiquidityAnalyzer()
        # Should not raise division by zero
        risk_level, risks = analyzer.analyze_liquidity(
            liquidity_usd=0,
            trade_size_usd=1000,
        )

        assert risk_level is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
