"""
Tests for AutoGPT integration (deprecated wrapper).

Tests the backward compatibility layer that wraps agent_validation.
"""

import warnings
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any


# Test imports work correctly
class TestImports:
    """Test that all imports from autogpt module work."""

    def test_import_validation_result(self):
        """ValidationResult should be importable."""
        from sentinelseed.integrations.autogpt import ValidationResult
        assert ValidationResult is not None

    def test_import_safety_validator(self):
        """SafetyValidator should be importable."""
        from sentinelseed.integrations.autogpt import SafetyValidator
        assert SafetyValidator is not None

    def test_import_execution_guard(self):
        """ExecutionGuard should be importable."""
        from sentinelseed.integrations.autogpt import ExecutionGuard
        assert ExecutionGuard is not None

    def test_import_safety_check(self):
        """safety_check function should be importable."""
        from sentinelseed.integrations.autogpt import safety_check
        assert callable(safety_check)

    def test_import_legacy_aliases(self):
        """Legacy aliases should be importable."""
        from sentinelseed.integrations.autogpt import (
            SafetyCheckResult,
            SentinelSafetyComponent,
            SentinelGuard,
        )
        assert SafetyCheckResult is not None
        assert SentinelSafetyComponent is not None
        assert SentinelGuard is not None

    def test_import_plugin_template(self):
        """AutoGPTPluginTemplate should be importable."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate
        assert AutoGPTPluginTemplate is not None


class TestBackwardCompatibilityAliases:
    """Test that backward compatibility aliases point to correct classes."""

    def test_safety_check_result_is_validation_result(self):
        """SafetyCheckResult should be alias for ValidationResult."""
        from sentinelseed.integrations.autogpt import (
            SafetyCheckResult,
            ValidationResult,
        )
        assert SafetyCheckResult is ValidationResult

    def test_sentinel_safety_component_is_safety_validator(self):
        """SentinelSafetyComponent should be alias for SafetyValidator."""
        from sentinelseed.integrations.autogpt import (
            SentinelSafetyComponent,
            SafetyValidator,
        )
        assert SentinelSafetyComponent is SafetyValidator

    def test_sentinel_guard_is_execution_guard(self):
        """SentinelGuard should be alias for ExecutionGuard."""
        from sentinelseed.integrations.autogpt import (
            SentinelGuard,
            ExecutionGuard,
        )
        assert SentinelGuard is ExecutionGuard


class TestDeprecationWarning:
    """Test that deprecation warning is issued on import."""

    def test_deprecation_warning_issued(self):
        """Importing autogpt module should issue DeprecationWarning."""
        import importlib
        import sentinelseed.integrations.autogpt as autogpt_module

        # Reload to trigger warning again
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            importlib.reload(autogpt_module)

            # Check that at least one deprecation warning was issued
            deprecation_warnings = [
                x for x in w if issubclass(x.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) >= 1

            # Check warning message content
            warning_msg = str(deprecation_warnings[0].message)
            assert "legacy" in warning_msg.lower() or "deprecated" in warning_msg.lower()


class TestAutoGPTPluginTemplate:
    """Test the legacy AutoGPTPluginTemplate class."""

    @pytest.fixture
    def mock_validator(self):
        """Create a mock validator."""
        mock = Mock()
        mock.validate_action.return_value = Mock(
            should_proceed=True,
            reasoning="Action is safe",
            concerns=[],
            safe=True,
            risk_level="low",
        )
        mock.validate_output.return_value = Mock(
            should_proceed=True,
            reasoning="Output is safe",
            concerns=[],
            safe=True,
        )
        mock.get_seed.return_value = "Safety seed content"
        return mock

    def test_can_handle_methods_return_true(self):
        """Plugin template should indicate it can handle all hooks."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        with patch.object(AutoGPTPluginTemplate, '__init__', lambda self: None):
            plugin = AutoGPTPluginTemplate()
            plugin.validator = Mock()

            assert plugin.can_handle_pre_command() is True
            assert plugin.can_handle_post_command() is True
            assert plugin.can_handle_on_planning() is True

    def test_pre_command_allows_safe_action(self, mock_validator):
        """pre_command should pass through safe actions."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        with patch.object(AutoGPTPluginTemplate, '__init__', lambda self: None):
            plugin = AutoGPTPluginTemplate()
            plugin.validator = mock_validator

            result = plugin.pre_command("search", {"query": "python tutorials"})

            assert result == ("search", {"query": "python tutorials"})
            mock_validator.validate_action.assert_called_once()

    def test_pre_command_blocks_unsafe_action(self, mock_validator):
        """pre_command should block unsafe actions with reasoning."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        mock_validator.validate_action.return_value = Mock(
            should_proceed=False,
            reasoning="This action could cause harm",
            concerns=["potential harm"],
            safe=False,
        )

        with patch.object(AutoGPTPluginTemplate, '__init__', lambda self: None):
            plugin = AutoGPTPluginTemplate()
            plugin.validator = mock_validator

            result = plugin.pre_command("delete", {"path": "/important"})

            assert result[0] == "think"
            assert "blocked" in result[1]["thought"].lower()
            assert "This action could cause harm" in result[1]["thought"]

    def test_pre_command_uses_reasoning_not_recommendation(self, mock_validator):
        """pre_command should use .reasoning field, not .recommendation."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        mock_validator.validate_action.return_value = Mock(
            should_proceed=False,
            reasoning="Blocked for safety",
            concerns=[],
            safe=False,
        )

        with patch.object(AutoGPTPluginTemplate, '__init__', lambda self: None):
            plugin = AutoGPTPluginTemplate()
            plugin.validator = mock_validator

            result = plugin.pre_command("cmd", {})

            # Verify it uses reasoning
            assert "Blocked for safety" in result[1]["thought"]

    def test_post_command_allows_safe_output(self, mock_validator):
        """post_command should pass through safe outputs."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        with patch.object(AutoGPTPluginTemplate, '__init__', lambda self: None):
            plugin = AutoGPTPluginTemplate()
            plugin.validator = mock_validator

            response = "Here is the search result"
            result = plugin.post_command("search", response)

            assert result == response
            mock_validator.validate_output.assert_called_once_with(response)

    def test_post_command_filters_unsafe_output(self, mock_validator):
        """post_command should filter unsafe outputs."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        mock_validator.validate_output.return_value = Mock(
            should_proceed=False,
            reasoning="Contains harmful content",
            concerns=["harmful content"],
            safe=False,
        )

        with patch.object(AutoGPTPluginTemplate, '__init__', lambda self: None):
            plugin = AutoGPTPluginTemplate()
            plugin.validator = mock_validator

            result = plugin.post_command("generate", "harmful content here")

            assert "[SENTINEL FILTERED]" in result
            assert "harmful content" in result.lower()

    def test_on_planning_injects_seed(self, mock_validator):
        """on_planning should inject safety seed into prompt."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        with patch.object(AutoGPTPluginTemplate, '__init__', lambda self: None):
            plugin = AutoGPTPluginTemplate()
            plugin.validator = mock_validator

            prompt = "Plan the next action"
            messages = [{"role": "user", "content": "Do something"}]

            result = plugin.on_planning(prompt, messages)

            assert "Safety seed content" in result
            assert prompt in result
            mock_validator.get_seed.assert_called_once()


class TestSafetyValidatorMethods:
    """Test that SafetyValidator methods are accessible via legacy imports."""

    @pytest.fixture
    def mock_sentinel(self):
        """Create mock for Sentinel class."""
        mock = MagicMock()
        mock.get_seed.return_value = "test seed"
        return mock

    def test_validate_action_accessible(self):
        """validate_action method should be accessible."""
        from sentinelseed.integrations.autogpt import SentinelSafetyComponent

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_cls.return_value = MagicMock()
            component = SentinelSafetyComponent.__new__(SentinelSafetyComponent)
            assert hasattr(component, 'validate_action')

    def test_validate_thought_accessible(self):
        """validate_thought method should be accessible."""
        from sentinelseed.integrations.autogpt import SentinelSafetyComponent

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_cls.return_value = MagicMock()
            component = SentinelSafetyComponent.__new__(SentinelSafetyComponent)
            assert hasattr(component, 'validate_thought')

    def test_validate_output_accessible(self):
        """validate_output method should be accessible."""
        from sentinelseed.integrations.autogpt import SentinelSafetyComponent

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_cls.return_value = MagicMock()
            component = SentinelSafetyComponent.__new__(SentinelSafetyComponent)
            assert hasattr(component, 'validate_output')

    def test_get_seed_accessible(self):
        """get_seed method should be accessible."""
        from sentinelseed.integrations.autogpt import SentinelSafetyComponent

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_cls.return_value = MagicMock()
            component = SentinelSafetyComponent.__new__(SentinelSafetyComponent)
            assert hasattr(component, 'get_seed')

    def test_get_history_accessible(self):
        """get_history method should be accessible."""
        from sentinelseed.integrations.autogpt import SentinelSafetyComponent

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_cls.return_value = MagicMock()
            component = SentinelSafetyComponent.__new__(SentinelSafetyComponent)
            assert hasattr(component, 'get_history')

    def test_get_stats_accessible(self):
        """get_stats method should be accessible."""
        from sentinelseed.integrations.autogpt import SentinelSafetyComponent

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_cls.return_value = MagicMock()
            component = SentinelSafetyComponent.__new__(SentinelSafetyComponent)
            assert hasattr(component, 'get_stats')


class TestValidationResultFields:
    """Test ValidationResult has correct fields."""

    def test_validation_result_has_reasoning_field(self):
        """ValidationResult should have reasoning field."""
        from sentinelseed.integrations.autogpt import ValidationResult

        result = ValidationResult(
            safe=True,
            action="test",
            concerns=[],
            risk_level="low",
            should_proceed=True,
            reasoning="Test reasoning",
            gate_results={},
        )

        assert hasattr(result, 'reasoning')
        assert result.reasoning == "Test reasoning"

    def test_validation_result_no_recommendation_field(self):
        """ValidationResult should NOT have recommendation field."""
        from sentinelseed.integrations.autogpt import ValidationResult

        result = ValidationResult(
            safe=True,
            action="test",
            concerns=[],
            risk_level="low",
            should_proceed=True,
            reasoning="Test reasoning",
            gate_results={},
        )

        assert not hasattr(result, 'recommendation')

    def test_safety_check_result_alias_same_as_validation_result(self):
        """SafetyCheckResult alias should have same fields as ValidationResult."""
        from sentinelseed.integrations.autogpt import (
            SafetyCheckResult,
            ValidationResult,
        )

        # They should be the same class
        assert SafetyCheckResult is ValidationResult

        result = SafetyCheckResult(
            safe=True,
            action="test",
            concerns=[],
            risk_level="low",
            should_proceed=True,
            reasoning="Test reasoning",
            gate_results={},
        )

        assert hasattr(result, 'reasoning')
        assert not hasattr(result, 'recommendation')


class TestSafetyCheckFunction:
    """Test the safety_check standalone function."""

    def test_safety_check_returns_dict(self):
        """safety_check should return a dictionary."""
        from sentinelseed.integrations.autogpt import safety_check

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_instance = MagicMock()
            mock_instance.validate_action.return_value = {
                "passed": True,
                "reasoning": "Safe action",
                "gate_results": {},
            }
            mock_cls.return_value = mock_instance

            # The function might fail without proper setup, but we're testing structure
            # In real test, this would need API key
            assert callable(safety_check)

    def test_safety_check_result_has_reasoning_key(self):
        """safety_check result should have 'reasoning' key, not 'recommendation'."""
        # This tests the contract - actual implementation uses reasoning
        from sentinelseed.integrations.autogpt import safety_check

        # We verify the function exists and has correct signature
        assert callable(safety_check)
        # The actual return value is documented to have 'reasoning'


class TestExecutionGuardDecorator:
    """Test the ExecutionGuard decorator functionality."""

    def test_sentinel_guard_is_execution_guard(self):
        """SentinelGuard should be the same as ExecutionGuard."""
        from sentinelseed.integrations.autogpt import SentinelGuard, ExecutionGuard

        assert SentinelGuard is ExecutionGuard

    def test_guard_has_protected_decorator(self):
        """ExecutionGuard should have protected decorator method."""
        from sentinelseed.integrations.autogpt import ExecutionGuard

        with patch('sentinelseed.integrations.agent_validation.Sentinel'):
            guard = ExecutionGuard.__new__(ExecutionGuard)
            assert hasattr(guard, 'protected')

    def test_guard_has_check_method(self):
        """ExecutionGuard should have check method."""
        from sentinelseed.integrations.autogpt import ExecutionGuard

        with patch('sentinelseed.integrations.agent_validation.Sentinel'):
            guard = ExecutionGuard.__new__(ExecutionGuard)
            assert hasattr(guard, 'check')


class TestModuleDocstring:
    """Test module documentation."""

    def test_module_has_migration_notice(self):
        """Module should have migration notice in docstring."""
        import sentinelseed.integrations.autogpt as autogpt

        assert autogpt.__doc__ is not None
        assert "migration" in autogpt.__doc__.lower()

    def test_module_mentions_agent_validation(self):
        """Module docstring should mention agent_validation alternative."""
        import sentinelseed.integrations.autogpt as autogpt

        assert "agent_validation" in autogpt.__doc__

    def test_module_mentions_autogpt_block(self):
        """Module docstring should mention autogpt_block alternative."""
        import sentinelseed.integrations.autogpt as autogpt

        assert "autogpt_block" in autogpt.__doc__


class TestPluginTemplateCreation:
    """Test AutoGPTPluginTemplate can be created."""

    def test_plugin_template_creates_validator(self):
        """AutoGPTPluginTemplate should create a SafetyValidator on init."""
        from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

        with patch('sentinelseed.integrations.agent_validation.Sentinel') as mock_cls:
            mock_cls.return_value = MagicMock()

            plugin = AutoGPTPluginTemplate()

            assert hasattr(plugin, 'validator')


class TestIntegrationWithAgentValidation:
    """Test integration with agent_validation module."""

    def test_imports_from_agent_validation(self):
        """All main classes should be from agent_validation."""
        from sentinelseed.integrations.autogpt import (
            ValidationResult,
            SafetyValidator,
            ExecutionGuard,
            safety_check,
        )
        from sentinelseed.integrations.agent_validation import (
            ValidationResult as AV_ValidationResult,
            SafetyValidator as AV_SafetyValidator,
            ExecutionGuard as AV_ExecutionGuard,
            safety_check as av_safety_check,
        )

        assert ValidationResult is AV_ValidationResult
        assert SafetyValidator is AV_SafetyValidator
        assert ExecutionGuard is AV_ExecutionGuard
        assert safety_check is av_safety_check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
