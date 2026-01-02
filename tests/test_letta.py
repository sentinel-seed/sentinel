"""
Tests for Sentinel Letta integration.

Tests cover:
- Module attributes and exports
- Input validation
- Validation functions
- Safety tools
- Client wrappers
- Approval handler
- Edge cases
"""

import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================================
# Module Imports
# ============================================================================

class TestModuleAttributes:
    """Test module-level attributes."""

    def test_version_exists(self):
        """Test __version__ is defined."""
        from sentinelseed.integrations.letta import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert __version__ == "1.0.0"

    def test_valid_modes_constant(self):
        """Test VALID_MODES constant."""
        from sentinelseed.integrations.letta import VALID_MODES
        assert VALID_MODES == ("block", "flag", "log")

    def test_valid_providers_constant(self):
        """Test VALID_PROVIDERS constant."""
        from sentinelseed.integrations.letta import VALID_PROVIDERS
        assert VALID_PROVIDERS == ("openai", "anthropic")

    def test_default_high_risk_tools_constant(self):
        """Test DEFAULT_HIGH_RISK_TOOLS constant."""
        from sentinelseed.integrations.letta import DEFAULT_HIGH_RISK_TOOLS
        assert "send_message" in DEFAULT_HIGH_RISK_TOOLS
        assert "run_code" in DEFAULT_HIGH_RISK_TOOLS
        assert "web_search" in DEFAULT_HIGH_RISK_TOOLS


class TestExports:
    """Test module exports."""

    def test_wrappers_exported(self):
        """Test wrapper classes are exported."""
        from sentinelseed.integrations.letta import (
            SentinelLettaClient,
            SentinelAgentsAPI,
            SentinelMessagesAPI,
            SafetyConfig,
            BlockedResponse,
            SafetyBlockedError,
            create_safe_agent,
        )
        assert SentinelLettaClient is not None
        assert SentinelAgentsAPI is not None
        assert SentinelMessagesAPI is not None
        assert SafetyConfig is not None
        assert BlockedResponse is not None
        assert SafetyBlockedError is not None
        assert create_safe_agent is not None

    def test_tools_exported(self):
        """Test tool classes are exported."""
        from sentinelseed.integrations.letta import (
            create_sentinel_tool,
            create_memory_guard_tool,
            SentinelSafetyTool,
            MemoryGuardTool,
            SENTINEL_TOOL_SOURCE,
            MEMORY_GUARD_TOOL_SOURCE,
        )
        assert create_sentinel_tool is not None
        assert create_memory_guard_tool is not None
        assert SentinelSafetyTool is not None
        assert MemoryGuardTool is not None
        assert SENTINEL_TOOL_SOURCE is not None
        assert MEMORY_GUARD_TOOL_SOURCE is not None

    def test_helpers_exported(self):
        """Test helper functions are exported."""
        from sentinelseed.integrations.letta import (
            sentinel_approval_handler,
            validate_message,
            validate_tool_call,
            async_validate_message,
            ApprovalDecision,
            ApprovalStatus,
        )
        assert sentinel_approval_handler is not None
        assert validate_message is not None
        assert validate_tool_call is not None
        assert async_validate_message is not None
        assert ApprovalDecision is not None
        assert ApprovalStatus is not None


# ============================================================================
# validate_message Tests
# ============================================================================

class TestValidateMessage:
    """Test validate_message function."""

    def test_none_content_raises(self):
        """Test that None content raises ValueError."""
        from sentinelseed.integrations.letta import validate_message
        with pytest.raises(ValueError, match="content cannot be None"):
            validate_message(None)

    def test_non_string_content_raises(self):
        """Test that non-string content raises ValueError."""
        from sentinelseed.integrations.letta import validate_message
        with pytest.raises(ValueError, match="content must be a string"):
            validate_message(123)

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises ValueError."""
        from sentinelseed.integrations.letta import validate_message
        with pytest.raises(ValueError, match="Invalid provider"):
            validate_message("test", provider="invalid")

    def test_empty_content_returns_safe(self):
        """Test that empty content returns safe result."""
        from sentinelseed.integrations.letta import validate_message
        result = validate_message("")
        assert result["is_safe"] is True
        assert result["method"] == "validation"

    def test_whitespace_content_returns_safe(self):
        """Test that whitespace-only content returns safe result."""
        from sentinelseed.integrations.letta import validate_message
        result = validate_message("   \n\t  ")
        assert result["is_safe"] is True

    def test_valid_content_returns_result(self):
        """Test that valid content returns result dict."""
        from sentinelseed.integrations.letta import validate_message
        result = validate_message("Hello, world!")
        assert "is_safe" in result
        assert "gates" in result
        assert "reasoning" in result
        assert "method" in result

    def test_heuristic_validation_used_without_api_key(self):
        """Test that heuristic validation is used without API key."""
        from sentinelseed.integrations.letta import validate_message
        result = validate_message("Test content")
        assert result["method"] in ("heuristic", "none")


# ============================================================================
# validate_tool_call Tests
# ============================================================================

class TestValidateToolCall:
    """Test validate_tool_call function."""

    def test_none_tool_name_raises(self):
        """Test that None tool_name raises ValueError."""
        from sentinelseed.integrations.letta import validate_tool_call
        with pytest.raises(ValueError, match="tool_name cannot be None"):
            validate_tool_call(None)

    def test_non_string_tool_name_raises(self):
        """Test that non-string tool_name raises ValueError."""
        from sentinelseed.integrations.letta import validate_tool_call
        with pytest.raises(ValueError, match="tool_name must be a string"):
            validate_tool_call(123)

    def test_empty_tool_name_raises(self):
        """Test that empty tool_name raises ValueError."""
        from sentinelseed.integrations.letta import validate_tool_call
        with pytest.raises(ValueError, match="tool_name cannot be empty"):
            validate_tool_call("")

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises ValueError."""
        from sentinelseed.integrations.letta import validate_tool_call
        with pytest.raises(ValueError, match="Invalid provider"):
            validate_tool_call("test_tool", provider="invalid")

    def test_none_arguments_handled(self):
        """Test that None arguments are handled."""
        from sentinelseed.integrations.letta import validate_tool_call
        result = validate_tool_call("test_tool", arguments=None)
        assert "is_safe" in result

    def test_non_dict_arguments_converted(self):
        """Test that non-dict arguments are converted."""
        from sentinelseed.integrations.letta import validate_tool_call
        result = validate_tool_call("test_tool", arguments="some_value")
        assert "is_safe" in result

    def test_high_risk_tool_marked_high(self):
        """Test that high-risk tools get high risk level."""
        from sentinelseed.integrations.letta import validate_tool_call
        result = validate_tool_call("run_code", arguments={"code": "print('hi')"})
        assert result["risk_level"] == "high"

    def test_medium_risk_tool_detected(self):
        """Test that medium-risk tools are detected."""
        from sentinelseed.integrations.letta import validate_tool_call
        result = validate_tool_call("write_file", arguments={})
        assert result["risk_level"] == "medium"

    def test_low_risk_tool_default(self):
        """Test that unknown tools default to low risk."""
        from sentinelseed.integrations.letta import validate_tool_call
        result = validate_tool_call("read_file", arguments={})
        assert result["risk_level"] == "low"


# ============================================================================
# sentinel_approval_handler Tests
# ============================================================================

class TestSentinelApprovalHandler:
    """Test sentinel_approval_handler function."""

    def test_none_request_raises(self):
        """Test that None request raises ValueError."""
        from sentinelseed.integrations.letta import sentinel_approval_handler
        with pytest.raises(ValueError, match="approval_request cannot be None"):
            sentinel_approval_handler(None)

    def test_non_dict_request_raises(self):
        """Test that non-dict request raises ValueError."""
        from sentinelseed.integrations.letta import sentinel_approval_handler
        with pytest.raises(ValueError, match="approval_request must be a dict"):
            sentinel_approval_handler("invalid")

    def test_empty_request_handled(self):
        """Test that empty request is handled."""
        from sentinelseed.integrations.letta import sentinel_approval_handler
        result = sentinel_approval_handler({})
        assert hasattr(result, "status")
        assert hasattr(result, "approve")
        assert hasattr(result, "tool_call_id")

    def test_valid_request_returns_decision(self):
        """Test that valid request returns ApprovalDecision."""
        from sentinelseed.integrations.letta import (
            sentinel_approval_handler,
            ApprovalDecision,
        )
        result = sentinel_approval_handler({
            "tool_name": "test_tool",
            "arguments": {},
            "tool_call_id": "call-123",
        })
        assert isinstance(result, ApprovalDecision)

    def test_to_approval_message_format(self):
        """Test to_approval_message returns correct format."""
        from sentinelseed.integrations.letta import sentinel_approval_handler
        result = sentinel_approval_handler({
            "tool_name": "test_tool",
            "arguments": {},
            "tool_call_id": "call-123",
        })
        msg = result.to_approval_message()
        assert "type" in msg
        assert msg["type"] == "approval"
        assert "approvals" in msg
        assert isinstance(msg["approvals"], list)


# ============================================================================
# ApprovalDecision Tests
# ============================================================================

class TestApprovalDecision:
    """Test ApprovalDecision class."""

    def test_creation(self):
        """Test ApprovalDecision creation."""
        from sentinelseed.integrations.letta import ApprovalDecision, ApprovalStatus
        decision = ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approve=True,
            tool_call_id="call-123",
            reason="Test reason",
        )
        assert decision.status == ApprovalStatus.APPROVED
        assert decision.approve is True
        assert decision.tool_call_id == "call-123"
        assert decision.reason == "Test reason"

    def test_to_approval_message(self):
        """Test to_approval_message method."""
        from sentinelseed.integrations.letta import ApprovalDecision, ApprovalStatus
        decision = ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approve=True,
            tool_call_id="call-123",
            reason="Test reason",
        )
        msg = decision.to_approval_message()
        assert msg["type"] == "approval"
        assert len(msg["approvals"]) == 1
        assert msg["approvals"][0]["approve"] is True
        assert msg["approvals"][0]["tool_call_id"] == "call-123"


# ============================================================================
# SentinelSafetyTool Tests
# ============================================================================

class TestSentinelSafetyTool:
    """Test SentinelSafetyTool class."""

    def test_creation(self):
        """Test SentinelSafetyTool creation."""
        from sentinelseed.integrations.letta import SentinelSafetyTool
        tool = SentinelSafetyTool()
        assert tool.name == "sentinel_safety_check"
        assert tool.requires_approval is False

    def test_run_none_content(self):
        """Test run with None content returns error."""
        from sentinelseed.integrations.letta import SentinelSafetyTool
        tool = SentinelSafetyTool()
        result = tool.run(None)
        assert "ERROR" in result

    def test_run_non_string_content(self):
        """Test run with non-string content returns error."""
        from sentinelseed.integrations.letta import SentinelSafetyTool
        tool = SentinelSafetyTool()
        result = tool.run(123)
        assert "ERROR" in result

    def test_run_empty_content(self):
        """Test run with empty content returns safe."""
        from sentinelseed.integrations.letta import SentinelSafetyTool
        tool = SentinelSafetyTool()
        result = tool.run("")
        assert "SAFE" in result

    def test_run_no_validator(self):
        """Test run without validator returns warning."""
        from sentinelseed.integrations.letta import SentinelSafetyTool
        tool = SentinelSafetyTool()
        result = tool.run("test content")
        assert "WARNING" in result


# ============================================================================
# MemoryGuardTool Tests
# ============================================================================

class TestMemoryGuardTool:
    """Test MemoryGuardTool class."""

    def test_creation(self):
        """Test MemoryGuardTool creation."""
        from sentinelseed.integrations.letta import MemoryGuardTool
        tool = MemoryGuardTool()
        assert tool.name == "verify_memory_integrity"
        assert tool.requires_approval is False

    def test_run_none_label(self):
        """Test run with None label returns error."""
        from sentinelseed.integrations.letta import MemoryGuardTool
        tool = MemoryGuardTool()
        tool.initialize("test-secret")
        result = tool.run(None)
        assert "ERROR" in result

    def test_run_empty_label(self):
        """Test run with empty label returns error."""
        from sentinelseed.integrations.letta import MemoryGuardTool
        tool = MemoryGuardTool()
        tool.initialize("test-secret")
        result = tool.run("")
        assert "ERROR" in result

    def test_run_no_secret(self):
        """Test run without initialization returns error."""
        from sentinelseed.integrations.letta import MemoryGuardTool
        tool = MemoryGuardTool()
        result = tool.run("human")
        assert "ERROR" in result
        assert "not initialized" in result

    def test_run_with_secret(self):
        """Test run with initialization returns HMAC hash."""
        from sentinelseed.integrations.letta import MemoryGuardTool
        tool = MemoryGuardTool()
        tool.initialize("test-secret")
        result = tool.run("human", content="test content")
        assert "HASH:" in result
        # Hash should be 64-char SHA256 hex
        hash_value = result.split(": ")[1] if ": " in result else ""
        assert len(hash_value) == 64


# ============================================================================
# create_sentinel_tool Tests
# ============================================================================

class TestCreateSentinelTool:
    """Test create_sentinel_tool function."""

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises ValueError."""
        from sentinelseed.integrations.letta import create_sentinel_tool
        with pytest.raises(ValueError, match="Invalid provider"):
            create_sentinel_tool(None, provider="invalid")

    def test_none_client_returns_tool(self):
        """Test that None client returns tool without registration."""
        from sentinelseed.integrations.letta import create_sentinel_tool, SentinelSafetyTool
        tool = create_sentinel_tool(None)
        assert isinstance(tool, SentinelSafetyTool)

    def test_tool_created_with_defaults(self):
        """Test tool is created with default values."""
        from sentinelseed.integrations.letta import create_sentinel_tool
        tool = create_sentinel_tool(None)
        assert tool.name == "sentinel_safety_check"
        assert tool.requires_approval is False


# ============================================================================
# create_memory_guard_tool Tests
# ============================================================================

class TestCreateMemoryGuardTool:
    """Test create_memory_guard_tool function."""

    def test_none_secret_raises(self):
        """Test that None secret raises ValueError."""
        from sentinelseed.integrations.letta import create_memory_guard_tool
        with pytest.raises(ValueError, match="secret cannot be None"):
            create_memory_guard_tool(None, None)

    def test_empty_secret_raises(self):
        """Test that empty secret raises ValueError."""
        from sentinelseed.integrations.letta import create_memory_guard_tool
        with pytest.raises(ValueError, match="secret cannot be empty"):
            create_memory_guard_tool(None, "")

    def test_non_string_secret_raises(self):
        """Test that non-string secret raises ValueError."""
        from sentinelseed.integrations.letta import create_memory_guard_tool
        with pytest.raises(ValueError, match="secret must be a string"):
            create_memory_guard_tool(None, 123)

    def test_valid_secret_creates_tool(self):
        """Test that valid secret creates tool."""
        from sentinelseed.integrations.letta import create_memory_guard_tool, MemoryGuardTool
        tool = create_memory_guard_tool(None, "test-secret")
        assert isinstance(tool, MemoryGuardTool)
        assert tool._secret == "test-secret"


# ============================================================================
# SafetyBlockedError Tests
# ============================================================================

class TestSafetyBlockedError:
    """Test SafetyBlockedError exception."""

    def test_creation(self):
        """Test SafetyBlockedError creation."""
        from sentinelseed.integrations.letta import SafetyBlockedError
        error = SafetyBlockedError("Test message")
        assert str(error) == "Test message"

    def test_with_validation_result(self):
        """Test SafetyBlockedError with validation result."""
        from sentinelseed.integrations.letta import SafetyBlockedError
        error = SafetyBlockedError(
            "Test message",
            validation_result={"is_safe": False},
            context="input",
        )
        assert error.validation_result == {"is_safe": False}
        assert error.context == "input"

    def test_str_with_context(self):
        """Test __str__ with context."""
        from sentinelseed.integrations.letta import SafetyBlockedError
        error = SafetyBlockedError("Test message", context="input")
        assert "input" in str(error)


# ============================================================================
# SafetyConfig Tests
# ============================================================================

class TestSafetyConfig:
    """Test SafetyConfig dataclass."""

    def test_creation_with_defaults(self):
        """Test SafetyConfig creation with defaults."""
        from sentinelseed.integrations.letta import SafetyConfig
        config = SafetyConfig()
        assert config.mode == "block"
        assert config.validate_input is True
        assert config.validate_output is True

    def test_creation_with_values(self):
        """Test SafetyConfig creation with custom values."""
        from sentinelseed.integrations.letta import SafetyConfig
        config = SafetyConfig(
            api_key="test-key",
            mode="flag",
            validate_input=False,
        )
        assert config.api_key == "test-key"
        assert config.mode == "flag"
        assert config.validate_input is False


# ============================================================================
# BlockedResponse Tests
# ============================================================================

class TestBlockedResponse:
    """Test BlockedResponse dataclass."""

    def test_creation_with_defaults(self):
        """Test BlockedResponse creation with defaults."""
        from sentinelseed.integrations.letta import BlockedResponse
        response = BlockedResponse()
        assert response.blocked is True
        assert response.messages == []

    def test_creation_with_values(self):
        """Test BlockedResponse creation with custom values."""
        from sentinelseed.integrations.letta import BlockedResponse
        response = BlockedResponse(
            blocked=True,
            safety_validation={"is_safe": False},
            reason="Test reason",
        )
        assert response.blocked is True
        assert response.safety_validation == {"is_safe": False}
        assert response.reason == "Test reason"


# ============================================================================
# SentinelLettaClient Tests
# ============================================================================

@dataclass
class MockAgent:
    """Mock agent for testing."""
    id: str = "agent-123"


@dataclass
class MockTool:
    """Mock tool for testing."""
    id: str = "tool-123"
    name: str = "test_tool"


class MockToolsAPI:
    """Mock tools API for testing."""

    def create(self, source_code: str = None, **kwargs):
        return MockTool()

    def modify_approval(self, agent_id: str, tool_name: str, requires_approval: bool):
        pass


class MockMessagesAPI:
    """Mock messages API for testing."""

    def create(self, agent_id: str, input: str = None, **kwargs):
        @dataclass
        class MockMessage:
            content: str = "Response"

        @dataclass
        class MockResponse:
            messages: List = field(default_factory=lambda: [MockMessage()])

        return MockResponse()


class MockAgentsAPI:
    """Mock agents API for testing."""

    def __init__(self):
        self.messages = MockMessagesAPI()
        self.tools = MockToolsAPI()

    def create(self, **kwargs):
        return MockAgent()


class MockLettaClient:
    """Mock Letta client for testing."""

    def __init__(self):
        self.agents = MockAgentsAPI()
        self.tools = MockToolsAPI()


class TestSentinelLettaClient:
    """Test SentinelLettaClient class."""

    def test_none_client_raises(self):
        """Test that None client raises ValueError."""
        from sentinelseed.integrations.letta import SentinelLettaClient
        with pytest.raises(ValueError, match="client cannot be None"):
            SentinelLettaClient(None)

    def test_invalid_mode_raises(self):
        """Test that invalid mode raises ValueError."""
        from sentinelseed.integrations.letta import SentinelLettaClient
        with pytest.raises(ValueError, match="Invalid mode"):
            SentinelLettaClient(MockLettaClient(), mode="invalid")

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises ValueError."""
        from sentinelseed.integrations.letta import SentinelLettaClient
        with pytest.raises(ValueError, match="Invalid provider"):
            SentinelLettaClient(MockLettaClient(), provider="invalid")

    def test_valid_client_creates_wrapper(self):
        """Test that valid client creates wrapper."""
        from sentinelseed.integrations.letta import SentinelLettaClient
        client = SentinelLettaClient(MockLettaClient())
        assert client is not None
        assert hasattr(client, "agents")
        assert hasattr(client, "config")

    def test_agents_property(self):
        """Test agents property returns wrapped API."""
        from sentinelseed.integrations.letta import SentinelLettaClient, SentinelAgentsAPI
        client = SentinelLettaClient(MockLettaClient())
        assert isinstance(client.agents, SentinelAgentsAPI)

    def test_config_property(self):
        """Test config property returns SafetyConfig."""
        from sentinelseed.integrations.letta import SentinelLettaClient, SafetyConfig
        client = SentinelLettaClient(MockLettaClient())
        assert isinstance(client.config, SafetyConfig)


# ============================================================================
# Async Tests
# ============================================================================

class TestAsyncValidateMessage:
    """Test async_validate_message function."""

    def test_none_content_raises(self):
        """Test that None content raises ValueError."""
        import asyncio
        from sentinelseed.integrations.letta import async_validate_message

        async def run_test():
            with pytest.raises(ValueError, match="content cannot be None"):
                await async_validate_message(None)

        asyncio.run(run_test())

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises ValueError."""
        import asyncio
        from sentinelseed.integrations.letta import async_validate_message

        async def run_test():
            with pytest.raises(ValueError, match="Invalid provider"):
                await async_validate_message("test", provider="invalid")

        asyncio.run(run_test())

    def test_empty_content_returns_safe(self):
        """Test that empty content returns safe result."""
        import asyncio
        from sentinelseed.integrations.letta import async_validate_message

        async def run_test():
            result = await async_validate_message("")
            assert result["is_safe"] is True

        asyncio.run(run_test())

    def test_valid_content_returns_result(self):
        """Test that valid content returns result."""
        import asyncio
        from sentinelseed.integrations.letta import async_validate_message

        async def run_test():
            result = await async_validate_message("Hello, world!")
            assert "is_safe" in result
            assert "method" in result

        asyncio.run(run_test())


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_content(self):
        """Test validation with very long content."""
        from sentinelseed.integrations.letta import validate_message
        long_content = "x" * 10000
        result = validate_message(long_content)
        assert "is_safe" in result

    def test_unicode_content(self):
        """Test validation with unicode content."""
        from sentinelseed.integrations.letta import validate_message
        result = validate_message("Hello, 世界! 🌍")
        assert "is_safe" in result

    def test_special_characters(self):
        """Test validation with special characters."""
        from sentinelseed.integrations.letta import validate_message
        result = validate_message("<script>alert('xss')</script>")
        assert "is_safe" in result

    def test_newlines_in_content(self):
        """Test validation with newlines."""
        from sentinelseed.integrations.letta import validate_message
        result = validate_message("Line 1\nLine 2\nLine 3")
        assert "is_safe" in result

    def test_very_long_arguments(self):
        """Test validate_tool_call with very long arguments."""
        from sentinelseed.integrations.letta import validate_tool_call
        long_args = {"data": "x" * 10000}
        result = validate_tool_call("test_tool", arguments=long_args)
        assert "is_safe" in result


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_workflow(self):
        """Test a full workflow with wrapped client."""
        from sentinelseed.integrations.letta import (
            SentinelLettaClient,
            create_sentinel_tool,
        )

        # Create client
        base_client = MockLettaClient()
        client = SentinelLettaClient(
            base_client,
            mode="flag",
            validate_input=True,
            validate_output=True,
        )

        # Create agent
        agent = client.agents.create(
            model="openai/gpt-4o-mini",
            memory_blocks=[],
        )
        assert agent is not None

    def test_approval_workflow(self):
        """Test approval handler workflow."""
        from sentinelseed.integrations.letta import (
            sentinel_approval_handler,
            ApprovalStatus,
        )

        # Simulate approval request
        request = {
            "tool_name": "read_file",
            "arguments": {"path": "/safe/path.txt"},
            "tool_call_id": "call-abc",
        }

        decision = sentinel_approval_handler(
            request,
            auto_approve_safe=True,
            auto_deny_unsafe=True,
        )

        assert decision.tool_call_id == "call-abc"
        assert hasattr(decision, "status")
        assert hasattr(decision, "approve")
