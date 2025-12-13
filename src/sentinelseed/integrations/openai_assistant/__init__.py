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

from typing import Any, Dict, List, Optional, Union, Iterator
import os

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel

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
            seed_level: Seed level used
        """
        self._assistant = assistant
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._seed_level = seed_level

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
            seed_level: Seed level to use
            api_key: OpenAI API key
            **kwargs: Additional assistant parameters

        Returns:
            SentinelAssistant instance

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

        sentinel = sentinel or Sentinel(seed_level=seed_level)
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

        return cls(assistant, sentinel, seed_level)

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
    ):
        """
        Initialize Sentinel Assistant client.

        Args:
            api_key: OpenAI API key
            sentinel: Sentinel instance
            seed_level: Seed level to use
            validate_input: Whether to validate user messages
            validate_output: Whether to validate assistant responses
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        self._client = OpenAI(api_key=api_key)
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._validate_input = validate_input
        self._validate_output = validate_output
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
        """
        if messages:
            # Validate initial messages
            if self._validate_input:
                for msg in messages:
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        result = self._sentinel.validate_request(content)
                        if not result["should_proceed"]:
                            raise ValueError(f"Message blocked: {result['concerns']}")

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
        """
        # Validate user messages
        if self._validate_input and role == "user":
            result = self._sentinel.validate_request(content)
            if not result["should_proceed"]:
                raise ValueError(f"Message blocked by Sentinel: {result['concerns']}")

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
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> Any:
        """
        Wait for a run to complete.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            poll_interval: Seconds between status checks
            timeout: Maximum wait time

        Returns:
            Completed Run object
        """
        import time

        start_time = time.time()

        while True:
            run = self._client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id,
            )

            if run.status in ("completed", "failed", "cancelled", "expired"):
                return run

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
        poll_interval: float = 1.0,
        timeout: float = 300.0,
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
            Dict with 'response', 'messages', 'run', 'validated'

        Example:
            result = client.run_conversation(
                assistant_id="asst_...",
                thread_id="thread_...",
                message="Help me debug this code"
            )
            print(result["response"])
        """
        # Add user message
        self.add_message(thread_id, message, role="user")

        # Create and wait for run
        run = self.create_run(thread_id, assistant_id)
        completed_run = self.wait_for_run(
            thread_id,
            run.id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

        # Get response messages
        messages = self.get_messages(thread_id, limit=5)

        # Extract assistant response
        response_text = ""
        for msg in messages:
            if msg.role == "assistant":
                for block in msg.content:
                    if hasattr(block, "text"):
                        response_text = block.text.value
                        break
                break

        # Validate output
        validation_result = {"valid": True, "violations": []}
        if self._validate_output and response_text:
            is_safe, violations = self._sentinel.validate(response_text)
            validation_result = {
                "valid": is_safe,
                "violations": violations,
            }
            if not is_safe:
                print(f"[SENTINEL] Output validation concerns: {violations}")

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
    ):
        """Initialize async client."""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")

        self._client = AsyncOpenAI(api_key=api_key)
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._validate_input = validate_input
        self._validate_output = validate_output
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
        """Async create thread."""
        if messages:
            if self._validate_input:
                for msg in messages:
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        result = self._sentinel.validate_request(content)
                        if not result["should_proceed"]:
                            raise ValueError(f"Message blocked: {result['concerns']}")

            return await self._client.beta.threads.create(messages=messages)

        return await self._client.beta.threads.create()

    async def add_message(
        self,
        thread_id: str,
        content: str,
        role: str = "user",
    ) -> Any:
        """Async add message."""
        if self._validate_input and role == "user":
            result = self._sentinel.validate_request(content)
            if not result["should_proceed"]:
                raise ValueError(f"Message blocked: {result['concerns']}")

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
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> Any:
        """Async wait for run completion."""
        import asyncio
        import time

        start_time = time.time()

        while True:
            run = await self._client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id,
            )

            if run.status in ("completed", "failed", "cancelled", "expired"):
                return run

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Run {run_id} did not complete")

            await asyncio.sleep(poll_interval)

    async def run_conversation(
        self,
        assistant_id: str,
        thread_id: str,
        message: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Async run complete conversation turn."""
        await self.add_message(thread_id, message, role="user")

        run = await self.create_run(thread_id, assistant_id)
        completed_run = await self.wait_for_run(
            thread_id,
            run.id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

        messages = await self._client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=5,
            order="desc",
        )

        response_text = ""
        for msg in messages.data:
            if msg.role == "assistant":
                for block in msg.content:
                    if hasattr(block, "text"):
                        response_text = block.text.value
                        break
                break

        validation_result = {"valid": True, "violations": []}
        if self._validate_output and response_text:
            is_safe, violations = self._sentinel.validate(response_text)
            validation_result = {"valid": is_safe, "violations": violations}

        return {
            "response": response_text,
            "messages": list(messages.data),
            "run": completed_run,
            "validated": validation_result["valid"],
            "validation": validation_result,
        }


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
        seed_level: Seed level

    Returns:
        SentinelAssistant wrapper

    Example:
        from openai import OpenAI
        from sentinelseed.integrations.openai_assistant import wrap_assistant

        client = OpenAI()
        assistant = client.beta.assistants.retrieve("asst_...")
        safe_assistant = wrap_assistant(assistant)
    """
    return SentinelAssistant(assistant, sentinel, seed_level)


def inject_seed_instructions(
    instructions: Optional[str] = None,
    seed_level: str = "standard",
) -> str:
    """
    Inject Sentinel seed into assistant instructions.

    Use this to prepare instructions for assistant creation.

    Args:
        instructions: Base instructions
        seed_level: Seed level to use

    Returns:
        Instructions with Sentinel seed prepended

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
    sentinel = Sentinel(seed_level=seed_level)
    seed = sentinel.get_seed()

    if instructions:
        return f"{seed}\n\n---\n\n{instructions}"
    return seed
