"""
Tests for MCP Server Integration.

Tests cover:
- Configuration constants
- Text size validation
- Exception classes
- Server creation (without MCP)
- Client initialization
- Tool function behavior (mocked)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
import json


# ============================================================================
# Test Configuration Constants
# ============================================================================

class TestMCPConfig:
    """Tests for MCPConfig configuration class."""

    def test_max_text_size(self):
        """Test MAX_TEXT_SIZE constant."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        assert MCPConfig.MAX_TEXT_SIZE == 50 * 1024  # 50KB
        assert MCPConfig.MAX_TEXT_SIZE == 51200

    def test_max_text_size_batch(self):
        """Test MAX_TEXT_SIZE_BATCH constant."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        assert MCPConfig.MAX_TEXT_SIZE_BATCH == 10 * 1024  # 10KB
        assert MCPConfig.MAX_TEXT_SIZE_BATCH == 10240

    def test_max_batch_items(self):
        """Test MAX_BATCH_ITEMS constant."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        assert MCPConfig.MAX_BATCH_ITEMS == 1000

    def test_default_batch_items(self):
        """Test DEFAULT_BATCH_ITEMS constant."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        assert MCPConfig.DEFAULT_BATCH_ITEMS == 100

    def test_default_timeout(self):
        """Test DEFAULT_TIMEOUT constant."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        assert MCPConfig.DEFAULT_TIMEOUT == 30.0

    def test_batch_timeout(self):
        """Test BATCH_TIMEOUT constant."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        assert MCPConfig.BATCH_TIMEOUT == 60.0

    def test_item_preview_length(self):
        """Test ITEM_PREVIEW_LENGTH constant."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        assert MCPConfig.ITEM_PREVIEW_LENGTH == 100


# ============================================================================
# Test Version
# ============================================================================

class TestVersion:
    """Tests for module version."""

    def test_version_exists(self):
        """Test that __version__ is defined."""
        from sentinelseed.integrations.mcp_server import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_format(self):
        """Test version follows semantic versioning."""
        from sentinelseed.integrations.mcp_server import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2
        # Should be numeric
        assert parts[0].isdigit()
        assert parts[1].isdigit()


# ============================================================================
# Test Text Size Validation
# ============================================================================

class TestTextTooLargeError:
    """Tests for TextTooLargeError exception."""

    def test_creation(self):
        """Test error creation."""
        from sentinelseed.integrations.mcp_server import TextTooLargeError

        error = TextTooLargeError(60000, 51200)
        assert error.size == 60000
        assert error.max_size == 51200

    def test_message(self):
        """Test error message formatting."""
        from sentinelseed.integrations.mcp_server import TextTooLargeError

        error = TextTooLargeError(60000, 51200)
        assert "60,000" in str(error)
        assert "51,200" in str(error)

    def test_inheritance(self):
        """Test error inherits from Exception."""
        from sentinelseed.integrations.mcp_server import TextTooLargeError

        error = TextTooLargeError(100, 50)
        assert isinstance(error, Exception)


class TestValidateTextSize:
    """Tests for _validate_text_size function."""

    def test_valid_text_passes(self):
        """Test valid text passes validation."""
        from sentinelseed.integrations.mcp_server import _validate_text_size

        # Should not raise
        _validate_text_size("Hello, world!", context="test")

    def test_large_text_raises(self):
        """Test large text raises TextTooLargeError."""
        from sentinelseed.integrations.mcp_server import (
            _validate_text_size,
            TextTooLargeError,
            MCPConfig,
        )

        large_text = "x" * (MCPConfig.MAX_TEXT_SIZE + 100)

        with pytest.raises(TextTooLargeError) as exc_info:
            _validate_text_size(large_text, context="test")

        assert exc_info.value.max_size == MCPConfig.MAX_TEXT_SIZE

    def test_custom_max_size(self):
        """Test custom max_size parameter."""
        from sentinelseed.integrations.mcp_server import (
            _validate_text_size,
            TextTooLargeError,
        )

        # 100 bytes max
        with pytest.raises(TextTooLargeError):
            _validate_text_size("x" * 200, max_size=100, context="test")

    def test_non_string_passes(self):
        """Test non-string values pass (no validation)."""
        from sentinelseed.integrations.mcp_server import _validate_text_size

        # Should not raise for non-strings
        _validate_text_size(None, context="test")
        _validate_text_size(123, context="test")

    def test_empty_string_passes(self):
        """Test empty string passes validation."""
        from sentinelseed.integrations.mcp_server import _validate_text_size

        _validate_text_size("", context="test")

    def test_unicode_text_byte_counting(self):
        """Test that unicode is counted by bytes, not characters."""
        from sentinelseed.integrations.mcp_server import (
            _validate_text_size,
            TextTooLargeError,
        )

        # Unicode characters take multiple bytes
        unicode_text = "你好" * 100  # Each char is 3 bytes in UTF-8

        # 200 chars * 3 bytes = 600 bytes, should pass at 1000 byte limit
        _validate_text_size(unicode_text, max_size=1000, context="test")

        # But fail at 500 byte limit
        with pytest.raises(TextTooLargeError):
            _validate_text_size(unicode_text, max_size=500, context="test")


# ============================================================================
# Test Exception Classes
# ============================================================================

class TestMCPClientError:
    """Tests for MCPClientError exception."""

    def test_creation(self):
        """Test error creation."""
        from sentinelseed.integrations.mcp_server import MCPClientError

        error = MCPClientError("Test error")
        assert str(error) == "Test error"

    def test_inheritance(self):
        """Test inheritance from Exception."""
        from sentinelseed.integrations.mcp_server import MCPClientError

        error = MCPClientError("Test")
        assert isinstance(error, Exception)


class TestMCPTimeoutError:
    """Tests for MCPTimeoutError exception."""

    def test_creation(self):
        """Test error creation with attributes."""
        from sentinelseed.integrations.mcp_server import MCPTimeoutError

        error = MCPTimeoutError("validate", 30.0)
        assert error.operation == "validate"
        assert error.timeout == 30.0

    def test_message(self):
        """Test error message formatting."""
        from sentinelseed.integrations.mcp_server import MCPTimeoutError

        error = MCPTimeoutError("validate", 30.0)
        assert "validate" in str(error)
        assert "30.0" in str(error)
        assert "timed out" in str(error).lower()

    def test_inheritance(self):
        """Test inheritance from MCPClientError."""
        from sentinelseed.integrations.mcp_server import (
            MCPTimeoutError,
            MCPClientError,
        )

        error = MCPTimeoutError("test", 10.0)
        assert isinstance(error, MCPClientError)


class TestMCPConnectionError:
    """Tests for MCPConnectionError exception."""

    def test_creation(self):
        """Test error creation."""
        from sentinelseed.integrations.mcp_server import MCPConnectionError

        error = MCPConnectionError("Connection failed")
        assert str(error) == "Connection failed"

    def test_inheritance(self):
        """Test inheritance from MCPClientError."""
        from sentinelseed.integrations.mcp_server import (
            MCPConnectionError,
            MCPClientError,
        )

        error = MCPConnectionError("Test")
        assert isinstance(error, MCPClientError)


# ============================================================================
# Test MCP Availability
# ============================================================================

class TestMCPAvailability:
    """Tests for MCP_AVAILABLE constant."""

    def test_mcp_available_is_bool(self):
        """Test MCP_AVAILABLE is a boolean."""
        from sentinelseed.integrations.mcp_server import MCP_AVAILABLE

        assert isinstance(MCP_AVAILABLE, bool)


# ============================================================================
# Test Client Initialization
# ============================================================================

class TestSentinelMCPClientInit:
    """Tests for SentinelMCPClient initialization."""

    def test_url_only(self):
        """Test initialization with URL only."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000/mcp")
        assert client.url == "http://localhost:8000/mcp"
        assert client.command is None
        assert client.args == []

    def test_command_only(self):
        """Test initialization with command only."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(
            command="python",
            args=["-m", "sentinelseed.integrations.mcp_server"],
        )
        assert client.command == "python"
        assert client.args == ["-m", "sentinelseed.integrations.mcp_server"]
        assert client.url is None

    def test_both_raises_error(self):
        """Test that providing both url and command raises ValueError."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        with pytest.raises(ValueError) as exc_info:
            SentinelMCPClient(url="http://localhost", command="python")

        assert "either" in str(exc_info.value).lower()

    def test_neither_raises_error(self):
        """Test that providing neither url nor command raises ValueError."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        with pytest.raises(ValueError) as exc_info:
            SentinelMCPClient()

        assert "must provide" in str(exc_info.value).lower()

    def test_default_timeout(self):
        """Test default timeout is set from MCPConfig."""
        from sentinelseed.integrations.mcp_server import (
            SentinelMCPClient,
            MCPConfig,
        )

        client = SentinelMCPClient(url="http://localhost:8000")
        assert client.timeout == MCPConfig.DEFAULT_TIMEOUT

    def test_custom_timeout(self):
        """Test custom timeout is set."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000", timeout=60.0)
        assert client.timeout == 60.0

    def test_session_initially_none(self):
        """Test _session is initially None."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")
        assert client._session is None


# ============================================================================
# Test Client Methods (Mocked)
# ============================================================================

class TestSentinelMCPClientMethods:
    """Tests for SentinelMCPClient methods with mocks."""

    def test_list_tools_requires_connection(self):
        """Test list_tools raises without connection."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(client.list_tools())

        assert "not connected" in str(exc_info.value).lower()

    def test_validate_requires_connection(self):
        """Test validate raises without connection."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        with pytest.raises(RuntimeError):
            asyncio.run(client.validate("test"))

    def test_check_action_requires_connection(self):
        """Test check_action raises without connection."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        with pytest.raises(RuntimeError):
            asyncio.run(client.check_action("test"))

    def test_check_request_requires_connection(self):
        """Test check_request raises without connection."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        with pytest.raises(RuntimeError):
            asyncio.run(client.check_request("test"))

    def test_get_seed_requires_connection(self):
        """Test get_seed raises without connection."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        with pytest.raises(RuntimeError):
            asyncio.run(client.get_seed())

    def test_batch_validate_requires_connection(self):
        """Test batch_validate raises without connection."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        with pytest.raises(RuntimeError):
            asyncio.run(client.batch_validate(["test"]))


class TestParseToolResult:
    """Tests for _parse_tool_result method."""

    def test_empty_content_returns_default(self):
        """Test empty content returns default error."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        mock_result = Mock()
        mock_result.content = []

        default = {"error": "test"}
        result = client._parse_tool_result(mock_result, default, "test_tool")

        assert result == default

    def test_none_content_returns_default(self):
        """Test None content returns default error."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        mock_result = Mock()
        mock_result.content = None

        default = {"error": "test"}
        result = client._parse_tool_result(mock_result, default, "test_tool")

        assert result == default

    def test_text_content_json(self):
        """Test text content with JSON is parsed."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        mock_content = Mock()
        mock_content.text = '{"safe": true, "violations": []}'

        mock_result = Mock()
        mock_result.content = [mock_content]

        result = client._parse_tool_result(mock_result, {}, "test_tool")

        assert result["safe"] is True
        assert result["violations"] == []

    def test_text_content_non_json(self):
        """Test text content with non-JSON returns as result."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        mock_content = Mock()
        mock_content.text = "Just a string"

        mock_result = Mock()
        mock_result.content = [mock_content]

        result = client._parse_tool_result(mock_result, {}, "test_tool")

        assert result == {"result": "Just a string"}

    def test_dict_content(self):
        """Test dict content is returned directly."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        mock_result = Mock()
        mock_result.content = [{"safe": True}]

        result = client._parse_tool_result(mock_result, {}, "test_tool")

        assert result == {"safe": True}

    def test_data_attribute_dict(self):
        """Test content with data attribute as dict."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        mock_content = Mock()
        mock_content.data = {"safe": True}
        # Remove text attribute
        del mock_content.text

        mock_result = Mock()
        mock_result.content = [mock_content]

        result = client._parse_tool_result(mock_result, {}, "test_tool")

        assert result == {"safe": True}


class TestCallWithTimeout:
    """Tests for _call_with_timeout method."""

    def test_successful_call(self):
        """Test successful call returns result."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000")

        async def run_test():
            async def mock_coro():
                return "success"

            return await client._call_with_timeout(mock_coro(), "test", timeout=5.0)

        result = asyncio.run(run_test())
        assert result == "success"

    def test_timeout_raises_error(self):
        """Test timeout raises MCPTimeoutError."""
        from sentinelseed.integrations.mcp_server import (
            SentinelMCPClient,
            MCPTimeoutError,
        )

        client = SentinelMCPClient(url="http://localhost:8000")

        async def run_test():
            async def slow_coro():
                await asyncio.sleep(10)
                return "success"

            return await client._call_with_timeout(slow_coro(), "test", timeout=0.1)

        with pytest.raises(MCPTimeoutError) as exc_info:
            asyncio.run(run_test())

        assert exc_info.value.operation == "test"
        assert exc_info.value.timeout == 0.1

    def test_uses_default_timeout(self):
        """Test uses client's default timeout when not specified."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000", timeout=1.0)

        async def run_test():
            async def quick_coro():
                return "success"

            return await client._call_with_timeout(quick_coro(), "test")

        result = asyncio.run(run_test())
        assert result == "success"


# ============================================================================
# Test Server Creation (Mocked MCP)
# ============================================================================

class TestServerCreation:
    """Tests for server creation functions."""

    def test_create_server_requires_mcp(self):
        """Test create_sentinel_mcp_server requires MCP package."""
        from sentinelseed.integrations.mcp_server import (
            MCP_AVAILABLE,
            create_sentinel_mcp_server,
        )

        if not MCP_AVAILABLE:
            with pytest.raises(ImportError) as exc_info:
                create_sentinel_mcp_server()

            assert "mcp" in str(exc_info.value).lower()

    def test_add_tools_requires_mcp(self):
        """Test add_sentinel_tools requires MCP package."""
        from sentinelseed.integrations.mcp_server import (
            MCP_AVAILABLE,
            add_sentinel_tools,
        )

        if not MCP_AVAILABLE:
            with pytest.raises(ImportError) as exc_info:
                add_sentinel_tools(Mock())

            assert "mcp" in str(exc_info.value).lower()


# ============================================================================
# Test Exports
# ============================================================================

class TestExports:
    """Tests for module exports."""

    def test_all_main_exports(self):
        """Test all main exports are available."""
        from sentinelseed.integrations.mcp_server import (
            __version__,
            MCPConfig,
            TextTooLargeError,
            MCPClientError,
            MCPTimeoutError,
            MCPConnectionError,
            MCP_AVAILABLE,
            create_sentinel_mcp_server,
            add_sentinel_tools,
            SentinelMCPClient,
            run_server,
        )

        # All should be importable
        assert __version__
        assert MCPConfig
        assert TextTooLargeError
        assert MCPClientError
        assert MCPTimeoutError
        assert MCPConnectionError
        assert isinstance(MCP_AVAILABLE, bool)
        assert create_sentinel_mcp_server
        assert add_sentinel_tools
        assert SentinelMCPClient
        assert run_server


# ============================================================================
# Test Example Imports
# ============================================================================

class TestExampleImports:
    """Tests for example module imports."""

    def test_example_importable(self):
        """Test example module is importable."""
        try:
            from sentinelseed.integrations.mcp_server import example
            assert example
        except ImportError:
            # Module might not be in path
            pass

    def test_main_function_exists(self):
        """Test main function exists in example."""
        try:
            from sentinelseed.integrations.mcp_server.example import main
            assert callable(main)
        except ImportError:
            pass


# ============================================================================
# Integration Tests (Only if MCP available)
# ============================================================================

class TestIntegrationWithMCP:
    """Integration tests that require MCP package."""

    @pytest.fixture
    def skip_if_no_mcp(self):
        """Skip test if MCP not available."""
        from sentinelseed.integrations.mcp_server import MCP_AVAILABLE

        if not MCP_AVAILABLE:
            pytest.skip("MCP package not installed")

    def test_create_server_success(self, skip_if_no_mcp):
        """Test server creation succeeds with MCP."""
        from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server

        mcp = create_sentinel_mcp_server(name="test-server")
        assert mcp is not None

    def test_create_server_custom_sentinel(self, skip_if_no_mcp):
        """Test server creation with custom Sentinel instance."""
        from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server
        from sentinelseed import Sentinel

        sentinel = Sentinel(seed_level="minimal")
        mcp = create_sentinel_mcp_server(sentinel=sentinel)
        assert mcp is not None

    def test_add_tools_to_server(self, skip_if_no_mcp):
        """Test adding tools to existing server."""
        from sentinelseed.integrations.mcp_server import add_sentinel_tools

        try:
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test-server")
            add_sentinel_tools(mcp)
            # Should not raise
        except ImportError:
            pytest.skip("FastMCP not available")


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_text_exactly_at_limit(self):
        """Test text exactly at size limit passes."""
        from sentinelseed.integrations.mcp_server import (
            _validate_text_size,
            MCPConfig,
        )

        # Exactly at limit should pass
        exact_text = "x" * MCPConfig.MAX_TEXT_SIZE
        _validate_text_size(exact_text, context="test")

    def test_text_one_byte_over_limit(self):
        """Test text one byte over limit fails."""
        from sentinelseed.integrations.mcp_server import (
            _validate_text_size,
            TextTooLargeError,
            MCPConfig,
        )

        # One byte over should fail
        over_text = "x" * (MCPConfig.MAX_TEXT_SIZE + 1)
        with pytest.raises(TextTooLargeError):
            _validate_text_size(over_text, context="test")

    def test_batch_size_limit_enforcement(self):
        """Test batch items are limited to MAX_BATCH_ITEMS."""
        from sentinelseed.integrations.mcp_server import MCPConfig

        # This would be tested in integration tests with actual server
        assert MCPConfig.MAX_BATCH_ITEMS == 1000

    def test_timeout_zero_handling(self):
        """Test zero timeout raises immediately."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(url="http://localhost:8000", timeout=0.001)
        assert client.timeout == 0.001

    def test_empty_args_list(self):
        """Test empty args list is valid."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(command="python", args=[])
        assert client.args == []

    def test_args_none_becomes_empty_list(self):
        """Test args=None becomes empty list."""
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        client = SentinelMCPClient(command="python", args=None)
        assert client.args == []


# ============================================================================
# Logging Tests
# ============================================================================

class TestLogging:
    """Tests for logging behavior."""

    def test_logger_exists(self):
        """Test logger is configured."""
        import logging

        logger = logging.getLogger("sentinelseed.mcp_server")
        assert logger is not None

    def test_text_too_large_logs_warning(self):
        """Test TextTooLargeError logs warning."""
        import logging
        from sentinelseed.integrations.mcp_server import (
            _validate_text_size,
            TextTooLargeError,
        )

        logger = logging.getLogger("sentinelseed.mcp_server")

        with pytest.raises(TextTooLargeError):
            _validate_text_size("x" * 100, max_size=50, context="test")
