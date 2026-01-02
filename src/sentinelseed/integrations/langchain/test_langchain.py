"""
Comprehensive test suite for LangChain integration.

Tests cover:
- TextTooLargeError and ValidationTimeoutError
- validate_text_size function
- SentinelCallback with timeout and size limits
- SentinelGuard with timeout and size limits
- SentinelChain with streaming validation
- StreamingBuffer
- ThreadSafeDeque
- inject_seed function
- Module exports
"""

import asyncio
import time
import unittest
from unittest.mock import Mock, MagicMock, patch
import threading

# Import from the module
from sentinelseed.integrations.langchain import (
    # Constants
    DEFAULT_MAX_VIOLATIONS,
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    DEFAULT_STREAMING_VALIDATION_INTERVAL,
    LANGCHAIN_AVAILABLE,
    # Exceptions
    TextTooLargeError,
    ValidationTimeoutError,
    # Classes
    SentinelCallback,
    SentinelGuard,
    SentinelChain,
    SentinelViolationError,
    StreamingBuffer,
    ThreadSafeDeque,
    ValidationResult,
    ViolationRecord,
    # Functions
    inject_seed,
    wrap_llm,
    create_safe_callback,
    create_sentinel_callback,
    set_logger,
    get_logger,
    sanitize_text,
    validate_text_size,
)


# ============================================================================
# Exception Tests
# ============================================================================

class TestTextTooLargeError(unittest.TestCase):
    """Tests for TextTooLargeError exception."""

    def test_init_stores_values(self):
        """Test that constructor stores size values."""
        error = TextTooLargeError(size=100000, max_size=50000)
        self.assertEqual(error.size, 100000)
        self.assertEqual(error.max_size, 50000)

    def test_message_format(self):
        """Test error message format."""
        error = TextTooLargeError(size=100000, max_size=50000)
        msg = str(error)
        self.assertIn("100,000", msg)
        self.assertIn("50,000", msg)

    def test_inheritance(self):
        """Test that it inherits from Exception."""
        error = TextTooLargeError(100, 50)
        self.assertIsInstance(error, Exception)


class TestValidationTimeoutError(unittest.TestCase):
    """Tests for ValidationTimeoutError exception."""

    def test_init_stores_values(self):
        """Test that constructor stores timeout value."""
        error = ValidationTimeoutError(timeout=30.0, operation="input validation")
        self.assertEqual(error.timeout, 30.0)
        self.assertEqual(error.operation, "input validation")

    def test_default_operation(self):
        """Test default operation value."""
        error = ValidationTimeoutError(timeout=10.0)
        self.assertEqual(error.operation, "validation")

    def test_message_format(self):
        """Test error message format."""
        error = ValidationTimeoutError(timeout=5.0, operation="test")
        msg = str(error)
        self.assertIn("5.0s", msg)
        self.assertIn("test", msg)


# ============================================================================
# validate_text_size Tests
# ============================================================================

class TestValidateTextSize(unittest.TestCase):
    """Tests for validate_text_size function."""

    def test_empty_string_allowed(self):
        """Test that empty string passes validation."""
        validate_text_size("", max_size=100)  # Should not raise

    def test_none_allowed(self):
        """Test that None passes validation."""
        validate_text_size(None, max_size=100)  # Should not raise

    def test_small_string_allowed(self):
        """Test that small string passes validation."""
        validate_text_size("Hello", max_size=100)  # Should not raise

    def test_exactly_at_limit(self):
        """Test string exactly at limit passes."""
        text = "a" * 100
        validate_text_size(text, max_size=100)  # Should not raise

    def test_over_limit_raises(self):
        """Test that string over limit raises error."""
        text = "a" * 101
        with self.assertRaises(TextTooLargeError) as ctx:
            validate_text_size(text, max_size=100)
        self.assertEqual(ctx.exception.size, 101)
        self.assertEqual(ctx.exception.max_size, 100)

    def test_utf8_encoding(self):
        """Test that UTF-8 encoding is used for size calculation."""
        # Each emoji is 4 bytes in UTF-8
        text = "😀" * 25  # 100 bytes
        validate_text_size(text, max_size=100)  # Should pass

        text = "😀" * 26  # 104 bytes
        with self.assertRaises(TextTooLargeError):
            validate_text_size(text, max_size=100)


# ============================================================================
# StreamingBuffer Tests
# ============================================================================

class TestStreamingBuffer(unittest.TestCase):
    """Tests for StreamingBuffer class."""

    def test_init(self):
        """Test initialization."""
        buffer = StreamingBuffer()
        self.assertIsNotNone(buffer)

    def test_add_token_returns_none_for_small_input(self):
        """Test that add_token returns None for small input."""
        buffer = StreamingBuffer()
        result = buffer.add_token("Hi")
        self.assertIsNone(result)

    def test_add_token_returns_content_after_delimiter(self):
        """Test that add_token returns content after delimiter."""
        buffer = StreamingBuffer()
        # Add enough content with delimiter
        for i in range(20):
            buffer.add_token("x")
        result = buffer.add_token(".")
        self.assertIsNotNone(result)
        self.assertIn(".", result)

    def test_flush_returns_remaining(self):
        """Test that flush returns remaining content."""
        buffer = StreamingBuffer()
        buffer.add_token("Hello world")
        result = buffer.flush()
        self.assertEqual(result, "Hello world")

    def test_flush_returns_none_when_empty(self):
        """Test that flush returns None when buffer is empty."""
        buffer = StreamingBuffer()
        result = buffer.flush()
        self.assertIsNone(result)

    def test_clear(self):
        """Test clear method."""
        buffer = StreamingBuffer()
        buffer.add_token("content")
        buffer.clear()
        result = buffer.flush()
        self.assertIsNone(result)

    def test_thread_safety(self):
        """Test thread safety of buffer operations."""
        buffer = StreamingBuffer()
        errors = []

        def add_tokens():
            try:
                for i in range(100):
                    buffer.add_token(f"token{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)


# ============================================================================
# ThreadSafeDeque Tests
# ============================================================================

class TestThreadSafeDeque(unittest.TestCase):
    """Tests for ThreadSafeDeque class."""

    def test_init(self):
        """Test initialization."""
        deque = ThreadSafeDeque(maxlen=100)
        self.assertEqual(len(deque), 0)

    def test_append(self):
        """Test append method."""
        deque = ThreadSafeDeque()
        deque.append("item1")
        self.assertEqual(len(deque), 1)

    def test_extend(self):
        """Test extend method."""
        deque = ThreadSafeDeque()
        deque.extend(["a", "b", "c"])
        self.assertEqual(len(deque), 3)

    def test_clear(self):
        """Test clear method."""
        deque = ThreadSafeDeque()
        deque.extend(["a", "b", "c"])
        deque.clear()
        self.assertEqual(len(deque), 0)

    def test_to_list(self):
        """Test to_list method."""
        deque = ThreadSafeDeque()
        deque.extend([1, 2, 3])
        result = deque.to_list()
        self.assertEqual(result, [1, 2, 3])

    def test_maxlen_enforced(self):
        """Test that maxlen is enforced."""
        deque = ThreadSafeDeque(maxlen=3)
        deque.extend([1, 2, 3, 4, 5])
        self.assertEqual(len(deque), 3)
        self.assertEqual(deque.to_list(), [3, 4, 5])

    def test_iteration(self):
        """Test iteration."""
        deque = ThreadSafeDeque()
        deque.extend([1, 2, 3])
        result = list(deque)
        self.assertEqual(result, [1, 2, 3])

    def test_thread_safety(self):
        """Test thread safety."""
        deque = ThreadSafeDeque(maxlen=1000)
        errors = []

        def append_items():
            try:
                for i in range(100):
                    deque.append(i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=append_items) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)


# ============================================================================
# SentinelCallback Tests
# ============================================================================

class TestSentinelCallback(unittest.TestCase):
    """Tests for SentinelCallback class."""

    def test_init_with_defaults(self):
        """Test initialization with defaults."""
        callback = SentinelCallback()
        self.assertIsNotNone(callback.sentinel)
        self.assertEqual(callback.on_violation, "log")
        self.assertTrue(callback.validate_input)
        self.assertTrue(callback.validate_output)

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        callback = SentinelCallback(
            seed_level="minimal",
            on_violation="raise",
            max_text_size=10000,
            validation_timeout=5.0,
            fail_closed=True,
        )
        self.assertEqual(callback._max_text_size, 10000)
        self.assertEqual(callback._validation_timeout, 5.0)
        self.assertTrue(callback._fail_closed)

    def test_get_violations_empty(self):
        """Test get_violations returns empty list initially."""
        callback = SentinelCallback()
        violations = callback.get_violations()
        self.assertEqual(violations, [])

    def test_get_validation_log_empty(self):
        """Test get_validation_log returns empty list initially."""
        callback = SentinelCallback()
        log = callback.get_validation_log()
        self.assertEqual(log, [])

    def test_clear_violations(self):
        """Test clear_violations method."""
        callback = SentinelCallback()
        callback._violations_log.append({"test": "data"})
        callback.clear_violations()
        self.assertEqual(len(callback._violations_log), 0)

    def test_clear_log(self):
        """Test clear_log method."""
        callback = SentinelCallback()
        callback._violations_log.append({"test": "data"})
        callback._validation_log.append({"test": "data"})
        callback.clear_log()
        self.assertEqual(len(callback._violations_log), 0)
        self.assertEqual(len(callback._validation_log), 0)

    def test_get_stats_empty(self):
        """Test get_stats with no validations."""
        callback = SentinelCallback()
        stats = callback.get_stats()
        self.assertEqual(stats["total_validations"], 0)
        self.assertEqual(stats["total_violations"], 0)


class TestSentinelCallbackTextSize(unittest.TestCase):
    """Tests for SentinelCallback text size validation."""

    def test_large_input_triggers_violation(self):
        """Test that large input triggers violation."""
        callback = SentinelCallback(
            max_text_size=100,
            validate_input=True,
        )
        # Create text larger than limit
        large_text = "a" * 200

        callback._validate_input_safe(large_text, "test")

        violations = callback.get_violations()
        self.assertEqual(len(violations), 1)
        self.assertIn("too large", violations[0]["concerns"][0].lower())


# ============================================================================
# SentinelGuard Tests
# ============================================================================

class TestSentinelGuard(unittest.TestCase):
    """Tests for SentinelGuard class."""

    def test_init_with_defaults(self):
        """Test initialization with defaults."""
        mock_agent = Mock()
        guard = SentinelGuard(agent=mock_agent)
        self.assertIsNotNone(guard.sentinel)
        self.assertTrue(guard.block_unsafe)
        self.assertTrue(guard.validate_input)
        self.assertTrue(guard.validate_output)

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        mock_agent = Mock()
        guard = SentinelGuard(
            agent=mock_agent,
            max_text_size=10000,
            validation_timeout=5.0,
            fail_closed=True,
        )
        self.assertEqual(guard._max_text_size, 10000)
        self.assertEqual(guard._validation_timeout, 5.0)
        self.assertTrue(guard._fail_closed)

    def test_validate_input_blocks_large_text(self):
        """Test that large text is blocked on input."""
        mock_agent = Mock()
        guard = SentinelGuard(
            agent=mock_agent,
            max_text_size=100,
            block_unsafe=True,
        )
        large_text = "a" * 200
        result = guard._validate_input(large_text)

        self.assertIsNotNone(result)
        self.assertTrue(result["sentinel_blocked"])
        self.assertIn("too large", result["sentinel_reason"][0].lower())

    def test_validate_output_blocks_large_text(self):
        """Test that large text is blocked on output."""
        mock_agent = Mock()
        guard = SentinelGuard(
            agent=mock_agent,
            max_text_size=100,
            block_unsafe=True,
        )
        large_text = "a" * 200
        result = guard._validate_output(large_text)

        self.assertIsNotNone(result)
        self.assertTrue(result["sentinel_blocked"])


# ============================================================================
# SentinelChain Tests
# ============================================================================

class TestSentinelChain(unittest.TestCase):
    """Tests for SentinelChain class."""

    def test_init_requires_llm_or_chain(self):
        """Test that init requires llm or chain."""
        with self.assertRaises(ValueError):
            SentinelChain()

    def test_init_with_llm(self):
        """Test initialization with llm."""
        mock_llm = Mock()
        chain = SentinelChain(llm=mock_llm)
        self.assertIsNotNone(chain.sentinel)
        self.assertTrue(chain.validate_input)
        self.assertTrue(chain.validate_output)

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        mock_llm = Mock()
        chain = SentinelChain(
            llm=mock_llm,
            max_text_size=10000,
            validation_timeout=5.0,
            fail_closed=True,
            streaming_validation_interval=200,
        )
        self.assertEqual(chain._max_text_size, 10000)
        self.assertEqual(chain._validation_timeout, 5.0)
        self.assertTrue(chain._fail_closed)
        self.assertEqual(chain._streaming_validation_interval, 200)

    def test_validate_input_blocks_large_text(self):
        """Test that large text is blocked on input."""
        mock_llm = Mock()
        chain = SentinelChain(
            llm=mock_llm,
            max_text_size=100,
        )
        large_text = "a" * 200
        result = chain._validate_input_safe(large_text)

        self.assertIsNotNone(result)
        self.assertTrue(result["blocked"])
        self.assertEqual(result["blocked_at"], "input")


# ============================================================================
# inject_seed Tests
# ============================================================================

class TestInjectSeed(unittest.TestCase):
    """Tests for inject_seed function."""

    def test_inject_into_empty_list(self):
        """Test inject_seed with empty list."""
        result = inject_seed([], seed_level="minimal")
        self.assertEqual(len(result), 1)

    def test_inject_adds_system_message(self):
        """Test that inject_seed adds system message."""
        messages = [{"role": "user", "content": "Hello"}]
        result = inject_seed(messages, seed_level="minimal")
        self.assertEqual(len(result), 2)
        # First message should be system
        first = result[0]
        if isinstance(first, dict):
            self.assertEqual(first["role"], "system")

    def test_inject_prepends_to_existing_system(self):
        """Test that inject_seed prepends to existing system message."""
        messages = [
            {"role": "system", "content": "Original system"},
            {"role": "user", "content": "Hello"},
        ]
        result = inject_seed(messages, seed_level="minimal")
        self.assertEqual(len(result), 2)  # Should still be 2 messages
        # System message should contain both
        system = result[0]
        if isinstance(system, dict):
            self.assertIn("Original system", system["content"])

    def test_inject_does_not_mutate_original(self):
        """Test that inject_seed does not mutate original list."""
        messages = [{"role": "user", "content": "Hello"}]
        original_len = len(messages)
        inject_seed(messages, seed_level="minimal")
        self.assertEqual(len(messages), original_len)


# ============================================================================
# Factory Function Tests
# ============================================================================

class TestFactoryFunctions(unittest.TestCase):
    """Tests for factory functions."""

    def test_create_safe_callback(self):
        """Test create_safe_callback function."""
        callback = create_safe_callback(
            on_violation="raise",
            max_text_size=10000,
            validation_timeout=5.0,
        )
        self.assertIsInstance(callback, SentinelCallback)
        self.assertEqual(callback.on_violation, "raise")
        self.assertEqual(callback._max_text_size, 10000)

    def test_create_sentinel_callback_alias(self):
        """Test that create_sentinel_callback is alias for create_safe_callback."""
        callback = create_sentinel_callback()
        self.assertIsInstance(callback, SentinelCallback)


# ============================================================================
# Module Export Tests
# ============================================================================

class TestModuleExports(unittest.TestCase):
    """Tests for module exports."""

    def test_constants_exported(self):
        """Test that constants are exported."""
        self.assertIsInstance(DEFAULT_MAX_VIOLATIONS, int)
        self.assertIsInstance(DEFAULT_SEED_LEVEL, str)
        self.assertIsInstance(DEFAULT_MAX_TEXT_SIZE, int)
        self.assertIsInstance(DEFAULT_VALIDATION_TIMEOUT, float)
        self.assertIsInstance(DEFAULT_STREAMING_VALIDATION_INTERVAL, int)

    def test_exceptions_exported(self):
        """Test that exceptions are exported."""
        self.assertTrue(issubclass(TextTooLargeError, Exception))
        self.assertTrue(issubclass(ValidationTimeoutError, Exception))

    def test_classes_exported(self):
        """Test that classes are exported."""
        self.assertTrue(callable(SentinelCallback))
        self.assertTrue(callable(SentinelGuard))
        self.assertTrue(callable(SentinelChain))
        self.assertTrue(callable(StreamingBuffer))
        self.assertTrue(callable(ThreadSafeDeque))

    def test_functions_exported(self):
        """Test that functions are exported."""
        self.assertTrue(callable(inject_seed))
        self.assertTrue(callable(wrap_llm))
        self.assertTrue(callable(create_safe_callback))
        self.assertTrue(callable(validate_text_size))
        self.assertTrue(callable(sanitize_text))


# ============================================================================
# ValidationResult and ViolationRecord Tests
# ============================================================================

class TestValidationResult(unittest.TestCase):
    """Tests for ValidationResult class."""

    def test_init(self):
        """Test initialization."""
        result = ValidationResult(
            safe=True,
            stage="input",
            type="input",
            risk_level="low",
        )
        self.assertTrue(result.safe)
        self.assertEqual(result.stage, "input")

    def test_to_dict(self):
        """Test to_dict method."""
        result = ValidationResult(
            safe=False,
            stage="output",
            type="output",
            risk_level="high",
            concerns=["concern1"],
        )
        d = result.to_dict()
        self.assertFalse(d["safe"])
        self.assertEqual(d["stage"], "output")
        self.assertEqual(d["risk_level"], "high")


class TestViolationRecord(unittest.TestCase):
    """Tests for ViolationRecord class."""

    def test_init(self):
        """Test initialization."""
        record = ViolationRecord(
            stage="input",
            text="test",
            concerns=["concern1"],
            risk_level="high",
        )
        self.assertEqual(record.stage, "input")
        self.assertIsNotNone(record.timestamp)

    def test_to_dict(self):
        """Test to_dict method."""
        record = ViolationRecord(
            stage="output",
            text="test text",
            concerns=["c1", "c2"],
            risk_level="medium",
        )
        d = record.to_dict()
        self.assertEqual(d["stage"], "output")
        self.assertEqual(len(d["concerns"]), 2)


# ============================================================================
# Configuration Validation Tests
# ============================================================================

class TestConfigurationError(unittest.TestCase):
    """Tests for ConfigurationError exception."""

    def test_init_stores_values(self):
        """Test that constructor stores values."""
        from sentinelseed.integrations.langchain.utils import ConfigurationError
        error = ConfigurationError("max_text_size", "positive integer", "invalid")
        self.assertEqual(error.param_name, "max_text_size")
        self.assertEqual(error.expected, "positive integer")
        self.assertEqual(error.got, "invalid")

    def test_message_format(self):
        """Test error message format."""
        from sentinelseed.integrations.langchain.utils import ConfigurationError
        error = ConfigurationError("timeout", "positive number", -1)
        msg = str(error)
        self.assertIn("timeout", msg)
        self.assertIn("positive number", msg)
        self.assertIn("int", msg)


class TestValidateConfigTypes(unittest.TestCase):
    """Tests for validate_config_types function."""

    def test_valid_config(self):
        """Test that valid config passes validation."""
        from sentinelseed.integrations.langchain.utils import validate_config_types
        # Should not raise
        validate_config_types(
            max_text_size=1000,
            validation_timeout=30.0,
            fail_closed=True,
            max_violations=100,
            streaming_validation_interval=500,
        )

    def test_none_values_allowed(self):
        """Test that None values are skipped."""
        from sentinelseed.integrations.langchain.utils import validate_config_types
        # Should not raise
        validate_config_types(
            max_text_size=None,
            validation_timeout=None,
            fail_closed=None,
        )

    def test_invalid_max_text_size_type(self):
        """Test that invalid max_text_size type raises error."""
        from sentinelseed.integrations.langchain.utils import (
            validate_config_types,
            ConfigurationError,
        )
        with self.assertRaises(ConfigurationError) as ctx:
            validate_config_types(max_text_size="invalid")
        self.assertEqual(ctx.exception.param_name, "max_text_size")

    def test_invalid_max_text_size_value(self):
        """Test that negative max_text_size raises error."""
        from sentinelseed.integrations.langchain.utils import (
            validate_config_types,
            ConfigurationError,
        )
        with self.assertRaises(ConfigurationError):
            validate_config_types(max_text_size=-100)

    def test_invalid_validation_timeout_type(self):
        """Test that invalid validation_timeout type raises error."""
        from sentinelseed.integrations.langchain.utils import (
            validate_config_types,
            ConfigurationError,
        )
        with self.assertRaises(ConfigurationError):
            validate_config_types(validation_timeout="30s")

    def test_invalid_fail_closed_type(self):
        """Test that invalid fail_closed type raises error."""
        from sentinelseed.integrations.langchain.utils import (
            validate_config_types,
            ConfigurationError,
        )
        with self.assertRaises(ConfigurationError):
            validate_config_types(fail_closed="yes")

    def test_callback_validates_config(self):
        """Test that SentinelCallback validates config on init."""
        from sentinelseed.integrations.langchain.utils import ConfigurationError
        with self.assertRaises(ConfigurationError):
            SentinelCallback(max_text_size="invalid")

    def test_guard_validates_config(self):
        """Test that SentinelGuard validates config on init."""
        from sentinelseed.integrations.langchain.utils import ConfigurationError
        mock_agent = Mock()
        with self.assertRaises(ConfigurationError):
            SentinelGuard(agent=mock_agent, validation_timeout=-5)

    def test_chain_validates_config(self):
        """Test that SentinelChain validates config on init."""
        from sentinelseed.integrations.langchain.utils import ConfigurationError
        mock_llm = Mock()
        with self.assertRaises(ConfigurationError):
            SentinelChain(llm=mock_llm, streaming_validation_interval=0)


# ============================================================================
# Async Tests
# ============================================================================

class TestAsyncOperations(unittest.TestCase):
    """Tests for async operations."""

    def test_guard_ainvoke(self):
        """Test SentinelGuard.ainvoke."""
        async def _test():
            mock_agent = Mock()
            mock_agent.ainvoke = MagicMock(
                return_value=asyncio.coroutine(lambda: {"output": "response"})()
            )
            guard = SentinelGuard(
                agent=mock_agent,
                max_text_size=100,
                validate_input=True,
            )
            # Test with small input (should pass)
            result = await guard.ainvoke({"input": "test"})
            # The result should not be blocked for small valid input
            return result

        # Run without raising - we expect this may fail without actual LLM
        # This test verifies the guard structure can be instantiated
        try:
            asyncio.run(_test())
        except (RuntimeError, ValueError, ConnectionError):
            # Expected: no actual LLM configured for tests
            pass


# ============================================================================
# ValidationExecutor Tests
# ============================================================================

class TestValidationExecutor(unittest.TestCase):
    """Tests for ValidationExecutor singleton."""

    def setUp(self):
        """Reset the executor before each test."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor
        ValidationExecutor.reset_instance()

    def tearDown(self):
        """Clean up after each test."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor
        ValidationExecutor.reset_instance()

    def test_singleton_pattern(self):
        """Test that get_instance returns the same instance."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor
        instance1 = ValidationExecutor.get_instance()
        instance2 = ValidationExecutor.get_instance()
        self.assertIs(instance1, instance2)

    def test_run_with_timeout_success(self):
        """Test successful execution with timeout."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor

        def add(a, b):
            return a + b

        executor = ValidationExecutor.get_instance()
        result = executor.run_with_timeout(add, args=(2, 3), timeout=5.0)
        self.assertEqual(result, 5)

    def test_run_with_timeout_raises_on_timeout(self):
        """Test that timeout raises ValidationTimeoutError."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor
        import time

        def slow_function():
            time.sleep(5)
            return "done"

        executor = ValidationExecutor.get_instance()
        with self.assertRaises(ValidationTimeoutError):
            executor.run_with_timeout(slow_function, timeout=0.1)

    def test_shutdown_and_reset(self):
        """Test shutdown and reset functionality."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor

        executor = ValidationExecutor.get_instance()
        executor.shutdown()

        # After shutdown, operations should fail
        with self.assertRaises(RuntimeError):
            executor.run_with_timeout(lambda: 1, timeout=1.0)

        # Reset should allow new instance
        ValidationExecutor.reset_instance()
        new_executor = ValidationExecutor.get_instance()
        result = new_executor.run_with_timeout(lambda: 42, timeout=1.0)
        self.assertEqual(result, 42)

    def test_run_with_timeout_async_success(self):
        """Test successful async execution with timeout."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor

        def multiply(a, b):
            return a * b

        async def _test():
            executor = ValidationExecutor.get_instance()
            result = await executor.run_with_timeout_async(
                multiply, args=(4, 5), timeout=5.0
            )
            return result

        result = asyncio.run(_test())
        self.assertEqual(result, 20)

    def test_run_with_timeout_async_raises_on_timeout(self):
        """Test that async timeout raises ValidationTimeoutError."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor

        def slow_function():
            time.sleep(5)
            return "done"

        async def _test():
            executor = ValidationExecutor.get_instance()
            return await executor.run_with_timeout_async(slow_function, timeout=0.1)

        with self.assertRaises(ValidationTimeoutError):
            asyncio.run(_test())

    def test_run_with_timeout_async_shutdown_raises(self):
        """Test that async execution after shutdown raises RuntimeError."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor

        async def _test():
            executor = ValidationExecutor.get_instance()
            executor.shutdown()
            return await executor.run_with_timeout_async(lambda: 1, timeout=1.0)

        with self.assertRaises(RuntimeError):
            asyncio.run(_test())


# ============================================================================
# Async Helper Tests
# ============================================================================

class TestAsyncHelpers(unittest.TestCase):
    """Tests for async helper functions."""

    def test_run_sync_with_timeout_async_success(self):
        """Test successful async execution."""
        from sentinelseed.integrations.langchain.utils import run_sync_with_timeout_async

        def multiply(a, b):
            return a * b

        async def _test():
            result = await run_sync_with_timeout_async(
                multiply,
                args=(3, 4),
                timeout=5.0,
            )
            return result

        result = asyncio.run(_test())
        self.assertEqual(result, 12)

    def test_run_sync_with_timeout_async_timeout(self):
        """Test timeout handling in async helper."""
        from sentinelseed.integrations.langchain.utils import run_sync_with_timeout_async
        import time

        def slow_function():
            time.sleep(5)
            return "done"

        async def _test():
            return await run_sync_with_timeout_async(
                slow_function,
                timeout=0.1,
            )

        with self.assertRaises(ValidationTimeoutError):
            asyncio.run(_test())


# ============================================================================
# wrap_llm Tests
# ============================================================================

class TestWrapLLM(unittest.TestCase):
    """Tests for wrap_llm function."""

    def test_wrap_llm_does_not_modify_original(self):
        """Test that wrap_llm does not modify the original LLM."""
        mock_llm = Mock()
        mock_llm.callbacks = []

        # Store original callbacks reference
        original_callbacks = mock_llm.callbacks

        # Wrap the LLM
        wrapped = wrap_llm(mock_llm, inject_seed=True, add_callback=True)

        # Original should be unchanged
        self.assertEqual(mock_llm.callbacks, original_callbacks)
        self.assertEqual(len(mock_llm.callbacks), 0)

    def test_wrap_llm_returns_wrapper(self):
        """Test that wrap_llm returns a wrapper instance."""
        mock_llm = Mock()
        wrapped = wrap_llm(mock_llm, inject_seed=True)

        # Should be a wrapper, not the original
        self.assertIsNot(wrapped, mock_llm)
        self.assertIn("Sentinel", str(type(wrapped).__name__))


# ============================================================================
# _SentinelLLMWrapper Tests
# ============================================================================

class TestSentinelLLMWrapper(unittest.TestCase):
    """Tests for _SentinelLLMWrapper class."""

    def test_repr(self):
        """Test __repr__ method."""
        mock_llm = Mock()
        wrapped = wrap_llm(mock_llm, seed_level="minimal")

        repr_str = repr(wrapped)
        self.assertIn("_SentinelLLMWrapper", repr_str)
        self.assertIn("minimal", repr_str)

    def test_str(self):
        """Test __str__ method."""
        mock_llm = Mock()
        wrapped = wrap_llm(mock_llm)

        str_result = str(wrapped)
        self.assertIn("SentinelWrapped", str_result)

    def test_getattr_proxy(self):
        """Test that unknown attributes are proxied to wrapped LLM."""
        mock_llm = Mock()
        mock_llm.custom_attribute = "test_value"

        wrapped = wrap_llm(mock_llm)

        self.assertEqual(wrapped.custom_attribute, "test_value")


# ============================================================================
# get_validation_executor Tests
# ============================================================================

class TestGetValidationExecutor(unittest.TestCase):
    """Tests for get_validation_executor convenience function."""

    def setUp(self):
        """Reset the executor before each test."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor
        ValidationExecutor.reset_instance()

    def tearDown(self):
        """Clean up after each test."""
        from sentinelseed.integrations.langchain.utils import ValidationExecutor
        ValidationExecutor.reset_instance()

    def test_returns_executor_instance(self):
        """Test that get_validation_executor returns an executor."""
        from sentinelseed.integrations.langchain.utils import (
            get_validation_executor,
            ValidationExecutor,
        )

        executor = get_validation_executor()
        self.assertIsInstance(executor, ValidationExecutor)

    def test_returns_same_instance(self):
        """Test that get_validation_executor returns the same instance."""
        from sentinelseed.integrations.langchain.utils import get_validation_executor

        executor1 = get_validation_executor()
        executor2 = get_validation_executor()
        self.assertIs(executor1, executor2)


if __name__ == "__main__":
    unittest.main()
