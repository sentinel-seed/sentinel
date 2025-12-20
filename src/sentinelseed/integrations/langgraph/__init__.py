"""
LangGraph integration for Sentinel AI.

Provides safety nodes, guards, and tools for LangGraph agent workflows:
- SentinelSafetyNode: Pre/post validation node for agent graphs
- SentinelGuardNode: Wrapper node that validates before/after execution
- SentinelAgentExecutor: Wrapper for compiled graphs with safety
- sentinel_gate_tool: Tool for agents to self-check actions
- create_sentinel_tool: LangChain-compatible safety tool
- add_safety_layer: Add safety nodes to existing graphs
- conditional_safety_edge: Route based on safety state

Usage:
    from sentinelseed.integrations.langgraph import (
        SentinelSafetyNode,
        SentinelGuardNode,
        add_safety_layer,
        sentinel_gate_tool,
    )

    # Option 1: Add safety node to existing graph
    graph.add_node("sentinel_check", SentinelSafetyNode())

    # Option 2: Wrap a node with safety guards
    safe_node = SentinelGuardNode(your_node)

    # Option 3: Give agent a safety self-check tool
    tools = [your_tools..., sentinel_gate_tool]
"""

from typing import Any, Dict, List, Optional, Union, Callable, TypedDict, Protocol
import logging
import asyncio

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.validators.gates import THSPValidator


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_VALIDATION_TIMEOUT = 30.0  # 30 seconds


# =============================================================================
# Exceptions
# =============================================================================

class TextTooLargeError(Exception):
    """Raised when input text exceeds maximum allowed size."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Text size ({size:,} bytes) exceeds maximum allowed ({max_size:,} bytes)"
        )


class ValidationTimeoutError(Exception):
    """Raised when validation exceeds timeout."""

    def __init__(self, timeout: float, operation: str = "validation"):
        self.timeout = timeout
        self.operation = operation
        super().__init__(f"{operation} timed out after {timeout}s")


class SafetyValidationError(Exception):
    """Raised when safety validation fails in fail_closed mode."""

    def __init__(self, message: str, violations: List[str] = None):
        self.violations = violations or []
        super().__init__(message)


# =============================================================================
# Logger
# =============================================================================

class SentinelLogger(Protocol):
    """Protocol for custom logger implementations."""

    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class DefaultLogger:
    """Default logger using Python's logging module."""

    def __init__(self, name: str = "sentinelseed.langgraph"):
        self._logger = logging.getLogger(name)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)


# Module-level logger (can be replaced)
_logger: SentinelLogger = DefaultLogger()


def set_logger(logger: SentinelLogger) -> None:
    """
    Set a custom logger for the LangGraph integration.

    Args:
        logger: Logger instance implementing SentinelLogger protocol

    Example:
        import logging

        class MyLogger:
            def debug(self, msg): logging.debug(f"[SENTINEL] {msg}")
            def info(self, msg): logging.info(f"[SENTINEL] {msg}")
            def warning(self, msg): logging.warning(f"[SENTINEL] {msg}")
            def error(self, msg): logging.error(f"[SENTINEL] {msg}")

        set_logger(MyLogger())
    """
    global _logger
    _logger = logger


def get_logger() -> SentinelLogger:
    """Get the current logger instance."""
    return _logger


# =============================================================================
# Validation Helpers
# =============================================================================

def _validate_text_size(
    text: str,
    max_size: int = DEFAULT_MAX_TEXT_SIZE,
    context: str = "text"
) -> None:
    """
    Validate text size against maximum limit.

    Args:
        text: Text to validate
        max_size: Maximum allowed size in bytes
        context: Context for error message

    Raises:
        TextTooLargeError: If text exceeds maximum size
    """
    if not text or not isinstance(text, str):
        return
    size = len(text.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size, max_size)


def _validate_state(state: Dict[str, Any], message_key: str = "messages") -> List[Any]:
    """
    Validate state and extract messages safely.

    Args:
        state: State dictionary
        message_key: Key for messages in state

    Returns:
        List of messages (empty list if invalid)
    """
    if not state or not isinstance(state, dict):
        return []
    messages = state.get(message_key)
    if messages is None:
        return []
    if not isinstance(messages, list):
        return []
    return messages


# =============================================================================
# State Type
# =============================================================================

class SentinelState(TypedDict, total=False):
    """State extension for Sentinel safety tracking."""
    sentinel_safe: bool
    sentinel_violations: List[str]
    sentinel_blocked: bool
    sentinel_risk_level: str


# =============================================================================
# Message Helpers
# =============================================================================

def _is_user_message(msg: Any) -> bool:
    """Check if message is from user."""
    if isinstance(msg, dict):
        return msg.get("role") == "user" or msg.get("type") == "human"
    if hasattr(msg, "type"):
        return msg.type in ("human", "user")
    return False


def _is_assistant_message(msg: Any) -> bool:
    """Check if message is from assistant."""
    if isinstance(msg, dict):
        return msg.get("role") == "assistant" or msg.get("type") == "ai"
    if hasattr(msg, "type"):
        return msg.type in ("ai", "assistant")
    return False


def _get_content(msg: Any) -> str:
    """Extract content from message."""
    if isinstance(msg, dict):
        return msg.get("content", "")
    if hasattr(msg, "content"):
        return str(msg.content) if msg.content else ""
    return str(msg) if msg else ""


def _create_block_message(violations: List[str]) -> Dict[str, str]:
    """Create a blocking response message."""
    concerns = ", ".join(violations) if violations else "safety concerns detected"
    return {
        "role": "assistant",
        "content": f"I cannot proceed with this request. Safety concerns: {concerns}"
    }


# =============================================================================
# SentinelSafetyNode
# =============================================================================

class SentinelSafetyNode:
    """
    LangGraph node that validates state content for safety.

    Can be used as an entry gate, exit gate, or intermediate checkpoint
    in agent workflows. Validates messages and content against THSP protocol.

    Example:
        from langgraph.graph import StateGraph, MessagesState
        from sentinelseed.integrations.langgraph import SentinelSafetyNode

        safety_node = SentinelSafetyNode(on_violation="block")

        graph = StateGraph(MessagesState)
        graph.add_node("safety_check", safety_node)
        graph.add_edge("user_input", "safety_check")
        graph.add_edge("safety_check", "agent")
    """

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
        on_violation: str = "log",
        check_input: bool = True,
        check_output: bool = True,
        message_key: str = "messages",
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        fail_closed: bool = False,
        logger: Optional[SentinelLogger] = None,
    ):
        """
        Initialize safety node.

        Args:
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level to use ("minimal", "standard", "full")
            on_violation: Action on violation:
                - "log": Log and continue
                - "block": Block execution and return safe response
                - "flag": Add flag to state but continue
            check_input: Whether to validate input (user) messages
            check_output: Whether to validate output (assistant) messages
            message_key: Key in state containing messages
            max_text_size: Maximum text size in bytes (default: 50KB)
            fail_closed: Raise exception on validation errors (default: False)
            logger: Custom logger instance
        """
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.on_violation = on_violation
        self.check_input = check_input
        self.check_output = check_output
        self.message_key = message_key
        self.max_text_size = max_text_size
        self.fail_closed = fail_closed
        self._logger = logger or _logger

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process state and validate for safety.

        Args:
            state: Current graph state

        Returns:
            Updated state with safety annotations
        """
        violations = []
        risk_level = "low"

        try:
            messages = _validate_state(state, self.message_key)

            if self.check_input:
                for msg in messages:
                    if _is_user_message(msg):
                        content = _get_content(msg)
                        if not content:
                            continue

                        try:
                            _validate_text_size(content, self.max_text_size, "input message")
                        except TextTooLargeError as e:
                            violations.append(f"Input too large: {e}")
                            risk_level = "high"
                            continue

                        try:
                            result = self.sentinel.validate_request(content)
                            if not result["should_proceed"]:
                                violations.extend(result.get("concerns", []))
                                risk_level = result.get("risk_level", "high")
                        except Exception as e:
                            self._logger.error(f"Validation error: {e}")
                            if self.fail_closed:
                                raise SafetyValidationError(f"Input validation failed: {e}")

            if self.check_output:
                for msg in messages:
                    if _is_assistant_message(msg):
                        content = _get_content(msg)
                        if not content:
                            continue

                        try:
                            _validate_text_size(content, self.max_text_size, "output message")
                        except TextTooLargeError as e:
                            violations.append(f"Output too large: {e}")
                            risk_level = "high"
                            continue

                        try:
                            is_safe, msg_violations = self.sentinel.validate(content)
                            if not is_safe:
                                violations.extend(msg_violations or [])
                                risk_level = "high"
                        except Exception as e:
                            self._logger.error(f"Output validation error: {e}")
                            if self.fail_closed:
                                raise SafetyValidationError(f"Output validation failed: {e}")

        except SafetyValidationError:
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error in SentinelSafetyNode: {e}")
            if self.fail_closed:
                raise SafetyValidationError(f"Safety node error: {e}")

        # Handle violations based on mode
        is_safe = len(violations) == 0
        blocked = False

        if not is_safe:
            if self.on_violation == "log":
                self._logger.warning(f"Violations detected: {violations}")
            elif self.on_violation == "block":
                blocked = True
                block_msg = _create_block_message(violations)
                messages = list(messages) + [block_msg]
                state = {**state, self.message_key: messages}
            elif self.on_violation == "flag":
                self._logger.info(f"Flagged violations: {violations}")

        return {
            **state,
            "sentinel_safe": is_safe,
            "sentinel_violations": violations,
            "sentinel_blocked": blocked,
            "sentinel_risk_level": risk_level,
        }

    async def __acall__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of __call__."""
        # For now, the validation is synchronous so we just call the sync version
        # In the future, this could use async validation
        return self.__call__(state)


# =============================================================================
# SentinelGuardNode
# =============================================================================

class SentinelGuardNode:
    """
    LangGraph node that wraps another node with safety validation.

    Validates inputs before and outputs after the wrapped node executes.
    Supports both synchronous and asynchronous wrapped nodes.

    Example:
        from sentinelseed.integrations.langgraph import SentinelGuardNode

        # Wrap your existing node
        safe_tool_node = SentinelGuardNode(tool_node)
        graph.add_node("safe_tools", safe_tool_node)
    """

    def __init__(
        self,
        wrapped_node: Callable,
        sentinel: Optional[Sentinel] = None,
        on_violation: str = "block",
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        fail_closed: bool = False,
        logger: Optional[SentinelLogger] = None,
    ):
        """
        Initialize guard node.

        Args:
            wrapped_node: The node function to wrap
            sentinel: Sentinel instance
            on_violation: Action on violation ("log", "block", "flag")
            max_text_size: Maximum text size in bytes (default: 50KB)
            fail_closed: Raise exception on validation errors (default: False)
            logger: Custom logger instance
        """
        self.wrapped_node = wrapped_node
        self.sentinel = sentinel or Sentinel()
        self.on_violation = on_violation
        self.max_text_size = max_text_size
        self.fail_closed = fail_closed
        self._logger = logger or _logger
        self._is_async = asyncio.iscoroutinefunction(wrapped_node)

    def _validate_messages(
        self,
        messages: List[Any],
        context: str = "input"
    ) -> tuple[bool, List[str]]:
        """
        Validate a list of messages.

        Returns:
            Tuple of (is_safe, violations)
        """
        violations = []

        for msg in messages:
            content = _get_content(msg)
            if not content:
                continue

            try:
                _validate_text_size(content, self.max_text_size, f"{context} message")
            except TextTooLargeError as e:
                violations.append(f"{context.capitalize()} too large: {e}")
                continue

            try:
                result = self.sentinel.validate_request(content)
                if not result["should_proceed"]:
                    violations.extend(result.get("concerns", []))
            except Exception as e:
                self._logger.error(f"{context.capitalize()} validation error: {e}")
                if self.fail_closed:
                    raise SafetyValidationError(f"{context.capitalize()} validation failed: {e}")

        return len(violations) == 0, violations

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wrapped node with safety checks (sync)."""
        try:
            # Pre-check: validate state before execution
            messages = _validate_state(state, "messages")
            is_safe, violations = self._validate_messages(messages, "input")

            if not is_safe and self.on_violation == "block":
                return {
                    **state,
                    "sentinel_blocked": True,
                    "sentinel_violations": violations,
                    "sentinel_safe": False,
                }

            # Execute wrapped node
            try:
                result_state = self.wrapped_node(state)
            except Exception as e:
                self._logger.error(f"Wrapped node execution error: {e}")
                if self.fail_closed:
                    raise
                return {
                    **state,
                    "sentinel_blocked": True,
                    "sentinel_violations": [f"Execution error: {e}"],
                    "sentinel_safe": False,
                }

            # Post-check: validate result
            result_messages = _validate_state(result_state, "messages")
            is_safe, violations = self._validate_messages(result_messages, "output")

            if not is_safe and self.on_violation == "block":
                return {
                    **result_state,
                    "sentinel_blocked": True,
                    "sentinel_violations": violations,
                    "sentinel_safe": False,
                }

            return {
                **result_state,
                "sentinel_safe": True,
                "sentinel_blocked": False,
            }

        except SafetyValidationError:
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error in SentinelGuardNode: {e}")
            if self.fail_closed:
                raise SafetyValidationError(f"Guard node error: {e}")
            return {
                **state,
                "sentinel_blocked": True,
                "sentinel_violations": [f"Error: {e}"],
                "sentinel_safe": False,
            }

    async def __acall__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wrapped node with safety checks (async)."""
        try:
            # Pre-check: validate state before execution
            messages = _validate_state(state, "messages")
            is_safe, violations = self._validate_messages(messages, "input")

            if not is_safe and self.on_violation == "block":
                return {
                    **state,
                    "sentinel_blocked": True,
                    "sentinel_violations": violations,
                    "sentinel_safe": False,
                }

            # Execute wrapped node (async or sync)
            try:
                if self._is_async:
                    result_state = await self.wrapped_node(state)
                else:
                    result_state = self.wrapped_node(state)
            except Exception as e:
                self._logger.error(f"Wrapped node execution error: {e}")
                if self.fail_closed:
                    raise
                return {
                    **state,
                    "sentinel_blocked": True,
                    "sentinel_violations": [f"Execution error: {e}"],
                    "sentinel_safe": False,
                }

            # Post-check: validate result
            result_messages = _validate_state(result_state, "messages")
            is_safe, violations = self._validate_messages(result_messages, "output")

            if not is_safe and self.on_violation == "block":
                return {
                    **result_state,
                    "sentinel_blocked": True,
                    "sentinel_violations": violations,
                    "sentinel_safe": False,
                }

            return {
                **result_state,
                "sentinel_safe": True,
                "sentinel_blocked": False,
            }

        except SafetyValidationError:
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error in async SentinelGuardNode: {e}")
            if self.fail_closed:
                raise SafetyValidationError(f"Guard node error: {e}")
            return {
                **state,
                "sentinel_blocked": True,
                "sentinel_violations": [f"Error: {e}"],
                "sentinel_safe": False,
            }


# =============================================================================
# Tools
# =============================================================================

def sentinel_gate_tool(
    action_description: str,
    sentinel: Optional[Sentinel] = None,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
) -> Dict[str, Any]:
    """
    Tool for agents to self-check their planned actions.

    Agents can call this tool before executing potentially risky actions
    to get safety validation through the THSP protocol.

    Args:
        action_description: Description of the action to validate
        sentinel: Sentinel instance (creates default if None)
        max_text_size: Maximum text size in bytes

    Returns:
        Dict with 'safe', 'proceed', 'concerns', and 'recommendation'

    Example (as LangChain tool):
        from langchain.tools import Tool
        from sentinelseed.integrations.langgraph import sentinel_gate_tool

        safety_tool = Tool(
            name="safety_check",
            description="Check if an action is safe before executing",
            func=lambda x: sentinel_gate_tool(x)
        )
    """
    if sentinel is None:
        sentinel = Sentinel()

    try:
        _validate_text_size(action_description, max_text_size, "action description")
    except TextTooLargeError as e:
        return {
            "safe": False,
            "proceed": False,
            "concerns": [str(e)],
            "risk_level": "high",
            "recommendation": f"Action blocked: {e}",
        }

    try:
        is_safe, violations = sentinel.validate_action(action_description)
        request_check = sentinel.validate_request(action_description)

        all_concerns = (violations or []) + request_check.get("concerns", [])
        proceed = is_safe and request_check["should_proceed"]

        if proceed:
            recommendation = "Action appears safe to proceed."
        else:
            recommendation = f"Action blocked. Address these concerns before proceeding: {', '.join(all_concerns)}"

        return {
            "safe": proceed,
            "proceed": proceed,
            "concerns": all_concerns,
            "risk_level": request_check.get("risk_level", "low") if proceed else "high",
            "recommendation": recommendation,
        }
    except Exception as e:
        _logger.error(f"Error in sentinel_gate_tool: {e}")
        return {
            "safe": False,
            "proceed": False,
            "concerns": [f"Validation error: {e}"],
            "risk_level": "high",
            "recommendation": f"Action blocked due to validation error: {e}",
        }


def create_sentinel_tool(
    sentinel: Optional[Sentinel] = None,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
):
    """
    Create a LangChain-compatible tool for safety checking.

    Returns a tool that can be added to any agent's toolkit.

    Args:
        sentinel: Sentinel instance (creates default if None)
        max_text_size: Maximum text size in bytes

    Returns:
        LangChain Tool object

    Raises:
        ImportError: If langchain is not installed

    Example:
        from sentinelseed.integrations.langgraph import create_sentinel_tool

        safety_tool = create_sentinel_tool()
        agent = create_react_agent(llm, tools=[..., safety_tool])
    """
    try:
        from langchain.tools import Tool
    except ImportError:
        raise ImportError(
            "langchain is required for create_sentinel_tool. "
            "Install with: pip install langchain"
        )

    _sentinel = sentinel or Sentinel()

    def check_action(action: str) -> str:
        """Check if an action is safe to execute."""
        result = sentinel_gate_tool(action, _sentinel, max_text_size)
        if result["safe"]:
            return f"SAFE: {result['recommendation']}"
        else:
            return f"BLOCKED: {result['recommendation']}"

    return Tool(
        name="sentinel_safety_check",
        description=(
            "Use this tool to verify if an action is safe before executing it. "
            "Input should be a description of the action you plan to take. "
            "The tool will check for harmful content, ethical concerns, and safety issues."
        ),
        func=check_action,
    )


# =============================================================================
# Graph Utilities
# =============================================================================

class SafetyLayerResult(TypedDict):
    """Result of adding safety layer to a graph."""
    graph: Any
    entry_node: Optional[str]
    exit_node: Optional[str]


def add_safety_layer(
    graph: Any,
    sentinel: Optional[Sentinel] = None,
    entry_check: bool = True,
    exit_check: bool = True,
    entry_node_name: str = "sentinel_entry",
    exit_node_name: str = "sentinel_exit",
    on_violation: str = "flag",
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
) -> SafetyLayerResult:
    """
    Add Sentinel safety nodes to a LangGraph StateGraph.

    This function adds safety nodes but does NOT automatically connect edges.
    You must manually connect the edges after calling this function.

    Args:
        graph: LangGraph StateGraph to modify
        sentinel: Sentinel instance
        entry_check: Add safety node at entry
        exit_check: Add safety node before end
        entry_node_name: Name for entry safety node
        exit_node_name: Name for exit safety node
        on_violation: Action on violation ("log", "block", "flag")
        max_text_size: Maximum text size in bytes

    Returns:
        SafetyLayerResult with graph and node names

    Example:
        from langgraph.graph import StateGraph, START, END
        from sentinelseed.integrations.langgraph import add_safety_layer

        graph = StateGraph(MyState)
        graph.add_node("agent", agent_node)

        # Add safety layer
        result = add_safety_layer(graph)

        # Connect the edges manually:
        # START -> sentinel_entry -> agent -> sentinel_exit -> END
        graph.add_edge(START, result["entry_node"])
        graph.add_edge(result["entry_node"], "agent")
        graph.add_edge("agent", result["exit_node"])
        graph.add_edge(result["exit_node"], END)

        compiled = graph.compile()
    """
    if sentinel is None:
        sentinel = Sentinel()

    entry_name = None
    exit_name = None

    if entry_check:
        entry_node = SentinelSafetyNode(
            sentinel=sentinel,
            on_violation=on_violation,
            check_input=True,
            check_output=False,
            max_text_size=max_text_size,
        )
        graph.add_node(entry_node_name, entry_node)
        entry_name = entry_node_name

    if exit_check:
        exit_node = SentinelSafetyNode(
            sentinel=sentinel,
            on_violation=on_violation,
            check_input=False,
            check_output=True,
            max_text_size=max_text_size,
        )
        graph.add_node(exit_node_name, exit_node)
        exit_name = exit_node_name

    return SafetyLayerResult(
        graph=graph,
        entry_node=entry_name,
        exit_node=exit_name,
    )


def conditional_safety_edge(
    state: Dict[str, Any],
    safe_route: str = "continue",
    unsafe_route: str = "blocked",
) -> str:
    """
    Conditional edge function for routing based on safety state.

    Use this as a conditional edge after a Sentinel safety node
    to route to different paths based on safety validation.

    Args:
        state: Current graph state
        safe_route: Route name when safe (default: "continue")
        unsafe_route: Route name when unsafe (default: "blocked")

    Returns:
        Route name based on safety state

    Example:
        from sentinelseed.integrations.langgraph import conditional_safety_edge

        graph.add_conditional_edges(
            "safety_check",
            conditional_safety_edge,
            {
                "continue": "agent",
                "blocked": "safe_response",
            }
        )
    """
    if state.get("sentinel_blocked", False):
        return unsafe_route
    if not state.get("sentinel_safe", True):
        # Has violations but not blocked, check risk level
        if state.get("sentinel_risk_level") == "high":
            return unsafe_route
    return safe_route


def create_safety_router(
    safe_route: str = "continue",
    unsafe_route: str = "blocked",
) -> Callable[[Dict[str, Any]], str]:
    """
    Create a customized safety router function.

    This is a factory function that returns a conditional edge function
    with custom route names.

    Args:
        safe_route: Route name when safe
        unsafe_route: Route name when unsafe

    Returns:
        Conditional edge function

    Example:
        from sentinelseed.integrations.langgraph import create_safety_router

        router = create_safety_router(
            safe_route="process",
            unsafe_route="reject"
        )

        graph.add_conditional_edges(
            "safety_check",
            router,
            {
                "process": "agent",
                "reject": "rejection_handler",
            }
        )
    """
    def router(state: Dict[str, Any]) -> str:
        return conditional_safety_edge(state, safe_route, unsafe_route)
    return router


# =============================================================================
# SentinelAgentExecutor
# =============================================================================

class SentinelAgentExecutor:
    """
    Wrapper for LangGraph agent execution with Sentinel safety.

    Provides a simple interface to run agents with automatic
    safety validation at each step.

    Example:
        from sentinelseed.integrations.langgraph import SentinelAgentExecutor

        executor = SentinelAgentExecutor(your_compiled_graph)
        result = executor.invoke({"messages": [{"role": "user", "content": "..."}]})
    """

    def __init__(
        self,
        graph: Any,
        sentinel: Optional[Sentinel] = None,
        on_violation: str = "block",
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        max_output_messages: int = 5,
        fail_closed: bool = False,
        logger: Optional[SentinelLogger] = None,
    ):
        """
        Initialize executor.

        Args:
            graph: Compiled LangGraph
            sentinel: Sentinel instance
            on_violation: Action on violation ("log", "block", "flag")
            max_text_size: Maximum text size in bytes (default: 50KB)
            max_output_messages: Number of output messages to validate (default: 5)
            fail_closed: Raise exception on validation errors (default: False)
            logger: Custom logger instance
        """
        self.graph = graph
        self.sentinel = sentinel or Sentinel()
        self.on_violation = on_violation
        self.max_text_size = max_text_size
        self.max_output_messages = max_output_messages
        self.fail_closed = fail_closed
        self._logger = logger or _logger

    def _validate_input(
        self,
        input_state: Dict[str, Any]
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate input state.

        Returns:
            Tuple of (should_continue, blocked_response or None)
        """
        messages = _validate_state(input_state, "messages")

        for msg in messages:
            content = _get_content(msg)
            if not content:
                continue

            try:
                _validate_text_size(content, self.max_text_size, "input")
            except TextTooLargeError as e:
                if self.on_violation == "block":
                    return False, {
                        **input_state,
                        "sentinel_blocked": True,
                        "sentinel_violations": [str(e)],
                        "output": "Request blocked by Sentinel: input too large.",
                    }
                self._logger.warning(f"Input size warning: {e}")
                continue

            try:
                result = self.sentinel.validate_request(content)
                if not result["should_proceed"] and self.on_violation == "block":
                    return False, {
                        **input_state,
                        "sentinel_blocked": True,
                        "sentinel_violations": result.get("concerns", []),
                        "output": "Request blocked by Sentinel safety check.",
                    }
            except Exception as e:
                self._logger.error(f"Input validation error: {e}")
                if self.fail_closed:
                    raise SafetyValidationError(f"Input validation failed: {e}")

        return True, None

    def _validate_output(
        self,
        result: Dict[str, Any]
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate output state.

        Returns:
            Tuple of (is_safe, blocked_response or None)
        """
        output_messages = _validate_state(result, "messages")

        # Validate last N messages
        messages_to_check = output_messages[-self.max_output_messages:] if output_messages else []

        for msg in messages_to_check:
            content = _get_content(msg)
            if not content:
                continue

            try:
                _validate_text_size(content, self.max_text_size, "output")
            except TextTooLargeError as e:
                if self.on_violation == "block":
                    return False, {
                        **result,
                        "sentinel_blocked": True,
                        "sentinel_violations": [str(e)],
                    }
                self._logger.warning(f"Output size warning: {e}")
                continue

            try:
                is_safe, violations = self.sentinel.validate(content)
                if not is_safe and self.on_violation == "block":
                    return False, {
                        **result,
                        "sentinel_blocked": True,
                        "sentinel_violations": violations or [],
                    }
            except Exception as e:
                self._logger.error(f"Output validation error: {e}")
                if self.fail_closed:
                    raise SafetyValidationError(f"Output validation failed: {e}")

        return True, None

    def invoke(
        self,
        input_state: Dict[str, Any],
        config: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute graph with safety validation.

        Args:
            input_state: Initial state
            config: Optional LangGraph config

        Returns:
            Final state with safety annotations
        """
        # Pre-validate input
        should_continue, blocked = self._validate_input(input_state)
        if not should_continue:
            return blocked

        # Execute graph
        try:
            result = self.graph.invoke(input_state, config)
        except Exception as e:
            self._logger.error(f"Graph execution error: {e}")
            if self.fail_closed:
                raise
            return {
                **input_state,
                "sentinel_blocked": True,
                "sentinel_violations": [f"Execution error: {e}"],
            }

        # Post-validate output
        is_safe, blocked = self._validate_output(result)
        if not is_safe:
            return blocked

        return {
            **result,
            "sentinel_safe": True,
            "sentinel_blocked": False,
        }

    async def ainvoke(
        self,
        input_state: Dict[str, Any],
        config: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Async version of invoke."""
        # Pre-validate input
        should_continue, blocked = self._validate_input(input_state)
        if not should_continue:
            return blocked

        # Execute graph async
        try:
            result = await self.graph.ainvoke(input_state, config)
        except Exception as e:
            self._logger.error(f"Async graph execution error: {e}")
            if self.fail_closed:
                raise
            return {
                **input_state,
                "sentinel_blocked": True,
                "sentinel_violations": [f"Execution error: {e}"],
            }

        # Post-validate output
        is_safe, blocked = self._validate_output(result)
        if not is_safe:
            return blocked

        return {
            **result,
            "sentinel_safe": True,
            "sentinel_blocked": False,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main classes
    "SentinelSafetyNode",
    "SentinelGuardNode",
    "SentinelAgentExecutor",
    # Tools
    "sentinel_gate_tool",
    "create_sentinel_tool",
    # Graph utilities
    "add_safety_layer",
    "conditional_safety_edge",
    "create_safety_router",
    # Types
    "SentinelState",
    "SafetyLayerResult",
    # Exceptions
    "TextTooLargeError",
    "ValidationTimeoutError",
    "SafetyValidationError",
    # Logger
    "SentinelLogger",
    "DefaultLogger",
    "set_logger",
    "get_logger",
    # Constants
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
]
