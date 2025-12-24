"""
OpenAI Assistants API integration for Sentinel AI.

Provides wrappers for the OpenAI Assistants API that inject Sentinel
safety instructions and validate conversations.

This follows the official OpenAI Assistants API specification:
https://platform.openai.com/docs/assistants

Usage:
    from sentinelseed.integrations.openai_assistant import SentinelAssistant

    # Option 1: Create a new Sentinel-protected assistant
    assistant = SentinelAssistant.create(
        name="My Safe Assistant",
        instructions="You are a helpful coding assistant",
        model="gpt-4o"
    )

    # Option 2: Wrap existing assistant
    from sentinelseed.integrations.openai_assistant import wrap_assistant

    safe_assistant = wrap_assistant(existing_assistant)

    # Option 3: Use SentinelAssistantClient for full control
    from sentinelseed.integrations.openai_assistant import SentinelAssistantClient

    client = SentinelAssistantClient()
    assistant = client.create_assistant(name="Helper", instructions="...")
    thread = client.create_thread()
    response = client.run_conversation(assistant.id, thread.id, "Hello!")
"""

from typing import Any, Dict, List, Optional, Union, Iterator, Tuple
import asyncio
import os
import logging
import time

from sentinelseed import Sentinel, SeedLevel
# B002: Removed unused imports (reserved for future semantic validation)
# from sentinelseed.validators.semantic import SemanticValidator, AsyncSemanticValidator, THSPResult

# B001: Explicit exports
__all__ = [
    # Classes principais
    "SentinelAssistant",
    "SentinelAssistantClient",
    "SentinelAsyncAssistantClient",
    # Funcoes utilitarias
    "wrap_assistant",
    "inject_seed_instructions",
    # Exceptions
    "AssistantRunError",
    "AssistantRequiresActionError",
    "ValidationError",
    "OutputBlockedError",
    # Constantes
    "OPENAI_AVAILABLE",
    "VALID_SEED_LEVELS",
    "DEFAULT_POLL_INTERVAL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_VALIDATION_TIMEOUT",
]

logger = logging.getLogger("sentinelseed.openai_assistant")

# Valid seed levels
VALID_SEED_LEVELS = ("minimal", "standard", "full")

# Default configuration values
DEFAULT_POLL_INTERVAL = 1.0
DEFAULT_TIMEOUT = 300.0
# Note: Validation timeout is reserved for future use with semantic validation.
# Current THS validation is pattern-based (local, fast) and doesn't need timeout.
DEFAULT_VALIDATION_TIMEOUT = 30.0


class AssistantRunError(Exception):
    """Raised when an assistant run fails or is cancelled."""

    def __init__(self, run_id: str, status: str, message: str = ""):
        self.run_id = run_id
        self.status = status
        super().__init__(f"Run {run_id} {status}: {message}" if message else f"Run {run_id} {status}")


class AssistantRequiresActionError(Exception):
    """Raised when a run requires action (function calling) but no handler is provided."""

    def __init__(self, run_id: str, required_action: Any = None):
        self.run_id = run_id
        self.required_action = required_action
        super().__init__(
            f"Run {run_id} requires action. Use a function calling handler or "
            "pass handle_requires_action=True to wait for manual resolution."
        )


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, concerns: Optional[List[str]] = None):
        self.concerns = concerns or []
        super().__init__(message)


class OutputBlockedError(Exception):
    """Raised when output validation fails and blocking is enabled."""

    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__(f"Output blocked due to safety violations: {violations}")


def _validate_seed_level(seed_level: str) -> str:
    """Validate and normalize seed level."""
    normalized = seed_level.lower()
    if normalized not in VALID_SEED_LEVELS:
        raise ValueError(
            f"Invalid seed_level '{seed_level}'. "
            f"Must be one of: {', '.join(VALID_SEED_LEVELS)}"
        )
    return normalized


def _safe_validate_request(
    sentinel: Sentinel,
    content: str,
    logger_instance: logging.Logger,
) -> Dict[str, Any]:
    """
    Safely validate a request with error handling.

    Returns:
        Dict with 'should_proceed', 'concerns', 'risk_level'
    """
    # Skip empty/None content
    if not content or not content.strip():
        return {"should_proceed": True, "concerns": [], "risk_level": "low"}

    try:
        result = sentinel.validate_request(content)
        return result
    except Exception as e:
        logger_instance.error(f"Validation error: {type(e).__name__}: {str(e)[:100]}")
        # Fail-safe: block on validation error
        return {
            "should_proceed": False,
            "concerns": [f"Validation error: {type(e).__name__}"],
            "risk_level": "high",
        }


def _safe_validate_output(
    sentinel: Sentinel,
    content: str,
    logger_instance: logging.Logger,
) -> Tuple[bool, List[str]]:
    """
    Safely validate output with error handling.

    Returns:
        Tuple of (is_safe, violations)
    """
    # Skip empty/None content
    if not content or not content.strip():
        return True, []

    try:
        is_safe, violations = sentinel.validate(content)
        return is_safe, violations
    except Exception as e:
        logger_instance.error(f"Output validation error: {type(e).__name__}: {str(e)[:100]}")
        # Fail-safe: treat as unsafe on validation error
        return False, [f"Validation error: {type(e).__name__}"]


def _extract_response_text(messages: List[Any], logger_instance: logging.Logger) -> str:
    """
    Safely extract response text from assistant messages.

    Args:
        messages: List of message objects
        logger_instance: Logger for error reporting

    Returns:
        Extracted text or empty string
    """
    try:
        for msg in messages:
            if not hasattr(msg, "role") or msg.role != "assistant":
                continue

            if not hasattr(msg, "content"):
                continue

            for block in msg.content:
                if hasattr(block, "text") and hasattr(block.text, "value"):
                    return block.text.value

        return ""
    except Exception as e:
        logger_instance.warning(f"Error extracting response: {type(e).__name__}: {str(e)[:50]}")
        return ""

# Check for OpenAI SDK availability
OPENAI_AVAILABLE = False
try:
    from openai import OpenAI, AsyncOpenAI
    from openai.types.beta import Assistant, Thread
    from openai.types.beta.threads import Run, Message
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    AsyncOpenAI = None
    Assistant = None
    Thread = None
    Run = None
    Message = None


class SentinelAssistant:
    """
    Sentinel-protected OpenAI Assistant.

    Creates assistants with Sentinel safety instructions prepended
    to the assistant's instructions.

    Example:
        from sentinelseed.integrations.openai_assistant import SentinelAssistant

        assistant = SentinelAssistant.create(
            name="Code Helper",
            instructions="You help users write Python code",
            model="gpt-4o",
            tools=[{"type": "code_interpreter"}]
        )

        # Use the assistant normally
        print(f"Created assistant: {assistant.id}")
    """

    def __init__(
        self,
        assistant: Any,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
    ):
        """
        Initialize wrapper around existing assistant.

        Args:
            assistant: OpenAI Assistant object
            sentinel: Sentinel instance
            seed_level: Seed level used ("minimal", "standard", "full")

        Raises:
            ValueError: If seed_level is invalid
        """
        # Validate seed_level
        self._seed_level = _validate_seed_level(seed_level)

        self._assistant = assistant
        self._sentinel = sentinel or Sentinel(seed_level=self._seed_level)

        # Copy key attributes
        self.id = assistant.id
        self.name = assistant.name
        self.model = assistant.model
        self.instructions = assistant.instructions

    @classmethod
    def create(
        cls,
        name: str,
        instructions: Optional[str] = None,
        model: str = "gpt-4o",
        tools: Optional[List[Dict[str, Any]]] = None,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        api_key: Optional[str] = None,
        **kwargs,
    ) -> "SentinelAssistant":
        """
        Create a new Sentinel-protected assistant.

        Args:
            name: Assistant name
            instructions: Base instructions (seed will be prepended)
            model: Model to use
            tools: List of tools (code_interpreter, file_search, function)
            sentinel: Sentinel instance
            seed_level: Seed level to use ("minimal", "standard", "full")
            api_key: OpenAI API key
            **kwargs: Additional assistant parameters

        Returns:
            SentinelAssistant instance

        Raises:
            ImportError: If openai package is not installed
            ValueError: If seed_level is invalid

        Example:
            assistant = SentinelAssistant.create(
                name="Research Helper",
                instructions="You help users research topics",
                model="gpt-4o",
                tools=[{"type": "file_search"}]
            )
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        # Validate seed_level
        validated_level = _validate_seed_level(seed_level)
        sentinel = sentinel or Sentinel(seed_level=validated_level)
        seed = sentinel.get_seed()

        # Prepend seed to instructions
        if instructions:
            full_instructions = f"{seed}\n\n---\n\n{instructions}"
        else:
            full_instructions = seed

        # Create OpenAI client
        client = OpenAI(api_key=api_key)

        # Create assistant
        assistant = client.beta.assistants.create(
            name=name,
            instructions=full_instructions,
            model=model,
            tools=tools or [],
            **kwargs,
        )

        return cls(assistant, sentinel, validated_level)

    def update(
        self,
        instructions: Optional[str] = None,
        name: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> "SentinelAssistant":
        """
        Update assistant with new parameters.

        Seed is re-injected into instructions if provided.

        Args:
            instructions: New base instructions
            name: New name
            tools: New tools
            api_key: OpenAI API key
            **kwargs: Additional parameters

        Returns:
            Updated SentinelAssistant
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")

        client = OpenAI(api_key=api_key)
        seed = self._sentinel.get_seed()

        update_params = {}

        if instructions is not None:
            update_params["instructions"] = f"{seed}\n\n---\n\n{instructions}"

        if name is not None:
            update_params["name"] = name

        if tools is not None:
            update_params["tools"] = tools

        update_params.update(kwargs)

        updated = client.beta.assistants.update(
            self.id,
            **update_params,
        )

        return SentinelAssistant(updated, self._sentinel, self._seed_level)

    def delete(self, api_key: Optional[str] = None) -> bool:
        """Delete this assistant."""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")

        client = OpenAI(api_key=api_key)
        result = client.beta.assistants.delete(self.id)
        return result.deleted

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped assistant."""
        return getattr(self._assistant, name)


class SentinelAssistantClient:
    """
    Full-featured client for OpenAI Assistants with Sentinel safety.

    Provides methods for creating assistants, managing threads,
    running conversations, and validating all inputs/outputs.

    Example:
        from sentinelseed.integrations.openai_assistant import SentinelAssistantClient

        client = SentinelAssistantClient()

        # Create assistant
        assistant = client.create_assistant(
            name="Helper",
            instructions="You are helpful"
        )

        # Create thread and run conversation
        thread = client.create_thread()
        response = client.run_conversation(
            assistant_id=assistant.id,
            thread_id=thread.id,
            message="Help me with Python"
        )

        print(response)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        validate_input: bool = True,
        validate_output: bool = True,
        block_unsafe_output: bool = False,
    ):
        """
        Initialize Sentinel Assistant client.

        Args:
            api_key: OpenAI API key
            sentinel: Sentinel instance
            seed_level: Seed level to use ("minimal", "standard", "full")
            validate_input: Whether to validate user messages
            validate_output: Whether to validate assistant responses
            block_unsafe_output: If True, raise OutputBlockedError for unsafe responses

        Raises:
            ImportError: If openai package is not installed
            ValueError: If seed_level is invalid
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        # Validate seed_level
        validated_level = _validate_seed_level(seed_level)

        self._client = OpenAI(api_key=api_key)
        self._sentinel = sentinel or Sentinel(seed_level=validated_level)
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._block_unsafe_output = block_unsafe_output
        self._seed = self._sentinel.get_seed()

    def create_assistant(
        self,
        name: str,
        instructions: Optional[str] = None,
        model: str = "gpt-4o",
        tools: Optional[List[Dict[str, Any]]] = None,
        inject_seed: bool = True,
        **kwargs,
    ) -> Any:
        """
        Create a new assistant with Sentinel protection.

        Args:
            name: Assistant name
            instructions: Base instructions
            model: Model to use
            tools: List of tools
            inject_seed: Whether to inject Sentinel seed
            **kwargs: Additional parameters

        Returns:
            OpenAI Assistant object
        """
        if inject_seed:
            if instructions:
                full_instructions = f"{self._seed}\n\n---\n\n{instructions}"
            else:
                full_instructions = self._seed
        else:
            full_instructions = instructions or ""

        return self._client.beta.assistants.create(
            name=name,
            instructions=full_instructions,
            model=model,
            tools=tools or [],
            **kwargs,
        )

    def create_thread(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Any:
        """
        Create a new conversation thread.

        Args:
            messages: Optional initial messages

        Returns:
            OpenAI Thread object

        Raises:
            ValidationError: If a message fails input validation
        """
        if messages:
            # Validate initial messages
            if self._validate_input:
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue

                    content = msg.get("content", "")
                    if not isinstance(content, str) or not content.strip():
                        continue

                    result = _safe_validate_request(self._sentinel, content, logger)
                    if not result["should_proceed"]:
                        concerns = result.get("concerns", [])
                        raise ValidationError(
                            f"Message blocked by Sentinel",
                            concerns=concerns
                        )

            return self._client.beta.threads.create(messages=messages)

        return self._client.beta.threads.create()

    def add_message(
        self,
        thread_id: str,
        content: str,
        role: str = "user",
    ) -> Any:
        """
        Add a message to a thread.

        Args:
            thread_id: Thread ID
            content: Message content
            role: Message role (user or assistant)

        Returns:
            OpenAI Message object

        Raises:
            ValidationError: If message fails input validation
        """
        # Validate user messages
        if self._validate_input and role == "user":
            # Skip empty content
            if content and content.strip():
                result = _safe_validate_request(self._sentinel, content, logger)
                if not result["should_proceed"]:
                    concerns = result.get("concerns", [])
                    raise ValidationError(
                        "Message blocked by Sentinel",
                        concerns=concerns
                    )

        return self._client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content,
        )

    def create_run(
        self,
        thread_id: str,
        assistant_id: str,
        instructions: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Create a run for an assistant on a thread.

        Args:
            thread_id: Thread ID
            assistant_id: Assistant ID
            instructions: Override instructions (seed will be prepended)
            **kwargs: Additional run parameters

        Returns:
            OpenAI Run object
        """
        run_params = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            **kwargs,
        }

        # Inject seed into override instructions if provided
        if instructions:
            run_params["instructions"] = f"{self._seed}\n\n---\n\n{instructions}"

        return self._client.beta.threads.runs.create(**run_params)

    def wait_for_run(
        self,
        thread_id: str,
        run_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
        handle_requires_action: bool = False,
    ) -> Any:
        """
        Wait for a run to complete.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            poll_interval: Seconds between status checks
            timeout: Maximum wait time
            handle_requires_action: If True, wait for manual action resolution.
                                   If False, raise AssistantRequiresActionError.

        Returns:
            Completed Run object

        Raises:
            TimeoutError: If run does not complete within timeout
            AssistantRequiresActionError: If run requires action and handle_requires_action is False
        """
        start_time = time.time()

        while True:
            run = self._client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id,
            )

            # Terminal states
            if run.status in ("completed", "failed", "cancelled", "expired"):
                return run

            # Requires action (function calling)
            if run.status == "requires_action":
                if not handle_requires_action:
                    raise AssistantRequiresActionError(
                        run_id=run_id,
                        required_action=getattr(run, "required_action", None)
                    )
                # If handle_requires_action is True, continue waiting for manual resolution

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Run {run_id} did not complete within {timeout}s")

            time.sleep(poll_interval)

    def get_messages(
        self,
        thread_id: str,
        limit: int = 20,
        order: str = "desc",
    ) -> List[Any]:
        """
        Get messages from a thread.

        Args:
            thread_id: Thread ID
            limit: Maximum messages to retrieve
            order: Sort order (asc or desc)

        Returns:
            List of Message objects
        """
        messages = self._client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=limit,
            order=order,
        )
        return list(messages.data)

    def run_conversation(
        self,
        assistant_id: str,
        thread_id: str,
        message: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Run a complete conversation turn.

        Adds a user message, creates a run, waits for completion,
        and returns the assistant's response with validation.

        Args:
            assistant_id: Assistant ID
            thread_id: Thread ID
            message: User message
            poll_interval: Seconds between status checks
            timeout: Maximum wait time

        Returns:
            Dict with 'response', 'messages', 'run', 'validated', 'validation'

        Raises:
            ValidationError: If user message fails input validation
            AssistantRunError: If the run fails, is cancelled, or expires
            OutputBlockedError: If output is unsafe and block_unsafe_output is True

        Example:
            result = client.run_conversation(
                assistant_id="asst_...",
                thread_id="thread_...",
                message="Help me debug this code"
            )
            print(result["response"])
        """
        # Add user message (may raise ValidationError)
        self.add_message(thread_id, message, role="user")

        # Create and wait for run
        run = self.create_run(thread_id, assistant_id)
        completed_run = self.wait_for_run(
            thread_id,
            run.id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

        # Check if run failed
        if completed_run.status == "failed":
            error_message = ""
            if hasattr(completed_run, "last_error") and completed_run.last_error:
                error_message = getattr(completed_run.last_error, "message", str(completed_run.last_error))
            raise AssistantRunError(run.id, "failed", error_message)

        if completed_run.status == "cancelled":
            raise AssistantRunError(run.id, "cancelled", "Run was cancelled")

        if completed_run.status == "expired":
            raise AssistantRunError(run.id, "expired", "Run expired")

        # Get response messages
        messages = self.get_messages(thread_id, limit=5)

        # Extract assistant response safely
        response_text = _extract_response_text(messages, logger)

        # Validate output
        validation_result = {"valid": True, "violations": []}
        if self._validate_output and response_text:
            is_safe, violations = _safe_validate_output(self._sentinel, response_text, logger)
            validation_result = {
                "valid": is_safe,
                "violations": violations,
            }
            if not is_safe:
                logger.warning(f"Output validation concerns: {violations}")

                # Block if configured
                if self._block_unsafe_output:
                    raise OutputBlockedError(violations)

        return {
            "response": response_text,
            "messages": messages,
            "run": completed_run,
            "validated": validation_result["valid"],
            "validation": validation_result,
        }

    def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant."""
        result = self._client.beta.assistants.delete(assistant_id)
        return result.deleted

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread."""
        result = self._client.beta.threads.delete(thread_id)
        return result.deleted


class SentinelAsyncAssistantClient:
    """
    Async version of SentinelAssistantClient.

    Example:
        from sentinelseed.integrations.openai_assistant import SentinelAsyncAssistantClient

        async def main():
            client = SentinelAsyncAssistantClient()
            assistant = await client.create_assistant(name="Helper")
            thread = await client.create_thread()
            result = await client.run_conversation(
                assistant.id, thread.id, "Hello!"
            )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        validate_input: bool = True,
        validate_output: bool = True,
        block_unsafe_output: bool = False,
    ):
        """
        Initialize async client.

        Args:
            api_key: OpenAI API key
            sentinel: Sentinel instance
            seed_level: Seed level to use ("minimal", "standard", "full")
            validate_input: Whether to validate user messages
            validate_output: Whether to validate assistant responses
            block_unsafe_output: If True, raise OutputBlockedError for unsafe responses

        Raises:
            ImportError: If openai package is not installed
            ValueError: If seed_level is invalid
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")

        # Validate seed_level
        validated_level = _validate_seed_level(seed_level)

        self._client = AsyncOpenAI(api_key=api_key)
        self._sentinel = sentinel or Sentinel(seed_level=validated_level)
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._block_unsafe_output = block_unsafe_output
        self._seed = self._sentinel.get_seed()

    async def create_assistant(
        self,
        name: str,
        instructions: Optional[str] = None,
        model: str = "gpt-4o",
        tools: Optional[List[Dict[str, Any]]] = None,
        inject_seed: bool = True,
        **kwargs,
    ) -> Any:
        """Async create assistant."""
        if inject_seed:
            if instructions:
                full_instructions = f"{self._seed}\n\n---\n\n{instructions}"
            else:
                full_instructions = self._seed
        else:
            full_instructions = instructions or ""

        return await self._client.beta.assistants.create(
            name=name,
            instructions=full_instructions,
            model=model,
            tools=tools or [],
            **kwargs,
        )

    async def create_thread(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Any:
        """
        Async create thread.

        Args:
            messages: Optional initial messages

        Returns:
            OpenAI Thread object

        Raises:
            ValidationError: If a message fails input validation
        """
        if messages:
            if self._validate_input:
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue

                    content = msg.get("content", "")
                    if not isinstance(content, str) or not content.strip():
                        continue

                    result = _safe_validate_request(self._sentinel, content, logger)
                    if not result["should_proceed"]:
                        concerns = result.get("concerns", [])
                        raise ValidationError(
                            "Message blocked by Sentinel",
                            concerns=concerns
                        )

            return await self._client.beta.threads.create(messages=messages)

        return await self._client.beta.threads.create()

    async def add_message(
        self,
        thread_id: str,
        content: str,
        role: str = "user",
    ) -> Any:
        """
        Async add message.

        Args:
            thread_id: Thread ID
            content: Message content
            role: Message role (user or assistant)

        Returns:
            OpenAI Message object

        Raises:
            ValidationError: If message fails input validation
        """
        if self._validate_input and role == "user":
            # Skip empty content
            if content and content.strip():
                result = _safe_validate_request(self._sentinel, content, logger)
                if not result["should_proceed"]:
                    concerns = result.get("concerns", [])
                    raise ValidationError(
                        "Message blocked by Sentinel",
                        concerns=concerns
                    )

        return await self._client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content,
        )

    async def create_run(
        self,
        thread_id: str,
        assistant_id: str,
        instructions: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Async create run."""
        run_params = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            **kwargs,
        }

        if instructions:
            run_params["instructions"] = f"{self._seed}\n\n---\n\n{instructions}"

        return await self._client.beta.threads.runs.create(**run_params)

    async def wait_for_run(
        self,
        thread_id: str,
        run_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
        handle_requires_action: bool = False,
    ) -> Any:
        """
        Async wait for run completion.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            poll_interval: Seconds between status checks
            timeout: Maximum wait time
            handle_requires_action: If True, wait for manual action resolution.
                                   If False, raise AssistantRequiresActionError.

        Returns:
            Completed Run object

        Raises:
            TimeoutError: If run does not complete within timeout
            AssistantRequiresActionError: If run requires action and handle_requires_action is False
        """
        start_time = time.time()

        while True:
            run = await self._client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id,
            )

            # Terminal states
            if run.status in ("completed", "failed", "cancelled", "expired"):
                return run

            # Requires action (function calling)
            if run.status == "requires_action":
                if not handle_requires_action:
                    raise AssistantRequiresActionError(
                        run_id=run_id,
                        required_action=getattr(run, "required_action", None)
                    )
                # If handle_requires_action is True, continue waiting for manual resolution

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Run {run_id} did not complete within {timeout}s")

            await asyncio.sleep(poll_interval)

    async def get_messages(
        self,
        thread_id: str,
        limit: int = 20,
        order: str = "desc",
    ) -> List[Any]:
        """
        Get messages from a thread.

        Args:
            thread_id: Thread ID
            limit: Maximum messages to retrieve
            order: Sort order (asc or desc)

        Returns:
            List of Message objects
        """
        messages = await self._client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=limit,
            order=order,
        )
        return list(messages.data)

    async def run_conversation(
        self,
        assistant_id: str,
        thread_id: str,
        message: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Async run complete conversation turn.

        Args:
            assistant_id: Assistant ID
            thread_id: Thread ID
            message: User message
            poll_interval: Seconds between status checks
            timeout: Maximum wait time

        Returns:
            Dict with 'response', 'messages', 'run', 'validated', 'validation'

        Raises:
            ValidationError: If user message fails input validation
            AssistantRunError: If the run fails, is cancelled, or expires
            OutputBlockedError: If output is unsafe and block_unsafe_output is True
        """
        # Add user message (may raise ValidationError)
        await self.add_message(thread_id, message, role="user")

        run = await self.create_run(thread_id, assistant_id)
        completed_run = await self.wait_for_run(
            thread_id,
            run.id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

        # Check if run failed
        if completed_run.status == "failed":
            error_message = ""
            if hasattr(completed_run, "last_error") and completed_run.last_error:
                error_message = getattr(completed_run.last_error, "message", str(completed_run.last_error))
            raise AssistantRunError(run.id, "failed", error_message)

        if completed_run.status == "cancelled":
            raise AssistantRunError(run.id, "cancelled", "Run was cancelled")

        if completed_run.status == "expired":
            raise AssistantRunError(run.id, "expired", "Run expired")

        # Get response messages
        messages = await self.get_messages(thread_id, limit=5)

        # Extract assistant response safely
        response_text = _extract_response_text(messages, logger)

        validation_result = {"valid": True, "violations": []}
        if self._validate_output and response_text:
            is_safe, violations = _safe_validate_output(self._sentinel, response_text, logger)
            validation_result = {"valid": is_safe, "violations": violations}

            if not is_safe:
                logger.warning(f"Output validation concerns: {violations}")

                # Block if configured
                if self._block_unsafe_output:
                    raise OutputBlockedError(violations)

        return {
            "response": response_text,
            "messages": messages,
            "run": completed_run,
            "validated": validation_result["valid"],
            "validation": validation_result,
        }

    async def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant."""
        result = await self._client.beta.assistants.delete(assistant_id)
        return result.deleted

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread."""
        result = await self._client.beta.threads.delete(thread_id)
        return result.deleted


def wrap_assistant(
    assistant: Any,
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
) -> SentinelAssistant:
    """
    Wrap an existing OpenAI assistant with Sentinel.

    Note: This wraps the local reference only. To add Sentinel
    instructions to the assistant itself, use update() or
    create a new assistant with SentinelAssistant.create().

    Args:
        assistant: OpenAI Assistant object
        sentinel: Sentinel instance
        seed_level: Seed level ("minimal", "standard", "full")

    Returns:
        SentinelAssistant wrapper

    Raises:
        ValueError: If seed_level is invalid

    Example:
        from openai import OpenAI
        from sentinelseed.integrations.openai_assistant import wrap_assistant

        client = OpenAI()
        assistant = client.beta.assistants.retrieve("asst_...")
        safe_assistant = wrap_assistant(assistant)
    """
    # M001: Guard against double wrapping
    if isinstance(assistant, SentinelAssistant):
        logger.warning(
            f"Assistant '{getattr(assistant, 'name', 'unknown')}' already wrapped. "
            "Returning as-is to prevent double wrapping."
        )
        return assistant

    # Validate seed_level (SentinelAssistant.__init__ also validates, but fail early)
    validated_level = _validate_seed_level(seed_level)
    return SentinelAssistant(assistant, sentinel, validated_level)


def inject_seed_instructions(
    instructions: Optional[str] = None,
    seed_level: str = "standard",
) -> str:
    """
    Inject Sentinel seed into assistant instructions.

    Use this to prepare instructions for assistant creation.

    Args:
        instructions: Base instructions
        seed_level: Seed level to use ("minimal", "standard", "full")

    Returns:
        Instructions with Sentinel seed prepended

    Raises:
        ValueError: If seed_level is invalid

    Example:
        from openai import OpenAI
        from sentinelseed.integrations.openai_assistant import inject_seed_instructions

        client = OpenAI()
        assistant = client.beta.assistants.create(
            name="Helper",
            instructions=inject_seed_instructions("You help users"),
            model="gpt-4o"
        )
    """
    # Validate seed_level
    validated_level = _validate_seed_level(seed_level)

    sentinel = Sentinel(seed_level=validated_level)
    seed = sentinel.get_seed()

    if instructions:
        return f"{seed}\n\n---\n\n{instructions}"
    return seed
