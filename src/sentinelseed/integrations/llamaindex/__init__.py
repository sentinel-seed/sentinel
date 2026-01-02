"""
LlamaIndex integration for Sentinel AI.

Provides callback handlers and LLM wrappers for adding Sentinel safety
to LlamaIndex applications.

This follows the official LlamaIndex documentation:
https://developers.llamaindex.ai/

Usage:
    from llama_index.core import Settings
    from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

    # Option 1: Global callback handler
    from llama_index.core.callbacks import CallbackManager

    sentinel_handler = SentinelCallbackHandler()
    Settings.callback_manager = CallbackManager([sentinel_handler])

    # Option 2: Wrap existing LLM
    from sentinelseed.integrations.llamaindex import wrap_llm

    Settings.llm = wrap_llm(OpenAI(model="gpt-4o"))

    # Option 3: Use SentinelLLM directly
    from sentinelseed.integrations.llamaindex import SentinelLLM

    Settings.llm = SentinelLLM(llm=OpenAI(model="gpt-4o"))
"""

from typing import Any, Dict, List, Optional, Union, Sequence
from dataclasses import dataclass, field
import uuid
import logging

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.integrations._base import (
    SentinelIntegration,
    LayeredValidator,
    ValidationConfig,
    ValidationResult,
)

# Semantic validation is available via LayeredValidator with API key
SEMANTIC_AVAILABLE = True  # Always available - LayeredValidator handles it

# Valid values for on_violation parameter
VALID_VIOLATION_MODES = frozenset({"log", "raise", "flag"})

logger = logging.getLogger("sentinelseed.llamaindex")

# Check for LlamaIndex availability
LLAMAINDEX_AVAILABLE = False
try:
    from llama_index.core.callbacks.base import BaseCallbackHandler
    from llama_index.core.callbacks import CBEventType, EventPayload
    from llama_index.core.llms import ChatMessage, MessageRole
    LLAMAINDEX_AVAILABLE = True
except (ImportError, AttributeError):
    BaseCallbackHandler = object
    CBEventType = None
    EventPayload = None
    ChatMessage = None
    MessageRole = None

# B001: Explicit exports
__all__ = [
    # Availability flags
    "LLAMAINDEX_AVAILABLE",
    "SEMANTIC_AVAILABLE",
    # Constants
    "VALID_VIOLATION_MODES",
    # Classes
    "SentinelCallbackHandler",
    "SentinelLLM",
    "SentinelValidationEvent",
    # Functions
    "wrap_llm",
    "setup_sentinel_monitoring",
]


def _validate_on_violation(on_violation: Any) -> str:
    """
    Validate on_violation parameter.

    Args:
        on_violation: Value to validate

    Returns:
        Validated on_violation value (defaults to "log" if None)

    Raises:
        ValueError: If on_violation is not a valid value
    """
    if on_violation is None:
        return "log"
    if not isinstance(on_violation, str) or on_violation not in VALID_VIOLATION_MODES:
        raise ValueError(
            f"Invalid on_violation '{on_violation}'. "
            f"Must be one of: {sorted(VALID_VIOLATION_MODES)}"
        )
    return on_violation


@dataclass
class SentinelValidationEvent:
    """Record of a Sentinel validation event."""
    event_id: str
    event_type: str
    content: str
    is_safe: bool
    violations: List[str] = field(default_factory=list)
    risk_level: str = "low"
    timestamp: Optional[str] = None


# Build base classes dynamically
_CALLBACK_BASES = (BaseCallbackHandler, SentinelIntegration) if LLAMAINDEX_AVAILABLE else (SentinelIntegration,)


class SentinelCallbackHandler(*_CALLBACK_BASES):
    """
    LlamaIndex callback handler for Sentinel safety monitoring.

    Monitors LLM inputs and outputs through the LlamaIndex callback system.
    Validates content through THSP protocol and logs violations.

    Inherits from BaseCallbackHandler (LlamaIndex) and SentinelIntegration
    for standardized validation.

    Event types monitored:
        - LLM: Template and response validation
        - QUERY: Query content validation
        - SYNTHESIZE: Synthesis result validation

    Example:
        from llama_index.core import Settings
        from llama_index.core.callbacks import CallbackManager
        from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

        handler = SentinelCallbackHandler(on_violation="log")
        Settings.callback_manager = CallbackManager([handler])

        # All LlamaIndex operations will now be monitored
        index = VectorStoreIndex.from_documents(documents)
        response = index.as_query_engine().query("Your question")
    """

    _integration_name = "llamaindex"

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        on_violation: str = "log",  # "log", "raise", "flag"
        event_starts_to_ignore: Optional[List[str]] = None,
        event_ends_to_ignore: Optional[List[str]] = None,
        validator: Optional[LayeredValidator] = None,
    ):
        """
        Initialize Sentinel callback handler.

        Args:
            sentinel: Sentinel instance (backwards compat for get_seed())
            seed_level: Seed level to use
            on_violation: Action on violation:
                - "log": Log warning and continue
                - "raise": Raise exception
                - "flag": Record but don't interrupt
            event_starts_to_ignore: Event types to ignore on start
            event_ends_to_ignore: Event types to ignore on end
            validator: Optional LayeredValidator for dependency injection (testing)

        Raises:
            ImportError: If llama-index-core is not installed
            ValueError: If on_violation is not a valid value
        """
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError(
                "llama-index-core not installed. "
                "Install with: pip install llama-index-core"
            )

        # BUG-002: Validate on_violation parameter
        on_violation = _validate_on_violation(on_violation)

        # Create LayeredValidator if not provided
        if validator is None:
            config = ValidationConfig(
                use_heuristic=True,
                use_semantic=False,
            )
            validator = LayeredValidator(config=config)

        # Initialize both parent classes explicitly
        if LLAMAINDEX_AVAILABLE and BaseCallbackHandler is not object:
            BaseCallbackHandler.__init__(
                self,
                event_starts_to_ignore=event_starts_to_ignore or [],
                event_ends_to_ignore=event_ends_to_ignore or [],
            )
        SentinelIntegration.__init__(self, validator=validator)

        # Keep sentinel for backwards compat (get_seed())
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.on_violation = on_violation
        self.validation_log: List[SentinelValidationEvent] = []
        self._active_events: Dict[str, Dict[str, Any]] = {}

    def on_event_start(
        self,
        event_type: "CBEventType",
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """Handle event start."""
        event_id = event_id or str(uuid.uuid4())

        # Store event context
        self._active_events[event_id] = {
            "type": event_type,
            "payload": payload,
            "parent_id": parent_id,
        }

        # Validate input for LLM events
        if event_type == CBEventType.LLM and payload:
            messages = payload.get(EventPayload.MESSAGES)
            if messages:
                self._validate_messages(messages, event_id, "input")

            # Also check serialized prompt
            serialized = payload.get(EventPayload.SERIALIZED)
            if serialized and isinstance(serialized, dict):
                prompt = serialized.get("prompt")
                if prompt:
                    self._validate_content(prompt, event_id, "prompt")

        # Validate query events
        elif event_type == CBEventType.QUERY and payload:
            query_str = payload.get(EventPayload.QUERY_STR)
            if query_str:
                self._validate_content(query_str, event_id, "query")

        return event_id

    def on_event_end(
        self,
        event_type: "CBEventType",
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Handle event end."""
        # Clean up active event
        self._active_events.pop(event_id, None)

        # Validate output for LLM events
        if event_type == CBEventType.LLM and payload:
            response = payload.get(EventPayload.RESPONSE)
            if response:
                if hasattr(response, "text"):
                    self._validate_content(response.text, event_id, "response")
                elif hasattr(response, "message"):
                    content = response.message.content if hasattr(response.message, "content") else str(response.message)
                    self._validate_content(content, event_id, "response")

            # Check completion text
            completion = payload.get(EventPayload.COMPLETION)
            if completion:
                self._validate_content(str(completion), event_id, "completion")

        # Validate synthesis results
        elif event_type == CBEventType.SYNTHESIZE and payload:
            response = payload.get(EventPayload.RESPONSE)
            if response:
                if hasattr(response, "response"):
                    self._validate_content(response.response, event_id, "synthesis")

    def _validate_messages(
        self,
        messages: Sequence[Any],
        event_id: str,
        stage: str,
    ) -> None:
        """Validate a sequence of messages."""
        for msg in messages:
            content = ""
            if hasattr(msg, "content"):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = str(msg)

            if content:
                self._validate_content(content, event_id, stage)

    def _validate_content(
        self,
        content: str,
        event_id: str,
        stage: str,
    ) -> None:
        """Validate content through Sentinel."""
        if not content or not content.strip():
            return

        # Validate through THSP
        is_safe, violations = self.sentinel.validate(content)

        # For input/query, also check request validation
        if stage in ("input", "query", "prompt"):
            request_check = self.sentinel.validate_request(content)
            if not request_check["should_proceed"]:
                violations.extend(request_check["concerns"])
                is_safe = False

        # Record validation event
        event = SentinelValidationEvent(
            event_id=event_id,
            event_type=stage,
            content=content[:200] + "..." if len(content) > 200 else content,
            is_safe=is_safe,
            violations=violations,
            risk_level="high" if violations else "low",
        )
        self.validation_log.append(event)

        # Handle violation
        if not is_safe:
            self._handle_violation(event)

    def _handle_violation(self, event: SentinelValidationEvent) -> None:
        """Handle a detected violation."""
        if self.on_violation == "log":
            print(f"[SENTINEL] Violation in {event.event_type}: {event.violations}")
        elif self.on_violation == "raise":
            raise ValueError(
                f"Sentinel safety violation in {event.event_type}: {event.violations}"
            )
        # "flag" mode just records without action

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Start a new trace."""
        pass

    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """End current trace."""
        pass

    def get_violations(self) -> List[SentinelValidationEvent]:
        """Get all validation violations."""
        return [e for e in self.validation_log if not e.is_safe]

    def get_validation_log(self) -> List[SentinelValidationEvent]:
        """Get full validation log."""
        return self.validation_log

    def clear_log(self) -> None:
        """Clear validation log."""
        self.validation_log = []

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = len(self.validation_log)
        violations = len(self.get_violations())

        return {
            "total_validations": total,
            "violations": violations,
            "safe": total - violations,
            "violation_rate": violations / total if total > 0 else 0,
        }


class SentinelLLM(SentinelIntegration):
    """
    Wrapper for LlamaIndex LLMs with Sentinel safety.

    Wraps any LlamaIndex-compatible LLM to inject Sentinel seed
    and validate inputs/outputs.

    Inherits from SentinelIntegration for standardized validation interface.

    Example:
        from llama_index.llms.openai import OpenAI
        from llama_index.core import Settings
        from sentinelseed.integrations.llamaindex import SentinelLLM

        base_llm = OpenAI(model="gpt-4o")
        Settings.llm = SentinelLLM(llm=base_llm)

        # All LLM calls now have Sentinel protection
    """

    _integration_name = "llamaindex_llm"

    def __init__(
        self,
        llm: Any,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        inject_seed: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        validator: Optional[LayeredValidator] = None,
    ):
        """
        Initialize Sentinel LLM wrapper.

        Args:
            llm: LlamaIndex LLM instance to wrap
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level to use
            inject_seed: Whether to inject seed into prompts
            validate_input: Whether to validate input
            validate_output: Whether to validate output
            validator: Optional LayeredValidator for dependency injection (testing)
        """
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("llama-index-core not installed")

        # Create LayeredValidator if not provided
        if validator is None:
            config = ValidationConfig(
                use_heuristic=True,
                use_semantic=False,
            )
            validator = LayeredValidator(config=config)

        # Initialize SentinelIntegration
        super().__init__(validator=validator)

        self._llm = llm
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._inject_seed = inject_seed
        # C001: Use _should_* prefix to avoid collision with _validate_output method
        self._should_validate_input = validate_input
        self._should_validate_output = validate_output
        self._seed = self._sentinel.get_seed()

        # Copy metadata from wrapped LLM
        for attr in ['metadata', 'model', 'temperature', 'max_tokens']:
            if hasattr(llm, attr):
                setattr(self, attr, getattr(llm, attr))

    def _inject_seed_messages(
        self,
        messages: List[Any],
    ) -> List[Any]:
        """Inject seed into messages."""
        if not messages:
            return messages

        messages = list(messages)

        # Check for existing system message
        has_system = False
        for i, msg in enumerate(messages):
            role = getattr(msg, 'role', None) or (msg.get('role') if isinstance(msg, dict) else None)
            if role == MessageRole.SYSTEM or role == "system":
                content = getattr(msg, 'content', None) or msg.get('content', '')
                messages[i] = ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=f"{self._seed}\n\n---\n\n{content}"
                )
                has_system = True
                break

        if not has_system:
            messages.insert(0, ChatMessage(
                role=MessageRole.SYSTEM,
                content=self._seed
            ))

        return messages

    def _validate_messages_input(self, messages: List[Any]) -> None:
        """Validate input messages using inherited LayeredValidator."""
        for msg in messages:
            content = getattr(msg, 'content', None) or (msg.get('content') if isinstance(msg, dict) else str(msg))
            if content:
                result = self.validator.validate(content)
                if not result.is_safe:
                    raise ValueError(f"Input blocked by Sentinel: {result.violations}")

    def _validate_output(self, response: Any) -> None:
        """Validate output response using inherited LayeredValidator."""
        content = ""
        if hasattr(response, 'message'):
            content = getattr(response.message, 'content', str(response.message))
        elif hasattr(response, 'text'):
            content = response.text
        else:
            content = str(response)

        if content:
            result = self.validator.validate(content)
            if not result.is_safe:
                print(f"[SENTINEL] Output validation concerns: {result.violations}")

    def chat(
        self,
        messages: List[Any],
        **kwargs: Any,
    ) -> Any:
        """Chat with Sentinel safety."""
        if self._should_validate_input:
            self._validate_messages_input(messages)

        if self._inject_seed:
            messages = self._inject_seed_messages(messages)

        response = self._llm.chat(messages, **kwargs)

        if self._should_validate_output:
            self._validate_output(response)

        return response

    async def achat(
        self,
        messages: List[Any],
        **kwargs: Any,
    ) -> Any:
        """Async chat with Sentinel safety."""
        if self._should_validate_input:
            self._validate_messages_input(messages)

        if self._inject_seed:
            messages = self._inject_seed_messages(messages)

        response = await self._llm.achat(messages, **kwargs)

        if self._should_validate_output:
            self._validate_output(response)

        return response

    def complete(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> Any:
        """Complete with Sentinel safety."""
        if self._should_validate_input:
            result = self.validator.validate(prompt)
            if not result.is_safe:
                raise ValueError(f"Input blocked by Sentinel: {result.violations}")

        # Inject seed into prompt
        if self._inject_seed:
            prompt = f"{self._seed}\n\n---\n\n{prompt}"

        response = self._llm.complete(prompt, **kwargs)

        if self._should_validate_output:
            self._validate_output(response)

        return response

    async def acomplete(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> Any:
        """Async complete with Sentinel safety."""
        if self._should_validate_input:
            result = self.validator.validate(prompt)
            if not result.is_safe:
                raise ValueError(f"Input blocked by Sentinel: {result.violations}")

        if self._inject_seed:
            prompt = f"{self._seed}\n\n---\n\n{prompt}"

        response = await self._llm.acomplete(prompt, **kwargs)

        if self._should_validate_output:
            self._validate_output(response)

        return response

    def stream_chat(
        self,
        messages: List[Any],
        **kwargs: Any,
    ) -> Any:
        """Stream chat with Sentinel safety."""
        if self._should_validate_input:
            self._validate_messages_input(messages)

        if self._inject_seed:
            messages = self._inject_seed_messages(messages)

        return self._llm.stream_chat(messages, **kwargs)

    def stream_complete(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> Any:
        """Stream complete with Sentinel safety."""
        if self._should_validate_input:
            result = self.validator.validate(prompt)
            if not result.is_safe:
                raise ValueError(f"Input blocked by Sentinel: {result.violations}")

        if self._inject_seed:
            prompt = f"{self._seed}\n\n---\n\n{prompt}"

        return self._llm.stream_complete(prompt, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped LLM."""
        return getattr(self._llm, name)


def wrap_llm(
    llm: Any,
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    inject_seed: bool = True,
) -> SentinelLLM:
    """
    Wrap a LlamaIndex LLM with Sentinel safety.

    Convenience function for wrapping LLMs.

    Args:
        llm: LlamaIndex LLM instance
        sentinel: Sentinel instance
        seed_level: Seed level to use
        inject_seed: Whether to inject seed

    Returns:
        SentinelLLM wrapper

    Example:
        from llama_index.llms.openai import OpenAI
        from llama_index.core import Settings
        from sentinelseed.integrations.llamaindex import wrap_llm

        Settings.llm = wrap_llm(OpenAI(model="gpt-4o"))
    """
    # M002: Guard against double wrapping
    if isinstance(llm, SentinelLLM):
        logger.warning("LLM already wrapped with Sentinel. Returning as-is.")
        return llm

    return SentinelLLM(
        llm=llm,
        sentinel=sentinel,
        seed_level=seed_level,
        inject_seed=inject_seed,
    )


def setup_sentinel_monitoring(
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    on_violation: str = "log",
) -> SentinelCallbackHandler:
    """
    Set up Sentinel monitoring for all LlamaIndex operations.

    Configures global Settings with Sentinel callback handler.

    Args:
        sentinel: Sentinel instance
        seed_level: Seed level to use
        on_violation: Action on violation ("log", "raise", or "flag")

    Returns:
        Configured SentinelCallbackHandler

    Raises:
        ImportError: If llama-index-core is not installed
        ValueError: If on_violation is not a valid value

    Example:
        from sentinelseed.integrations.llamaindex import setup_sentinel_monitoring

        handler = setup_sentinel_monitoring()

        # All LlamaIndex operations are now monitored
        index = VectorStoreIndex.from_documents(documents)
    """
    if not LLAMAINDEX_AVAILABLE:
        raise ImportError("llama-index-core not installed")

    # Validation happens in SentinelCallbackHandler.__init__
    from llama_index.core import Settings
    from llama_index.core.callbacks import CallbackManager

    handler = SentinelCallbackHandler(
        sentinel=sentinel,
        seed_level=seed_level,
        on_violation=on_violation,
    )

    # Add to existing callback manager or create new one
    if Settings.callback_manager:
        Settings.callback_manager.add_handler(handler)
    else:
        Settings.callback_manager = CallbackManager([handler])

    return handler
