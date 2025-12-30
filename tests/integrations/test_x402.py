"""
Comprehensive test suite for x402 Payment Validation Integration.

Tests cover:
- Types (PaymentRiskLevel, PaymentDecision, THSPGate, etc.)
- Config (SpendingLimits, ValidationConfig, get_default_config)
- Validators (THSP gates: Truth, Harm, Scope, Purpose)
- Middleware (SentinelX402Middleware)
- None handling for all edge cases

Run with: pytest tests/integrations/test_x402.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Import types
from sentinelseed.integrations.coinbase.x402.types import (
    PaymentRiskLevel,
    PaymentDecision,
    THSPGate,
    THSPGateResult,
    PaymentValidationResult,
    PaymentRequirementsModel,
    SupportedNetwork,
    NETWORK_CHAIN_IDS,
    SpendingRecord,
    EndpointReputation,
)

# Import config
from sentinelseed.integrations.coinbase.x402.config import (
    SpendingLimits,
    ConfirmationThresholds,
    ValidationConfig,
    SentinelX402Config,
    get_default_config,
    KNOWN_USDC_CONTRACTS,
    KNOWN_USDT_CONTRACTS,
    SUSPICIOUS_URL_PATTERNS,
)

# Import validators
from sentinelseed.integrations.coinbase.x402.validators import (
    TruthGateValidator,
    HarmGateValidator,
    ScopeGateValidator,
    PurposeGateValidator,
    THSPPaymentValidator,
)

# Import middleware
from sentinelseed.integrations.coinbase.x402.middleware import (
    SentinelX402Middleware,
    PaymentBlockedError,
    PaymentRejectedError,
    PaymentConfirmationRequired,
    create_sentinel_x402_middleware,
)

# Import schemas
from sentinelseed.integrations.coinbase.x402.schemas import (
    ValidatePaymentSchema,
    GetSpendingSummarySchema,
    ConfigureSpendingLimitsSchema,
    SafeX402RequestSchema,
    CheckEndpointSafetySchema,
    GetAuditLogSchema,
    ResetSpendingSchema,
)


# =============================================================================
# Type Tests
# =============================================================================

class TestPaymentRiskLevel:
    """Tests for PaymentRiskLevel enum."""

    def test_values(self):
        """All risk levels should be defined."""
        assert PaymentRiskLevel.SAFE.value == "safe"
        assert PaymentRiskLevel.CAUTION.value == "caution"
        assert PaymentRiskLevel.HIGH.value == "high"
        assert PaymentRiskLevel.CRITICAL.value == "critical"
        assert PaymentRiskLevel.BLOCKED.value == "blocked"

    def test_comparison(self):
        """Risk levels should be comparable."""
        assert PaymentRiskLevel.SAFE < PaymentRiskLevel.CAUTION
        assert PaymentRiskLevel.CAUTION < PaymentRiskLevel.HIGH
        assert PaymentRiskLevel.HIGH < PaymentRiskLevel.CRITICAL
        assert PaymentRiskLevel.CRITICAL < PaymentRiskLevel.BLOCKED


class TestPaymentDecision:
    """Tests for PaymentDecision enum."""

    def test_values(self):
        """All decisions should be defined."""
        assert PaymentDecision.APPROVE.value == "approve"
        assert PaymentDecision.REQUIRE_CONFIRMATION.value == "require_confirmation"
        assert PaymentDecision.REJECT.value == "reject"
        assert PaymentDecision.BLOCK.value == "block"


class TestTHSPGate:
    """Tests for THSPGate enum."""

    def test_values(self):
        """All THSP gates should be defined."""
        assert THSPGate.TRUTH.value == "truth"
        assert THSPGate.HARM.value == "harm"
        assert THSPGate.SCOPE.value == "scope"
        assert THSPGate.PURPOSE.value == "purpose"


class TestSupportedNetwork:
    """Tests for SupportedNetwork enum."""

    def test_values(self):
        """All supported networks should be defined."""
        assert SupportedNetwork.BASE.value == "base"
        assert SupportedNetwork.BASE_SEPOLIA.value == "base-sepolia"
        assert SupportedNetwork.AVALANCHE.value == "avalanche"
        assert SupportedNetwork.AVALANCHE_FUJI.value == "avalanche-fuji"

    def test_chain_ids(self):
        """Chain IDs should be mapped correctly."""
        assert NETWORK_CHAIN_IDS[SupportedNetwork.BASE] == 8453
        assert NETWORK_CHAIN_IDS[SupportedNetwork.BASE_SEPOLIA] == 84532


class TestTHSPGateResult:
    """Tests for THSPGateResult dataclass."""

    def test_create_passed(self):
        """Should create passed result."""
        result = THSPGateResult(gate=THSPGate.TRUTH, passed=True)
        assert result.passed is True
        assert result.reason is None
        assert result.details is None

    def test_create_failed(self):
        """Should create failed result with reason."""
        result = THSPGateResult(
            gate=THSPGate.HARM,
            passed=False,
            reason="Blocked address",
            details={"address": "0x123"},
        )
        assert result.passed is False
        assert result.reason == "Blocked address"
        assert result.details == {"address": "0x123"}


class TestPaymentValidationResult:
    """Tests for PaymentValidationResult dataclass."""

    def test_is_approved_approve(self):
        """is_approved should be True for APPROVE."""
        result = PaymentValidationResult(
            decision=PaymentDecision.APPROVE,
            risk_level=PaymentRiskLevel.SAFE,
            gates={},
        )
        assert result.is_approved is True

    def test_is_approved_require_confirmation(self):
        """is_approved should be True for REQUIRE_CONFIRMATION."""
        result = PaymentValidationResult(
            decision=PaymentDecision.REQUIRE_CONFIRMATION,
            risk_level=PaymentRiskLevel.CAUTION,
            gates={},
        )
        assert result.is_approved is True

    def test_is_approved_block(self):
        """is_approved should be False for BLOCK."""
        result = PaymentValidationResult(
            decision=PaymentDecision.BLOCK,
            risk_level=PaymentRiskLevel.BLOCKED,
            gates={},
        )
        assert result.is_approved is False

    def test_all_gates_passed(self):
        """all_gates_passed should check all gates."""
        result = PaymentValidationResult(
            decision=PaymentDecision.APPROVE,
            risk_level=PaymentRiskLevel.SAFE,
            gates={
                THSPGate.TRUTH: THSPGateResult(gate=THSPGate.TRUTH, passed=True),
                THSPGate.HARM: THSPGateResult(gate=THSPGate.HARM, passed=True),
            },
        )
        assert result.all_gates_passed is True

    def test_all_gates_passed_one_failed(self):
        """all_gates_passed should be False if any gate failed."""
        result = PaymentValidationResult(
            decision=PaymentDecision.REJECT,
            risk_level=PaymentRiskLevel.HIGH,
            gates={
                THSPGate.TRUTH: THSPGateResult(gate=THSPGate.TRUTH, passed=True),
                THSPGate.HARM: THSPGateResult(gate=THSPGate.HARM, passed=False, reason="Blocked"),
            },
        )
        assert result.all_gates_passed is False

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        result = PaymentValidationResult(
            decision=PaymentDecision.APPROVE,
            risk_level=PaymentRiskLevel.SAFE,
            gates={
                THSPGate.TRUTH: THSPGateResult(gate=THSPGate.TRUTH, passed=True),
            },
            issues=["test issue"],
        )
        d = result.to_dict()
        assert d["decision"] == "approve"
        assert d["risk_level"] == "safe"
        assert d["issues"] == ["test issue"]


class TestPaymentRequirementsModel:
    """Tests for PaymentRequirementsModel."""

    def test_create_valid(self):
        """Should create valid payment requirements."""
        req = PaymentRequirementsModel(
            scheme="exact",
            network="base",
            max_amount_required="5000000",  # 5 USDC
            resource="https://api.example.com/data",
            pay_to="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            max_timeout_seconds=300,
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        )
        assert req.scheme == "exact"
        assert req.network == "base"

    def test_get_amount_float(self):
        """Should convert atomic units to float."""
        req = PaymentRequirementsModel(
            scheme="exact",
            network="base",
            max_amount_required="5000000",  # 5 USDC (6 decimals)
            resource="https://api.example.com",
            pay_to="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            max_timeout_seconds=300,
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        )
        assert req.get_amount_float() == 5.0

    def test_get_amount_float_invalid(self):
        """Should return 0.0 for invalid amount."""
        req = PaymentRequirementsModel(
            scheme="exact",
            network="base",
            max_amount_required="invalid",
            resource="https://api.example.com",
            pay_to="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            max_timeout_seconds=300,
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        )
        assert req.get_amount_float() == 0.0


class TestSpendingRecord:
    """Tests for SpendingRecord model."""

    def test_add_payment(self):
        """Should record payment correctly."""
        record = SpendingRecord(
            wallet_address="0x123",
            period_start=datetime.utcnow(),
            period_type="daily",
        )
        record.add_payment(10.0, "https://api.example.com")

        assert record.total_spent == 10.0
        assert record.transaction_count == 1
        assert len(record.payments) == 1

    def test_add_multiple_payments(self):
        """Should accumulate payments."""
        record = SpendingRecord(
            wallet_address="0x123",
            period_start=datetime.utcnow(),
            period_type="daily",
        )
        record.add_payment(10.0, "https://api1.example.com")
        record.add_payment(20.0, "https://api2.example.com")

        assert record.total_spent == 30.0
        assert record.transaction_count == 2


# =============================================================================
# Config Tests
# =============================================================================

class TestSpendingLimits:
    """Tests for SpendingLimits dataclass."""

    def test_defaults(self):
        """Should have sensible defaults."""
        limits = SpendingLimits()
        assert limits.max_single_payment == 100.0
        assert limits.max_daily_total == 500.0
        assert limits.max_transactions_per_day == 50
        assert limits.max_transactions_per_hour == 10

    def test_custom_values(self):
        """Should accept custom values."""
        limits = SpendingLimits(
            max_single_payment=50.0,
            max_daily_total=200.0,
        )
        assert limits.max_single_payment == 50.0
        assert limits.max_daily_total == 200.0


class TestConfirmationThresholds:
    """Tests for ConfirmationThresholds dataclass."""

    def test_defaults(self):
        """Should have sensible defaults."""
        thresholds = ConfirmationThresholds()
        assert thresholds.amount_threshold == 10.0
        assert thresholds.unknown_endpoint_threshold == 5.0


class TestValidationConfig:
    """Tests for ValidationConfig dataclass."""

    def test_defaults(self):
        """Should have sensible defaults."""
        config = ValidationConfig()
        assert config.strict_mode is False
        assert config.allow_unknown_endpoints is True
        assert config.require_https is True
        assert config.enable_spending_limits is True


class TestSentinelX402Config:
    """Tests for SentinelX402Config dataclass."""

    def test_defaults(self):
        """Should have default sub-configs."""
        config = SentinelX402Config()
        assert config.spending_limits is not None
        assert config.confirmation_thresholds is not None
        assert config.validation is not None

    def test_allowed_networks(self):
        """Should include all networks by default."""
        config = SentinelX402Config()
        assert SupportedNetwork.BASE in config.allowed_networks
        assert SupportedNetwork.BASE_SEPOLIA in config.allowed_networks


class TestGetDefaultConfig:
    """Tests for get_default_config function."""

    def test_permissive(self):
        """Permissive profile should have high limits."""
        config = get_default_config("permissive")
        assert config.spending_limits.max_single_payment == 1000.0
        assert config.spending_limits.max_daily_total == 5000.0
        assert config.validation.enable_spending_limits is False

    def test_standard(self):
        """Standard profile should have default values."""
        config = get_default_config("standard")
        assert config.spending_limits.max_single_payment == 100.0

    def test_strict(self):
        """Strict profile should have low limits."""
        config = get_default_config("strict")
        assert config.spending_limits.max_single_payment == 25.0
        assert config.spending_limits.max_daily_total == 100.0
        assert config.validation.strict_mode is True

    def test_paranoid(self):
        """Paranoid profile should have very low limits."""
        config = get_default_config("paranoid")
        assert config.spending_limits.max_single_payment == 10.0
        assert config.spending_limits.max_daily_total == 50.0
        assert config.confirmation_thresholds.amount_threshold == 1.0

    def test_invalid_profile(self):
        """Should raise for unknown profile."""
        with pytest.raises(ValueError):
            get_default_config("unknown")


# =============================================================================
# Validator Tests
# =============================================================================

def create_test_payment_req(
    amount: str = "5000000",
    pay_to: str = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    network: str = "base",
    description: str = "Test payment",
) -> PaymentRequirementsModel:
    """Helper to create test payment requirements."""
    return PaymentRequirementsModel(
        scheme="exact",
        network=network,
        max_amount_required=amount,
        resource="https://api.example.com/data",
        description=description,
        pay_to=pay_to,
        max_timeout_seconds=300,
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )


class TestTruthGateValidator:
    """Tests for TruthGateValidator."""

    def test_gate_property(self):
        """Should return TRUTH gate."""
        validator = TruthGateValidator()
        assert validator.gate == THSPGate.TRUTH

    def test_valid_payment(self):
        """Should pass valid payment."""
        validator = TruthGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is True

    def test_invalid_url_format(self):
        """Should fail for invalid URL."""
        validator = TruthGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()

        result = validator.validate(req, "not-a-url", "0x123", config)
        assert result.passed is False
        assert "Invalid endpoint URL" in result.reason

    def test_http_not_allowed(self):
        """Should fail for HTTP when HTTPS required."""
        validator = TruthGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()

        result = validator.validate(req, "http://api.example.com", "0x123", config)
        assert result.passed is False
        assert "HTTPS" in result.reason

    def test_unknown_network(self):
        """Should flag unknown network."""
        validator = TruthGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req(network="unknown-network")

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is False
        assert "Unknown network" in result.reason

    def test_invalid_recipient_address(self):
        """Should fail for invalid recipient address."""
        validator = TruthGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req(pay_to="invalid-address")

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is False
        assert "Invalid recipient address" in result.reason

    def test_zero_amount(self):
        """Should flag zero amount."""
        validator = TruthGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req(amount="0")

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is False
        assert "zero" in result.reason.lower()


class TestHarmGateValidator:
    """Tests for HarmGateValidator."""

    def test_gate_property(self):
        """Should return HARM gate."""
        validator = HarmGateValidator()
        assert validator.gate == THSPGate.HARM

    def test_valid_payment(self):
        """Should pass valid payment."""
        validator = HarmGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is True

    def test_blocked_address(self):
        """Should fail for blocked address."""
        validator = HarmGateValidator()
        config = SentinelX402Config(
            blocked_addresses=["0x742d35Cc6634C0532925a3b844Bc454e4438f44e"],
        )
        req = create_test_payment_req()

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is False
        assert "blocked" in result.reason.lower()

    def test_blocked_endpoint(self):
        """Should fail for blocked endpoint pattern."""
        validator = HarmGateValidator()
        config = SentinelX402Config(
            blocked_endpoints=["malicious.com"],
        )
        req = create_test_payment_req()

        result = validator.validate(req, "https://malicious.com/api", "0x123", config)
        assert result.passed is False
        assert "blocklist" in result.reason.lower()

    def test_none_pay_to(self):
        """Should handle None pay_to gracefully."""
        validator = HarmGateValidator()
        config = get_default_config("standard")

        # Create payment req with None pay_to (bypass pydantic)
        req = create_test_payment_req()
        req.pay_to = None

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is False
        assert "Missing recipient" in result.reason


class TestScopeGateValidator:
    """Tests for ScopeGateValidator."""

    def test_gate_property(self):
        """Should return SCOPE gate."""
        validator = ScopeGateValidator()
        assert validator.gate == THSPGate.SCOPE

    def test_within_limits(self):
        """Should pass when within limits."""
        validator = ScopeGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req(amount="5000000")  # $5

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is True

    def test_exceeds_single_limit(self):
        """Should fail when exceeding single payment limit."""
        validator = ScopeGateValidator()
        config = get_default_config("strict")  # $25 limit
        req = create_test_payment_req(amount="50000000")  # $50

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is False
        assert "exceeds single payment limit" in result.reason

    def test_spending_limits_disabled(self):
        """Should pass when spending limits disabled."""
        validator = ScopeGateValidator()
        config = get_default_config("permissive")  # Limits disabled
        req = create_test_payment_req(amount="1000000000")  # $1000

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is True
        assert result.details.get("note") == "Spending limits disabled"


class TestPurposeGateValidator:
    """Tests for PurposeGateValidator."""

    def test_gate_property(self):
        """Should return PURPOSE gate."""
        validator = PurposeGateValidator()
        assert validator.gate == THSPGate.PURPOSE

    def test_valid_payment(self):
        """Should pass valid payment."""
        validator = PurposeGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req(description="API access payment")

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is True

    def test_suspicious_description(self):
        """Should flag suspicious terms in description."""
        validator = PurposeGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req(description="Send your private key urgently")

        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result.passed is False
        assert "Suspicious term" in result.reason

    def test_none_description(self):
        """Should handle None description gracefully."""
        validator = PurposeGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()
        req.description = None

        # Should not raise
        result = validator.validate(req, "https://api.example.com", "0x123", config)
        assert result is not None

    def test_none_pay_to_in_purpose(self):
        """Should handle None pay_to gracefully."""
        validator = PurposeGateValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()
        req.pay_to = None

        context = {"recipient_history": {}}
        result = validator.validate(req, "https://api.example.com", "0x123", config, context)
        assert "Missing recipient" in str(result.details.get("concerns", []))


class TestTHSPPaymentValidator:
    """Tests for THSPPaymentValidator orchestrator."""

    def test_init(self):
        """Should initialize with all validators."""
        validator = THSPPaymentValidator()
        assert len(validator._validators) == 4

    def test_validate_all_pass(self):
        """Should return all gates when all pass."""
        validator = THSPPaymentValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()

        results = validator.validate_payment(req, "https://api.example.com", "0x123", config)

        assert THSPGate.TRUTH in results
        assert THSPGate.HARM in results
        assert THSPGate.SCOPE in results
        assert THSPGate.PURPOSE in results
        assert all(r.passed for r in results.values())

    def test_calculate_risk_blocked(self):
        """Should return BLOCKED for HARM failure."""
        validator = THSPPaymentValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()

        gate_results = {
            THSPGate.TRUTH: THSPGateResult(gate=THSPGate.TRUTH, passed=True),
            THSPGate.HARM: THSPGateResult(gate=THSPGate.HARM, passed=False),
            THSPGate.SCOPE: THSPGateResult(gate=THSPGate.SCOPE, passed=True),
            THSPGate.PURPOSE: THSPGateResult(gate=THSPGate.PURPOSE, passed=True),
        }

        risk = validator.calculate_risk_level(gate_results, req, config)
        assert risk == PaymentRiskLevel.BLOCKED

    def test_calculate_risk_critical(self):
        """Should return CRITICAL for multiple failures."""
        validator = THSPPaymentValidator()
        config = get_default_config("standard")
        req = create_test_payment_req()

        gate_results = {
            THSPGate.TRUTH: THSPGateResult(gate=THSPGate.TRUTH, passed=False),
            THSPGate.HARM: THSPGateResult(gate=THSPGate.HARM, passed=True),
            THSPGate.SCOPE: THSPGateResult(gate=THSPGate.SCOPE, passed=False),
            THSPGate.PURPOSE: THSPGateResult(gate=THSPGate.PURPOSE, passed=True),
        }

        risk = validator.calculate_risk_level(gate_results, req, config)
        assert risk == PaymentRiskLevel.CRITICAL

    def test_calculate_risk_safe(self):
        """Should return SAFE for all passed with low amount."""
        validator = THSPPaymentValidator()
        config = get_default_config("standard")
        req = create_test_payment_req(amount="1000000")  # $1

        gate_results = {
            THSPGate.TRUTH: THSPGateResult(gate=THSPGate.TRUTH, passed=True),
            THSPGate.HARM: THSPGateResult(gate=THSPGate.HARM, passed=True),
            THSPGate.SCOPE: THSPGateResult(gate=THSPGate.SCOPE, passed=True),
            THSPGate.PURPOSE: THSPGateResult(gate=THSPGate.PURPOSE, passed=True),
        }

        risk = validator.calculate_risk_level(gate_results, req, config)
        assert risk == PaymentRiskLevel.SAFE


# =============================================================================
# Middleware Tests
# =============================================================================

class TestSentinelX402Middleware:
    """Tests for SentinelX402Middleware."""

    def test_init_default(self):
        """Should initialize with default config."""
        middleware = SentinelX402Middleware()
        assert middleware.config is not None
        assert middleware.validator is not None

    def test_init_custom_config(self):
        """Should accept custom config."""
        config = get_default_config("strict")
        middleware = SentinelX402Middleware(config=config)
        assert middleware.config.spending_limits.max_single_payment == 25.0

    def test_validate_payment_approve(self):
        """Should approve safe payment."""
        middleware = SentinelX402Middleware()
        req = create_test_payment_req(amount="1000000")  # $1

        result = middleware.validate_payment(
            endpoint="https://api.example.com",
            payment_requirements=req,
            wallet_address="0x123",
        )

        assert result.decision == PaymentDecision.APPROVE
        assert result.is_approved is True

    def test_validate_payment_block(self):
        """Should block payment to blocked address."""
        config = SentinelX402Config(
            blocked_addresses=["0x742d35Cc6634C0532925a3b844Bc454e4438f44e"],
        )
        middleware = SentinelX402Middleware(config=config)
        req = create_test_payment_req()

        result = middleware.validate_payment(
            endpoint="https://api.example.com",
            payment_requirements=req,
            wallet_address="0x123",
        )

        assert result.decision == PaymentDecision.BLOCK
        assert result.is_approved is False

    def test_validate_payment_dict_input(self):
        """Should accept dict as payment_requirements."""
        middleware = SentinelX402Middleware()

        result = middleware.validate_payment(
            endpoint="https://api.example.com",
            payment_requirements={
                "scheme": "exact",
                "network": "base",
                "max_amount_required": "1000000",
                "resource": "https://api.example.com",
                "pay_to": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "max_timeout_seconds": 300,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            },
            wallet_address="0x123",
        )

        assert result is not None
        assert result.decision in [PaymentDecision.APPROVE, PaymentDecision.REQUIRE_CONFIRMATION]

    def test_before_payment_hook_block_raises(self):
        """before_payment_hook should raise for blocked payment."""
        config = SentinelX402Config(
            blocked_addresses=["0x742d35Cc6634C0532925a3b844Bc454e4438f44e"],
        )
        middleware = SentinelX402Middleware(config=config)
        req = create_test_payment_req()

        with pytest.raises(PaymentBlockedError):
            middleware.before_payment_hook(
                endpoint="https://api.example.com",
                payment_requirements=req,
                wallet_address="0x123",
            )

    def test_get_spending_summary(self):
        """Should return spending summary."""
        middleware = SentinelX402Middleware()

        summary = middleware.get_spending_summary("0x123")

        assert "wallet_address" in summary
        assert "daily_spent" in summary
        assert "daily_limit" in summary
        assert "daily_remaining" in summary

    def test_after_payment_hook(self):
        """Should record payment after execution."""
        middleware = SentinelX402Middleware()

        middleware.after_payment_hook(
            endpoint="https://api.example.com",
            wallet_address="0x123",
            amount=5.0,
            asset="USDC",
            network="base",
            pay_to="0x456",
            success=True,
            transaction_hash="0xabc",
        )

        # Check spending was recorded
        summary = middleware.get_spending_summary("0x123")
        assert summary["daily_spent"] == 5.0
        assert summary["daily_transactions"] == 1

    def test_after_payment_hook_none_recipient(self):
        """Should handle None recipient gracefully."""
        middleware = SentinelX402Middleware()

        # Should not raise
        middleware.after_payment_hook(
            endpoint="https://api.example.com",
            wallet_address="0x123",
            amount=5.0,
            asset="USDC",
            network="base",
            pay_to=None,
            success=True,
        )

    def test_reset_spending(self):
        """Should reset spending records."""
        middleware = SentinelX402Middleware()

        # Record some spending
        middleware.after_payment_hook(
            endpoint="https://api.example.com",
            wallet_address="0x123",
            amount=5.0,
            asset="USDC",
            network="base",
            pay_to="0x456",
            success=True,
        )

        # Reset
        middleware.reset_spending("0x123")

        # Check reset
        summary = middleware.get_spending_summary("0x123")
        assert summary["daily_spent"] == 0.0

    def test_get_audit_log(self):
        """Should return audit log."""
        middleware = SentinelX402Middleware()
        req = create_test_payment_req()

        # Validate to create audit entry
        middleware.validate_payment(
            endpoint="https://api.example.com",
            payment_requirements=req,
            wallet_address="0x123",
        )

        log = middleware.get_audit_log()
        assert len(log) > 0


class TestCreateSentinelX402Middleware:
    """Tests for factory function."""

    def test_create_with_profile(self):
        """Should create middleware with profile."""
        middleware = create_sentinel_x402_middleware("strict")
        assert middleware.config.spending_limits.max_single_payment == 25.0


# =============================================================================
# Schema Tests
# =============================================================================

class TestValidatePaymentSchema:
    """Tests for ValidatePaymentSchema."""

    def test_valid(self):
        """Should validate correct input."""
        schema = ValidatePaymentSchema(
            endpoint="https://api.example.com",
            amount="5000000",
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            network="base",
            pay_to="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        )
        assert schema.endpoint == "https://api.example.com"

    def test_default_scheme(self):
        """Should have default scheme."""
        schema = ValidatePaymentSchema(
            endpoint="https://api.example.com",
            amount="5000000",
            asset="0x833",
            network="base",
            pay_to="0x742",
        )
        assert schema.scheme == "exact"


class TestConfigureSpendingLimitsSchema:
    """Tests for ConfigureSpendingLimitsSchema."""

    def test_all_optional(self):
        """All fields should be optional."""
        schema = ConfigureSpendingLimitsSchema()
        assert schema.max_single_payment is None
        assert schema.max_daily_total is None

    def test_partial(self):
        """Should accept partial values."""
        schema = ConfigureSpendingLimitsSchema(max_single_payment=50.0)
        assert schema.max_single_payment == 50.0
        assert schema.max_daily_total is None


class TestResetSpendingSchema:
    """Tests for ResetSpendingSchema."""

    def test_default_confirm_false(self):
        """confirm should default to False."""
        schema = ResetSpendingSchema()
        assert schema.confirm is False

    def test_with_confirm(self):
        """Should accept confirm=True."""
        schema = ResetSpendingSchema(confirm=True)
        assert schema.confirm is True


# =============================================================================
# Exception Tests
# =============================================================================

class TestExceptions:
    """Tests for custom exceptions."""

    def test_payment_blocked_error(self):
        """Should store result."""
        result = PaymentValidationResult(
            decision=PaymentDecision.BLOCK,
            risk_level=PaymentRiskLevel.BLOCKED,
            gates={},
        )
        error = PaymentBlockedError("Blocked", result=result)
        assert error.result == result
        assert str(error) == "Blocked"

    def test_payment_rejected_error(self):
        """Should store result."""
        result = PaymentValidationResult(
            decision=PaymentDecision.REJECT,
            risk_level=PaymentRiskLevel.CRITICAL,
            gates={},
        )
        error = PaymentRejectedError("Rejected", result=result)
        assert error.result == result

    def test_payment_confirmation_required(self):
        """Should store result."""
        result = PaymentValidationResult(
            decision=PaymentDecision.REQUIRE_CONFIRMATION,
            risk_level=PaymentRiskLevel.CAUTION,
            gates={},
        )
        error = PaymentConfirmationRequired("Confirm", result=result)
        assert error.result == result
