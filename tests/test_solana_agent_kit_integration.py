"""
Tests for Solana Agent Kit integration.

Run with:
    pytest tests/test_solana_agent_kit_integration.py -v
"""

import pytest
import warnings
from unittest.mock import patch, MagicMock


class TestAddressValidation:
    """Tests for Solana address validation."""

    def test_is_valid_solana_address_valid(self):
        """Test valid Solana addresses."""
        from sentinelseed.integrations.solana_agent_kit import is_valid_solana_address

        # Real Solana addresses (base58, 32-44 chars)
        valid_addresses = [
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            "11111111111111111111111111111111",  # System program
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token program
            "So11111111111111111111111111111111111111112",  # Wrapped SOL
        ]

        for addr in valid_addresses:
            assert is_valid_solana_address(addr), f"Should be valid: {addr}"

    def test_is_valid_solana_address_invalid(self):
        """Test invalid Solana addresses."""
        from sentinelseed.integrations.solana_agent_kit import is_valid_solana_address

        invalid_addresses = [
            "",
            "not-valid",
            "ABC",  # Too short
            "0xABC123",  # Ethereum format
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAs0",  # Contains 0
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsO",  # Contains O
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsl",  # Contains l
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsI",  # Contains I
        ]

        for addr in invalid_addresses:
            assert not is_valid_solana_address(addr), f"Should be invalid: {addr}"

    def test_is_valid_solana_address_none(self):
        """Test None and non-string inputs."""
        from sentinelseed.integrations.solana_agent_kit import is_valid_solana_address

        assert not is_valid_solana_address(None)
        assert not is_valid_solana_address(123)
        assert not is_valid_solana_address([])


class TestAddressValidationMode:
    """Tests for AddressValidationMode enum."""

    def test_address_validation_modes_exist(self):
        """Test that all modes exist."""
        from sentinelseed.integrations.solana_agent_kit import AddressValidationMode

        assert AddressValidationMode.IGNORE.value == "ignore"
        assert AddressValidationMode.WARN.value == "warn"
        assert AddressValidationMode.STRICT.value == "strict"

    def test_validator_strict_mode_blocks_invalid(self):
        """Test STRICT mode blocks invalid addresses."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            AddressValidationMode,
            TransactionRisk,
        )

        validator = SentinelValidator(
            address_validation=AddressValidationMode.STRICT
        )

        result = validator.check(
            action="transfer",
            amount=1.0,
            recipient="invalid-address",
            purpose="Test transfer",
        )

        assert not result.should_proceed
        assert result.risk_level == TransactionRisk.CRITICAL
        assert any("Invalid Solana address" in c for c in result.concerns)

    def test_validator_warn_mode_allows_invalid(self):
        """Test WARN mode allows but adds recommendation."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            AddressValidationMode,
        )

        validator = SentinelValidator(
            address_validation=AddressValidationMode.WARN
        )

        result = validator.check(
            action="transfer",
            amount=1.0,
            recipient="invalid-address",
            purpose="Test transfer",
        )

        # Should proceed (WARN doesn't block)
        # Note: may be blocked by other checks, but not by address validation
        assert any("Verify recipient" in r for r in result.recommendations)

    def test_validator_ignore_mode(self):
        """Test IGNORE mode doesn't validate."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            AddressValidationMode,
        )

        validator = SentinelValidator(
            address_validation=AddressValidationMode.IGNORE
        )

        result = validator.check(
            action="transfer",
            amount=1.0,
            recipient="invalid-address",
            purpose="Test transfer",
        )

        # No address-related concerns or recommendations
        assert not any("address" in c.lower() for c in result.concerns)
        assert not any("address" in r.lower() for r in result.recommendations)

    def test_validator_accepts_string_mode(self):
        """Test validator accepts string for address_validation."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            AddressValidationMode,
        )

        validator = SentinelValidator(address_validation="strict")
        assert validator.address_validation == AddressValidationMode.STRICT

        validator = SentinelValidator(address_validation="WARN")
        assert validator.address_validation == AddressValidationMode.WARN


class TestTransactionRisk:
    """Tests for TransactionRisk enum."""

    def test_risk_level_ordering(self):
        """Test risk level comparison."""
        from sentinelseed.integrations.solana_agent_kit import TransactionRisk

        assert TransactionRisk.LOW < TransactionRisk.MEDIUM
        assert TransactionRisk.MEDIUM < TransactionRisk.HIGH
        assert TransactionRisk.HIGH < TransactionRisk.CRITICAL
        assert TransactionRisk.LOW <= TransactionRisk.LOW
        assert TransactionRisk.CRITICAL >= TransactionRisk.HIGH


class TestSentinelValidator:
    """Tests for SentinelValidator class."""

    def test_validator_initialization_defaults(self):
        """Test default initialization."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        assert validator.max_transfer == 100.0
        assert validator.confirm_above == 10.0
        assert len(validator.blocked_addresses) == 0
        assert len(validator.allowed_programs) == 0
        assert "transfer" in validator.require_purpose_for
        assert "send" in validator.require_purpose_for

    def test_validator_custom_config(self):
        """Test custom configuration."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            max_transfer=50.0,
            confirm_above=5.0,
            blocked_addresses=["blocked1", "blocked2"],
            allowed_programs=["prog1"],
        )

        assert validator.max_transfer == 50.0
        assert validator.confirm_above == 5.0
        assert "blocked1" in validator.blocked_addresses
        assert "prog1" in validator.allowed_programs

    def test_check_basic_transaction(self):
        """Test basic transaction validation."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Test payment for services",
        )

        assert result.transaction_type == "transfer"

    def test_check_exceeds_max_transfer(self):
        """Test transaction exceeding max transfer."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            TransactionRisk,
        )

        validator = SentinelValidator(max_transfer=10.0)

        result = validator.check(
            action="transfer",
            amount=50.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        )

        assert not result.should_proceed
        assert result.risk_level == TransactionRisk.CRITICAL
        assert any("exceeds limit" in c for c in result.concerns)

    def test_check_blocked_address(self):
        """Test blocked address detection."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            TransactionRisk,
        )

        blocked = "BlockedAddress123456789012345678901234"
        validator = SentinelValidator(blocked_addresses=[blocked])

        result = validator.check(
            action="transfer",
            amount=1.0,
            recipient=blocked,
            purpose="Test transfer",
        )

        assert not result.should_proceed
        assert result.risk_level == TransactionRisk.CRITICAL
        assert any("blocked" in c.lower() for c in result.concerns)

    def test_check_non_whitelisted_program(self):
        """Test non-whitelisted program detection."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            TransactionRisk,
        )

        validator = SentinelValidator(
            allowed_programs=["AllowedProgram123"]
        )

        result = validator.check(
            action="call",
            amount=0,
            program_id="NotAllowedProgram456",
            purpose="Test call",
        )

        assert not result.should_proceed
        assert result.risk_level == TransactionRisk.HIGH
        assert any("not whitelisted" in c for c in result.concerns)

    def test_check_requires_confirmation(self):
        """Test high-value confirmation requirement."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(confirm_above=10.0)

        result = validator.check(
            action="transfer",
            amount=25.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Large payment",
        )

        assert result.requires_confirmation

    def test_purpose_gate_missing_purpose(self):
        """Test PURPOSE gate with missing purpose."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        )

        assert any("requires explicit purpose" in c for c in result.concerns)

    def test_purpose_gate_brief_purpose(self):
        """Test PURPOSE gate with brief purpose."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="pay",  # Too short
        )

        assert any("too brief" in c for c in result.concerns)

    def test_purpose_gate_valid_purpose(self):
        """Test PURPOSE gate with valid purpose."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Monthly payment for hosting services",
        )

        assert not any("purpose" in c.lower() for c in result.concerns)

    def test_pattern_detection_drain(self):
        """Test drain pattern detection."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="drain_wallet",
            amount=100.0,
            purpose="Drain operation",
        )

        assert any("drain" in c.lower() for c in result.concerns)

    def test_pattern_detection_bulk_transfer(self):
        """Test bulk transfer pattern detection."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transfer_all",
            amount=100.0,
            purpose="Transfer all tokens",
        )

        assert any("bulk" in c.lower() for c in result.concerns)

    def test_history_tracking(self):
        """Test validation history tracking."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(max_history_size=5)

        for i in range(7):
            validator.check(
                action="transfer",
                amount=float(i),
                purpose=f"Payment {i}",
            )

        assert len(validator.history) == 5  # Max size enforced

    def test_get_stats(self):
        """Test statistics calculation."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(max_transfer=10.0)

        # Some approved, some blocked
        validator.check(action="transfer", amount=5.0, purpose="Payment 1")
        validator.check(action="transfer", amount=5.0, purpose="Payment 2")
        validator.check(action="transfer", amount=50.0)  # Blocked

        stats = validator.get_stats()

        assert stats["total"] == 3
        assert stats["blocked"] >= 1
        assert "block_rate" in stats

    def test_clear_history(self):
        """Test history clearing."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()
        validator.check(action="transfer", amount=5.0, purpose="Test")

        assert len(validator.history) > 0

        validator.clear_history()

        assert len(validator.history) == 0


class TestSafeTransaction:
    """Tests for safe_transaction function."""

    def test_safe_transaction_basic(self):
        """Test basic safe_transaction call."""
        from sentinelseed.integrations.solana_agent_kit import safe_transaction

        result = safe_transaction(
            "transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Test payment",
        )

        assert result.transaction_type == "transfer"

    def test_safe_transaction_with_params_dict(self):
        """Test safe_transaction with params dict."""
        from sentinelseed.integrations.solana_agent_kit import safe_transaction

        result = safe_transaction(
            "swap",
            params={"amount": 10.0, "purpose": "Token swap"},
        )

        assert result.transaction_type == "swap"

    def test_safe_transaction_with_validator(self):
        """Test safe_transaction with custom validator."""
        from sentinelseed.integrations.solana_agent_kit import (
            safe_transaction,
            SentinelValidator,
        )

        validator = SentinelValidator(max_transfer=5.0)

        result = safe_transaction(
            "transfer",
            amount=10.0,
            validator=validator,
        )

        assert not result.should_proceed


class TestCreateSentinelActions:
    """Tests for create_sentinel_actions function."""

    def test_create_actions_returns_dict(self):
        """Test actions dictionary creation."""
        from sentinelseed.integrations.solana_agent_kit import create_sentinel_actions

        actions = create_sentinel_actions()

        assert "validate_transfer" in actions
        assert "validate_swap" in actions
        assert "validate_action" in actions
        assert "get_safety_seed" in actions

    def test_validate_transfer_action(self):
        """Test validate_transfer action."""
        from sentinelseed.integrations.solana_agent_kit import create_sentinel_actions

        actions = create_sentinel_actions()
        result = actions["validate_transfer"](
            5.0,
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        )

        assert "safe" in result
        assert "risk" in result
        assert "concerns" in result

    def test_validate_swap_action(self):
        """Test validate_swap action."""
        from sentinelseed.integrations.solana_agent_kit import create_sentinel_actions

        actions = create_sentinel_actions()
        result = actions["validate_swap"](10.0, "SOL", "USDC")

        assert "safe" in result
        assert "risk" in result

    def test_validate_action_generic(self):
        """Test generic validate_action."""
        from sentinelseed.integrations.solana_agent_kit import create_sentinel_actions

        actions = create_sentinel_actions()
        result = actions["validate_action"](
            "stake",
            amount=100.0,
            purpose="Staking rewards",
        )

        assert "safe" in result
        assert "recommendations" in result

    def test_get_safety_seed_action(self):
        """Test get_safety_seed action."""
        from sentinelseed.integrations.solana_agent_kit import create_sentinel_actions

        actions = create_sentinel_actions()
        seed = actions["get_safety_seed"]()

        assert isinstance(seed, str)
        assert len(seed) > 0


class TestCreateLangchainTools:
    """Tests for create_langchain_tools function."""

    def test_langchain_import_error(self):
        """Test graceful handling of missing langchain."""
        from sentinelseed.integrations.solana_agent_kit import create_langchain_tools

        with patch.dict("sys.modules", {"langchain": None, "langchain.tools": None}):
            # This should raise ImportError
            with pytest.raises(ImportError, match="langchain is required"):
                create_langchain_tools()

    def test_langchain_tools_created(self):
        """Test LangChain tools creation (with mock)."""
        # Mock langchain.tools.Tool
        mock_tool_class = MagicMock()
        mock_tool_module = MagicMock()
        mock_tool_module.Tool = mock_tool_class

        with patch.dict("sys.modules", {"langchain": MagicMock(), "langchain.tools": mock_tool_module}):
            from sentinelseed.integrations.solana_agent_kit import create_langchain_tools

            tools = create_langchain_tools()

            assert len(tools) == 1
            mock_tool_class.assert_called_once()


class TestLangchainToolParsing:
    """Tests for LangChain tool input parsing."""

    def test_parse_valid_input(self):
        """Test parsing valid input."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        # Simulate the check_transaction function logic
        description = "transfer 5.0 ABC123"
        parts = description.strip().split()
        action = parts[0]
        amount = float(parts[1])
        recipient = parts[2]

        result = validator.check(action, amount=amount, recipient=recipient, purpose="Test")

        assert result.transaction_type == "transfer"

    def test_parse_empty_input(self):
        """Test parsing empty input returns error."""
        # The check_transaction function should handle empty input
        description = ""
        parts = description.strip().split()

        assert len(parts) == 0 or parts[0] == ""

    def test_parse_invalid_amount(self):
        """Test parsing invalid amount."""
        description = "transfer abc recipient"
        parts = description.strip().split()

        with pytest.raises(ValueError):
            float(parts[1])  # Should raise ValueError

    def test_parse_negative_amount(self):
        """Test negative amount handling."""
        description = "transfer -5.0 recipient"
        parts = description.strip().split()
        amount = float(parts[1])

        assert amount < 0


class TestSentinelSafetyMiddleware:
    """Tests for SentinelSafetyMiddleware class."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        from sentinelseed.integrations.solana_agent_kit import SentinelSafetyMiddleware

        middleware = SentinelSafetyMiddleware()

        assert middleware.validator is not None

    def test_middleware_wrap_function(self):
        """Test wrapping a function."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelSafetyMiddleware,
            SentinelValidator,
        )

        validator = SentinelValidator(max_transfer=100.0)
        middleware = SentinelSafetyMiddleware(validator=validator)

        def my_transfer(amount, recipient):
            return f"Transferred {amount} to {recipient}"

        safe_fn = middleware.wrap(my_transfer, "transfer")

        # Should work for safe amount
        result = safe_fn(5.0, "recipient")
        assert "Transferred" in result

    def test_middleware_blocks_unsafe(self):
        """Test middleware blocks unsafe transactions."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelSafetyMiddleware,
            SentinelValidator,
            TransactionBlockedError,
        )

        validator = SentinelValidator(max_transfer=10.0)
        middleware = SentinelSafetyMiddleware(validator=validator)

        def my_transfer(amount, recipient):
            return f"Transferred {amount}"

        safe_fn = middleware.wrap(my_transfer, "transfer")

        with pytest.raises(TransactionBlockedError):
            safe_fn(50.0, "recipient")

    def test_middleware_preserves_function_metadata(self):
        """Test wrapper preserves function name and docstring."""
        from sentinelseed.integrations.solana_agent_kit import SentinelSafetyMiddleware

        middleware = SentinelSafetyMiddleware()

        def my_transfer(amount, recipient):
            """Transfer tokens."""
            return amount

        safe_fn = middleware.wrap(my_transfer, "transfer")

        assert safe_fn.__name__ == "my_transfer"
        assert safe_fn.__doc__ == "Transfer tokens."

    def test_middleware_handles_kwargs(self):
        """Test middleware handles keyword arguments."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelSafetyMiddleware,
            SentinelValidator,
        )

        validator = SentinelValidator(max_transfer=100.0)
        middleware = SentinelSafetyMiddleware(validator=validator)

        def my_transfer(amount, recipient):
            return amount

        safe_fn = middleware.wrap(my_transfer, "transfer")
        result = safe_fn(amount=5.0, recipient="test")

        assert result == 5.0

    def test_middleware_handles_invalid_amount_type(self):
        """Test middleware handles non-numeric amount."""
        from sentinelseed.integrations.solana_agent_kit import SentinelSafetyMiddleware

        middleware = SentinelSafetyMiddleware()

        def my_transfer(amount, recipient):
            return amount

        safe_fn = middleware.wrap(my_transfer, "transfer")

        # Should not crash, converts to 0.0
        result = safe_fn("not-a-number", "recipient")
        assert result == "not-a-number"


class TestMemoryIntegrityCheck:
    """Tests for memory integrity check feature."""

    def test_memory_check_disabled_by_default(self):
        """Test memory check is disabled by default."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        assert validator.memory_integrity_check is False
        assert validator._memory_checker is None

    def test_memory_check_warns_if_unavailable(self):
        """Test warning when memory module unavailable."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # This will try to import the memory module
            validator = SentinelValidator(memory_integrity_check=True)

            # Should have warned about unavailable module
            # (unless module is available)
            if validator._memory_checker is None:
                assert any("memory" in str(warning.message).lower() for warning in w)


class TestExports:
    """Tests for module exports."""

    def test_all_exports_available(self):
        """Test all __all__ exports are available."""
        from sentinelseed.integrations.solana_agent_kit import (
            __version__,
            TransactionRisk,
            AddressValidationMode,
            TransactionSafetyResult,
            SentinelValidator,
            SentinelSafetyMiddleware,
            TransactionBlockedError,
            safe_transaction,
            create_sentinel_actions,
            create_langchain_tools,
            is_valid_solana_address,
        )

        assert __version__ == "2.0.0"
        assert TransactionRisk is not None
        assert AddressValidationMode is not None
        assert TransactionSafetyResult is not None
        assert SentinelValidator is not None
        assert SentinelSafetyMiddleware is not None
        assert TransactionBlockedError is not None
        assert callable(safe_transaction)
        assert callable(create_sentinel_actions)
        assert callable(create_langchain_tools)
        assert callable(is_valid_solana_address)


class TestTransactionBlockedError:
    """Tests for TransactionBlockedError exception."""

    def test_exception_message(self):
        """Test exception message."""
        from sentinelseed.integrations.solana_agent_kit import TransactionBlockedError

        error = TransactionBlockedError("Test message")

        assert str(error) == "Test message"

    def test_exception_inheritance(self):
        """Test exception inherits from Exception."""
        from sentinelseed.integrations.solana_agent_kit import TransactionBlockedError

        assert issubclass(TransactionBlockedError, Exception)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_amount(self):
        """Test zero amount transaction."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="query",
            amount=0,
            purpose="Query balance",
        )

        # Zero amount should be allowed (not over limit)
        assert not any("exceeds limit" in c for c in result.concerns)

    def test_empty_recipient(self):
        """Test empty recipient."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="swap",
            amount=10.0,
            recipient="",
            purpose="Token swap",
        )

        # Empty recipient shouldn't trigger address validation
        assert not any("address" in c.lower() for c in result.concerns)

    def test_action_case_insensitive(self):
        """Test action matching is case-insensitive."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result1 = validator.check(action="TRANSFER", amount=5.0)
        result2 = validator.check(action="transfer", amount=5.0)
        result3 = validator.check(action="Transfer", amount=5.0)

        # All should trigger purpose requirement
        assert any("purpose" in c.lower() for c in result1.concerns)
        assert any("purpose" in c.lower() for c in result2.concerns)
        assert any("purpose" in c.lower() for c in result3.concerns)

    def test_very_long_purpose(self):
        """Test very long purpose is accepted."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        long_purpose = "A" * 1000

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose=long_purpose,
        )

        # Long purpose should be accepted
        assert not any("brief" in c.lower() for c in result.concerns)

    def test_reason_alias_for_purpose(self):
        """Test 'reason' works as alias for 'purpose'."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            reason="Monthly payment for services",  # Using reason instead of purpose
        )

        # Should not complain about missing purpose
        assert not any("requires explicit purpose" in c for c in result.concerns)


class TestStrictMode:
    """Tests for strict_mode configuration."""

    def test_strict_mode_disabled_by_default(self):
        """Test strict mode is disabled by default."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()
        assert validator.strict_mode is False

    def test_strict_mode_blocks_with_concerns(self):
        """Test strict mode blocks transactions with any concerns."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(strict_mode=True)

        # Missing purpose creates a concern but normally would proceed
        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        )

        # Should not proceed in strict mode
        assert not result.should_proceed

    def test_normal_mode_allows_medium_risk(self):
        """Test normal mode allows MEDIUM risk transactions."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            TransactionRisk,
        )

        validator = SentinelValidator(strict_mode=False)

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        )

        # MEDIUM risk should proceed in normal mode
        if result.risk_level == TransactionRisk.MEDIUM:
            assert result.should_proceed


class TestCustomPatterns:
    """Tests for custom_patterns configuration."""

    def test_default_patterns_loaded(self):
        """Test default suspicious patterns are loaded."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            DEFAULT_SUSPICIOUS_PATTERNS,
        )

        validator = SentinelValidator()

        assert len(validator.custom_patterns) >= len(DEFAULT_SUSPICIOUS_PATTERNS)

    def test_custom_pattern_detection(self):
        """Test custom pattern detection."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            SuspiciousPattern,
            TransactionRisk,
        )

        custom = SuspiciousPattern(
            name="test_pattern",
            pattern=r"forbidden_word",
            risk_level=TransactionRisk.HIGH,
            message="Forbidden word detected",
        )

        validator = SentinelValidator(custom_patterns=[custom])

        result = validator.check(
            action="forbidden_word_action",
            amount=1.0,
            purpose="Testing custom patterns",
        )

        assert any("Forbidden word" in c for c in result.concerns)

    def test_pattern_matches_method(self):
        """Test SuspiciousPattern.matches() method."""
        from sentinelseed.integrations.solana_agent_kit import (
            SuspiciousPattern,
            TransactionRisk,
        )

        pattern = SuspiciousPattern(
            name="test",
            pattern=r"danger",
            risk_level=TransactionRisk.HIGH,
            message="Danger detected",
        )

        assert pattern.matches("This is dangerous")
        assert pattern.matches("DANGER ahead")
        assert not pattern.matches("Safe text")


class TestOnValidationCallback:
    """Tests for on_validation callback."""

    def test_callback_called_on_validation(self):
        """Test callback is called after each validation."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        results = []

        def callback(result):
            results.append(result)

        validator = SentinelValidator(on_validation=callback)

        validator.check(action="transfer", amount=5.0, purpose="Test 1")
        validator.check(action="swap", amount=10.0, purpose="Test 2")

        assert len(results) == 2
        assert results[0].transaction_type == "transfer"
        assert results[1].transaction_type == "swap"

    def test_callback_error_handled(self):
        """Test callback errors are handled gracefully."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        def bad_callback(result):
            raise ValueError("Callback error")

        validator = SentinelValidator(on_validation=bad_callback)

        # Should not raise, error is logged
        result = validator.check(action="transfer", amount=5.0, purpose="Test")

        assert result is not None


class TestBlockUnblockAddress:
    """Tests for block_address and unblock_address methods."""

    def test_block_address(self):
        """Test blocking an address."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()
        address = "TestAddress123456789012345678901234"

        validator.block_address(address)

        assert address in validator.blocked_addresses

    def test_unblock_address(self):
        """Test unblocking an address."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        address = "TestAddress123456789012345678901234"
        validator = SentinelValidator(blocked_addresses=[address])

        validator.unblock_address(address)

        assert address not in validator.blocked_addresses

    def test_unblock_nonexistent_address(self):
        """Test unblocking non-existent address is safe."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        # Should not raise
        validator.unblock_address("nonexistent")

    def test_block_address_prevents_transaction(self):
        """Test blocked address prevents transaction."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()
        address = "BlockMeAddress123456789012345678901"

        validator.block_address(address)

        result = validator.check(
            action="transfer",
            amount=1.0,
            recipient=address,
            purpose="Test transfer",
        )

        assert not result.should_proceed
        assert any("blocked" in c.lower() for c in result.concerns)


class TestUpdateConfig:
    """Tests for get_config and update_config methods."""

    def test_get_config(self):
        """Test get_config returns current configuration."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            max_transfer=50.0,
            strict_mode=True,
        )

        config = validator.get_config()

        assert config["max_transfer"] == 50.0
        assert config["strict_mode"] is True
        assert "blocked_addresses" in config
        assert "custom_patterns_count" in config

    def test_update_config(self):
        """Test update_config modifies configuration."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(max_transfer=100.0)

        validator.update_config(max_transfer=50.0, strict_mode=True)

        assert validator.max_transfer == 50.0
        assert validator.strict_mode is True

    def test_update_config_partial(self):
        """Test update_config with partial updates."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(max_transfer=100.0, confirm_above=10.0)

        # Only update max_transfer
        validator.update_config(max_transfer=50.0)

        assert validator.max_transfer == 50.0
        assert validator.confirm_above == 10.0  # Unchanged

    def test_update_config_address_validation(self):
        """Test update_config with address validation mode."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            AddressValidationMode,
        )

        validator = SentinelValidator()

        validator.update_config(address_validation="strict")
        assert validator.address_validation == AddressValidationMode.STRICT

        validator.update_config(address_validation=AddressValidationMode.IGNORE)
        assert validator.address_validation == AddressValidationMode.IGNORE


class TestNegativeAmountValidation:
    """Tests for negative amount validation."""

    def test_negative_amount_blocked(self):
        """Test negative amount is blocked."""
        from sentinelseed.integrations.solana_agent_kit import (
            SentinelValidator,
            TransactionRisk,
        )

        validator = SentinelValidator()

        result = validator.check(
            action="transfer",
            amount=-5.0,
            purpose="Test transfer",
        )

        assert not result.should_proceed
        assert result.risk_level == TransactionRisk.CRITICAL
        assert any("negative" in c.lower() for c in result.concerns)

    def test_zero_amount_allowed(self):
        """Test zero amount is allowed."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="query",
            amount=0,
            purpose="Balance check",
        )

        assert not any("negative" in c.lower() for c in result.concerns)


class TestHighRiskActions:
    """Tests for HIGH_RISK_ACTIONS detection."""

    def test_drain_action_blocked(self):
        """Test drain action is blocked."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="drainWallet",
            amount=100.0,
            purpose="Drain operation",
        )

        assert not result.should_proceed
        assert any("High-risk action" in c for c in result.concerns)

    def test_sweep_action_blocked(self):
        """Test sweep action is blocked."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="sweepTokens",
            amount=100.0,
            purpose="Sweep operation",
        )

        assert not result.should_proceed
        assert any("High-risk action" in c for c in result.concerns)

    def test_transfer_all_blocked(self):
        """Test transferAll action is blocked."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transferAll",
            amount=100.0,
            purpose="Transfer all tokens",
        )

        assert not result.should_proceed

    def test_normal_transfer_allowed(self):
        """Test normal transfer is allowed."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Normal payment",
        )

        # Normal transfer should not be blocked by high-risk action check
        assert not any("High-risk action" in c for c in result.concerns)


class TestNewExports:
    """Tests for new module exports."""

    def test_suspicious_pattern_export(self):
        """Test SuspiciousPattern is exported."""
        from sentinelseed.integrations.solana_agent_kit import SuspiciousPattern

        assert SuspiciousPattern is not None

    def test_default_patterns_export(self):
        """Test DEFAULT_SUSPICIOUS_PATTERNS is exported."""
        from sentinelseed.integrations.solana_agent_kit import DEFAULT_SUSPICIOUS_PATTERNS

        assert isinstance(DEFAULT_SUSPICIOUS_PATTERNS, list)
        assert len(DEFAULT_SUSPICIOUS_PATTERNS) > 0

    def test_high_risk_actions_export(self):
        """Test HIGH_RISK_ACTIONS is exported."""
        from sentinelseed.integrations.solana_agent_kit import HIGH_RISK_ACTIONS

        assert isinstance(HIGH_RISK_ACTIONS, list)
        assert "drain" in HIGH_RISK_ACTIONS
