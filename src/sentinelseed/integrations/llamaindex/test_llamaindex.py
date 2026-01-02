"""
Tests for LlamaIndex integration.

Tests the Sentinel LLM wrapper and callback handler that integrate with
LlamaIndex for RAG and agent workflows.

These tests use mocks to avoid requiring llama-index-core as a dependency.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys

from sentinelseed.integrations._base import SentinelIntegration
from sentinelseed.validation import LayeredValidator, ValidationConfig, ValidationResult
from sentinelseed.validation.types import ValidationLayer, RiskLevel


# Check if llama_index is available
try:
    import llama_index.core
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False


class TestSentinelLLMInheritance:
    """Tests for SentinelLLM class inheritance (no llama_index required)."""

    def test_inherits_from_sentinel_integration(self):
        """Verify SentinelLLM inherits from SentinelIntegration."""
        from sentinelseed.integrations.llamaindex import SentinelLLM

        assert issubclass(SentinelLLM, SentinelIntegration)


class TestSentinelCallbackHandlerClass:
    """Tests for SentinelCallbackHandler class (no llama_index required)."""

    def test_callback_handler_exists(self):
        """Test that callback handler class exists."""
        from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

        assert SentinelCallbackHandler is not None

    def test_callback_handler_integration_name(self):
        """Test callback handler has correct integration name."""
        from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

        assert SentinelCallbackHandler._integration_name == "llamaindex"


class TestValidationEventClass:
    """Tests for SentinelValidationEvent class (no llama_index required)."""

    def test_validation_event_exists(self):
        """Test that validation event class exists."""
        from sentinelseed.integrations.llamaindex import SentinelValidationEvent

        assert SentinelValidationEvent is not None

    def test_validation_event_has_expected_attributes(self):
        """Test validation event class structure."""
        from sentinelseed.integrations.llamaindex import SentinelValidationEvent
        import inspect

        # Should have __init__ that takes is_safe, violations, content
        sig = inspect.signature(SentinelValidationEvent.__init__)
        params = list(sig.parameters.keys())

        assert "is_safe" in params
        assert "violations" in params
        assert "content" in params


@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="llama-index-core not installed")
class TestSentinelLLMWithLlamaIndex:
    """Tests that require llama-index-core to be installed."""

    def test_initialization_with_mock_llm(self):
        """Test initialization with mock LLM."""
        from sentinelseed.integrations.llamaindex import SentinelLLM

        mock_llm = MagicMock()
        mock_validator = MagicMock(spec=LayeredValidator)

        llm = SentinelLLM(llm=mock_llm, validator=mock_validator)

        assert llm._integration_name == "llamaindex_llm"
        assert llm._llm is mock_llm
        assert llm._validator is mock_validator

    def test_validate_method_works(self):
        """Test that validate method works."""
        from sentinelseed.integrations.llamaindex import SentinelLLM

        mock_llm = MagicMock()
        llm = SentinelLLM(llm=mock_llm)

        result = llm.validate("Hello world")
        assert result.is_safe is True


@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="llama-index-core not installed")
class TestSentinelCallbackHandlerWithLlamaIndex:
    """Tests that require llama-index-core to be installed."""

    def test_callback_handler_initialization(self):
        """Test callback handler initialization."""
        from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

        handler = SentinelCallbackHandler()
        assert hasattr(handler, "_validator")

    def test_get_stats_method(self):
        """Test that get_stats method exists and works."""
        from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

        handler = SentinelCallbackHandler()
        stats = handler.get_stats()

        assert isinstance(stats, dict)


class TestMockedLlamaIndexIntegration:
    """Tests using mocked llama-index to test without installing it."""

    @pytest.fixture
    def mock_llamaindex_module(self):
        """Create mock llama_index module."""
        # Create mock modules
        mock_core = MagicMock()
        mock_callbacks = MagicMock()
        mock_base_handler = MagicMock()
        mock_llms = MagicMock()
        mock_types = MagicMock()
        mock_callbacks_llm = MagicMock()

        # Setup CBEventType mock
        mock_base_handler.CBEventType = MagicMock()
        mock_base_handler.CBEventType.LLM = "llm"

        # Setup BaseCallbackHandler mock
        mock_base_handler.BaseCallbackHandler = type('BaseCallbackHandler', (), {
            '__init__': lambda self, *args, **kwargs: None,
        })

        return {
            'llama_index.core': mock_core,
            'llama_index.core.callbacks': mock_callbacks,
            'llama_index.core.callbacks.base_handler': mock_base_handler,
            'llama_index.core.llms': mock_llms,
            'llama_index.core.llms.types': mock_types,
            'llama_index.core.llms.callbacks': mock_callbacks_llm,
        }

    def test_sentinel_llm_validates_safe_content_mocked(self, mock_llamaindex_module):
        """Test validation of safe content with mocked llama_index."""
        with patch.dict(sys.modules, mock_llamaindex_module):
            # Reload the module to pick up mocks
            import importlib
            import sentinelseed.integrations.llamaindex as llamaindex_mod

            # Force LLAMAINDEX_AVAILABLE to True
            original_available = llamaindex_mod.LLAMAINDEX_AVAILABLE
            llamaindex_mod.LLAMAINDEX_AVAILABLE = True

            try:
                mock_llm = MagicMock()
                llm = llamaindex_mod.SentinelLLM(llm=mock_llm)

                result = llm.validate("Hello, how can I help?")
                assert result.is_safe is True
            finally:
                llamaindex_mod.LLAMAINDEX_AVAILABLE = original_available

    def test_sentinel_llm_validates_unsafe_content_mocked(self, mock_llamaindex_module):
        """Test validation of unsafe content with mocked llama_index."""
        with patch.dict(sys.modules, mock_llamaindex_module):
            import sentinelseed.integrations.llamaindex as llamaindex_mod

            original_available = llamaindex_mod.LLAMAINDEX_AVAILABLE
            llamaindex_mod.LLAMAINDEX_AVAILABLE = True

            try:
                mock_llm = MagicMock()
                llm = llamaindex_mod.SentinelLLM(llm=mock_llm)

                # SQL injection
                result = llm.validate("DROP TABLE users;")
                assert result.is_safe is False
            finally:
                llamaindex_mod.LLAMAINDEX_AVAILABLE = original_available


class TestModuleExports:
    """Tests for module exports (no llama_index required)."""

    def test_module_exports_expected_classes(self):
        """Test that module exports expected classes."""
        from sentinelseed.integrations import llamaindex

        assert hasattr(llamaindex, "SentinelLLM")
        assert hasattr(llamaindex, "SentinelCallbackHandler")
        assert hasattr(llamaindex, "SentinelValidationEvent")

    def test_llamaindex_available_flag_exists(self):
        """Test that LLAMAINDEX_AVAILABLE flag exists."""
        from sentinelseed.integrations.llamaindex import LLAMAINDEX_AVAILABLE

        assert isinstance(LLAMAINDEX_AVAILABLE, bool)

    def test_semantic_available_flag_exists(self):
        """Test that SEMANTIC_AVAILABLE flag exists."""
        from sentinelseed.integrations.llamaindex import SEMANTIC_AVAILABLE

        assert isinstance(SEMANTIC_AVAILABLE, bool)
        assert SEMANTIC_AVAILABLE is True  # Always available via LayeredValidator

    def test_valid_violation_modes_exported(self):
        """Test that VALID_VIOLATION_MODES is exported."""
        from sentinelseed.integrations.llamaindex import VALID_VIOLATION_MODES

        assert isinstance(VALID_VIOLATION_MODES, frozenset)
        assert VALID_VIOLATION_MODES == {"log", "raise", "flag"}


class TestLayeredValidatorIntegration:
    """Tests for LayeredValidator integration pattern."""

    def test_sentinel_llm_accepts_validator_parameter(self):
        """Test that SentinelLLM accepts validator parameter."""
        from sentinelseed.integrations.llamaindex import SentinelLLM
        import inspect

        sig = inspect.signature(SentinelLLM.__init__)
        params = list(sig.parameters.keys())

        assert "validator" in params

    def test_callback_handler_accepts_validator_parameter(self):
        """Test that callback handler accepts validator parameter."""
        from sentinelseed.integrations.llamaindex import SentinelCallbackHandler
        import inspect

        sig = inspect.signature(SentinelCallbackHandler.__init__)
        params = list(sig.parameters.keys())

        assert "validator" in params


class TestOnViolationValidation:
    """Tests for on_violation parameter validation (BUG-002)."""

    def test_validate_on_violation_function_exists(self):
        """Test that _validate_on_violation function exists."""
        from sentinelseed.integrations.llamaindex import _validate_on_violation

        assert callable(_validate_on_violation)

    def test_validate_on_violation_accepts_valid_values(self):
        """Test that valid values are accepted."""
        from sentinelseed.integrations.llamaindex import _validate_on_violation

        assert _validate_on_violation("log") == "log"
        assert _validate_on_violation("raise") == "raise"
        assert _validate_on_violation("flag") == "flag"

    def test_validate_on_violation_defaults_to_log(self):
        """Test that None defaults to 'log'."""
        from sentinelseed.integrations.llamaindex import _validate_on_violation

        assert _validate_on_violation(None) == "log"

    def test_validate_on_violation_rejects_invalid_string(self):
        """Test that invalid string values raise ValueError."""
        from sentinelseed.integrations.llamaindex import _validate_on_violation

        with pytest.raises(ValueError) as exc_info:
            _validate_on_violation("invalid")

        assert "Invalid on_violation" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_validate_on_violation_rejects_non_string(self):
        """Test that non-string values raise ValueError."""
        from sentinelseed.integrations.llamaindex import _validate_on_violation

        with pytest.raises(ValueError):
            _validate_on_violation(123)

        with pytest.raises(ValueError):
            _validate_on_violation(["log"])

    @pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="llama-index-core not installed")
    def test_callback_handler_validates_on_violation(self):
        """Test that SentinelCallbackHandler validates on_violation."""
        from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

        # Valid values should work
        handler = SentinelCallbackHandler(on_violation="log")
        assert handler.on_violation == "log"

        handler = SentinelCallbackHandler(on_violation="raise")
        assert handler.on_violation == "raise"

        handler = SentinelCallbackHandler(on_violation="flag")
        assert handler.on_violation == "flag"

        # Invalid value should raise
        with pytest.raises(ValueError) as exc_info:
            SentinelCallbackHandler(on_violation="block")

        assert "Invalid on_violation" in str(exc_info.value)
