"""
LangGraph integration for Sentinel AI.

Provides safety nodes and tools for LangGraph agent workflows:
- SentinelSafetyNode: Pre/post validation node for agent graphs
- SentinelGuardNode: Wrapper node that validates tool calls
- sentinel_gate_tool: Tool for agents to self-check actions
- create_safe_graph: Factory to wrap any graph with safety

Usage:
    from sentinel.integrations.langgraph import (
        SentinelSafetyNode,
        create_safe_graph,
        sentinel_gate_tool
    )

    # Option 1: Add safety node to existing graph
    graph.add_node("sentinel_check", SentinelSafetyNode())

    # Option 2: Create a safe graph wrapper
    safe_graph = create_safe_graph(your_graph)

    # Option 3: Give agent a safety self-check tool
    tools = [your_tools..., sentinel_gate_tool]
"""

from typing import Any, Dict, List, Optional, Union, Callable, TypedDict

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel


class SentinelState(TypedDict, total=False):
    """State extension for Sentinel safety tracking."""
    sentinel_safe: bool
    sentinel_violations: List[str]
    sentinel_blocked: bool
    sentinel_risk_level: str


class SentinelSafetyNode:
    """
    LangGraph node that validates state content for safety.

    Can be used as an entry gate, exit gate, or intermediate checkpoint
    in agent workflows. Validates messages and content against THSP protocol.

    Example:
        from langgraph.graph import StateGraph, MessagesState
        from sentinel.integrations.langgraph import SentinelSafetyNode

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
        on_violation: str = "log",  # "log", "block", "flag"
        check_input: bool = True,
        check_output: bool = True,
        message_key: str = "messages",
    ):
        """
        Initialize safety node.

        Args:
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level to use
            on_violation: Action on violation:
                - "log": Log and continue
                - "block": Block execution and return safe response
                - "flag": Add flag to state but continue
            check_input: Whether to validate input messages
            check_output: Whether to validate output messages
            message_key: Key in state containing messages
        """
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.on_violation = on_violation
        self.check_input = check_input
        self.check_output = check_output
        self.message_key = message_key

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

        # Get messages from state
        messages = state.get(self.message_key, [])

        if self.check_input:
            # Validate user messages
            for msg in messages:
                if self._is_user_message(msg):
                    content = self._get_content(msg)
                    result = self.sentinel.validate_request(content)

                    if not result["should_proceed"]:
                        violations.extend(result["concerns"])
                        risk_level = result["risk_level"]

        if self.check_output:
            # Validate assistant messages
            for msg in messages:
                if self._is_assistant_message(msg):
                    content = self._get_content(msg)
                    is_safe, msg_violations = self.sentinel.validate(content)

                    if not is_safe:
                        violations.extend(msg_violations)
                        risk_level = "high"

        # Handle violations based on mode
        is_safe = len(violations) == 0
        blocked = False

        if not is_safe:
            if self.on_violation == "log":
                print(f"[SENTINEL] Violations detected: {violations}")
            elif self.on_violation == "block":
                blocked = True
                # Add blocking response to messages
                block_msg = self._create_block_message(violations)
                messages = list(messages) + [block_msg]
                state = {**state, self.message_key: messages}
            elif self.on_violation == "flag":
                pass  # Just add to state below

        # Update state with safety info
        return {
            **state,
            "sentinel_safe": is_safe,
            "sentinel_violations": violations,
            "sentinel_blocked": blocked,
            "sentinel_risk_level": risk_level,
        }

    def _is_user_message(self, msg: Any) -> bool:
        """Check if message is from user."""
        if isinstance(msg, dict):
            return msg.get("role") == "user" or msg.get("type") == "human"
        if hasattr(msg, "type"):
            return msg.type in ("human", "user")
        return False

    def _is_assistant_message(self, msg: Any) -> bool:
        """Check if message is from assistant."""
        if isinstance(msg, dict):
            return msg.get("role") == "assistant" or msg.get("type") == "ai"
        if hasattr(msg, "type"):
            return msg.type in ("ai", "assistant")
        return False

    def _get_content(self, msg: Any) -> str:
        """Extract content from message."""
        if isinstance(msg, dict):
            return msg.get("content", "")
        if hasattr(msg, "content"):
            return msg.content
        return str(msg)

    def _create_block_message(self, violations: List[str]) -> Dict[str, str]:
        """Create a blocking response message."""
        return {
            "role": "assistant",
            "content": f"I cannot proceed with this request. Safety concerns: {', '.join(violations)}"
        }


class SentinelGuardNode:
    """
    LangGraph node that wraps another node with safety validation.

    Validates inputs before and outputs after the wrapped node executes.

    Example:
        from sentinel.integrations.langgraph import SentinelGuardNode

        # Wrap your existing node
        safe_tool_node = SentinelGuardNode(tool_node)
        graph.add_node("safe_tools", safe_tool_node)
    """

    def __init__(
        self,
        wrapped_node: Callable,
        sentinel: Optional[Sentinel] = None,
        block_unsafe: bool = True,
    ):
        """
        Initialize guard node.

        Args:
            wrapped_node: The node function to wrap
            sentinel: Sentinel instance
            block_unsafe: Whether to block unsafe executions
        """
        self.wrapped_node = wrapped_node
        self.sentinel = sentinel or Sentinel()
        self.block_unsafe = block_unsafe

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wrapped node with safety checks."""
        # Pre-check: validate state before execution
        messages = state.get("messages", [])
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = getattr(msg, "content", str(msg))

            result = self.sentinel.validate_request(content)
            if not result["should_proceed"] and self.block_unsafe:
                return {
                    **state,
                    "sentinel_blocked": True,
                    "sentinel_violations": result["concerns"],
                }

        # Execute wrapped node
        result_state = self.wrapped_node(state)

        # Post-check: validate result
        result_messages = result_state.get("messages", [])
        for msg in result_messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = getattr(msg, "content", str(msg))

            is_safe, violations = self.sentinel.validate(content)
            if not is_safe and self.block_unsafe:
                return {
                    **result_state,
                    "sentinel_blocked": True,
                    "sentinel_violations": violations,
                }

        return {
            **result_state,
            "sentinel_safe": True,
            "sentinel_blocked": False,
        }


def sentinel_gate_tool(
    action_description: str,
    sentinel: Optional[Sentinel] = None,
) -> Dict[str, Any]:
    """
    Tool for agents to self-check their planned actions.

    Agents can call this tool before executing potentially risky actions
    to get safety validation through the THSP protocol.

    Args:
        action_description: Description of the action to validate
        sentinel: Sentinel instance (creates default if None)

    Returns:
        Dict with 'safe', 'proceed', 'concerns', and 'recommendation'

    Example (as LangChain tool):
        from langchain.tools import Tool
        from sentinel.integrations.langgraph import sentinel_gate_tool

        safety_tool = Tool(
            name="safety_check",
            description="Check if an action is safe before executing",
            func=lambda x: sentinel_gate_tool(x)
        )
    """
    if sentinel is None:
        sentinel = Sentinel()

    # Validate the action
    is_safe, violations = sentinel.validate_action(action_description)
    request_check = sentinel.validate_request(action_description)

    # Combine assessments
    all_concerns = violations + request_check.get("concerns", [])
    proceed = is_safe and request_check["should_proceed"]

    # Generate recommendation
    if proceed:
        recommendation = "Action appears safe to proceed."
    else:
        recommendation = f"Action blocked. Address these concerns before proceeding: {', '.join(all_concerns)}"

    return {
        "safe": proceed,
        "proceed": proceed,
        "concerns": all_concerns,
        "risk_level": request_check["risk_level"] if not proceed else "low",
        "recommendation": recommendation,
    }


def create_sentinel_tool():
    """
    Create a LangChain-compatible tool for safety checking.

    Returns a tool that can be added to any agent's toolkit.

    Example:
        from sentinel.integrations.langgraph import create_sentinel_tool

        safety_tool = create_sentinel_tool()
        agent = create_react_agent(llm, tools=[..., safety_tool])
    """
    try:
        from langchain.tools import Tool
    except ImportError:
        raise ImportError("langchain is required for create_sentinel_tool")

    sentinel = Sentinel()

    def check_action(action: str) -> str:
        """Check if an action is safe to execute."""
        result = sentinel_gate_tool(action, sentinel)
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


def create_safe_graph(
    graph: Any,
    sentinel: Optional[Sentinel] = None,
    entry_check: bool = True,
    exit_check: bool = True,
) -> Any:
    """
    Wrap a LangGraph StateGraph with Sentinel safety nodes.

    Adds safety validation at graph entry and/or exit points.

    Args:
        graph: LangGraph StateGraph to wrap
        sentinel: Sentinel instance
        entry_check: Add safety node at entry
        exit_check: Add safety node before end

    Returns:
        Modified graph with safety nodes

    Example:
        from langgraph.graph import StateGraph
        from sentinel.integrations.langgraph import create_safe_graph

        graph = StateGraph(MyState)
        # ... add your nodes and edges ...

        safe_graph = create_safe_graph(graph)
        compiled = safe_graph.compile()
    """
    if sentinel is None:
        sentinel = Sentinel()

    if entry_check:
        entry_node = SentinelSafetyNode(
            sentinel=sentinel,
            on_violation="flag",
            check_input=True,
            check_output=False,
        )
        graph.add_node("sentinel_entry", entry_node)

    if exit_check:
        exit_node = SentinelSafetyNode(
            sentinel=sentinel,
            on_violation="flag",
            check_input=False,
            check_output=True,
        )
        graph.add_node("sentinel_exit", exit_node)

    return graph


def conditional_safety_edge(
    state: Dict[str, Any],
    safe_route: str = "continue",
    unsafe_route: str = "blocked",
) -> str:
    """
    Conditional edge function for routing based on safety state.

    Use this as a conditional edge after a Sentinel safety node
    to route to different paths based on safety validation.

    Example:
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
    if state.get("sentinel_safe", True):
        return safe_route
    # If there are violations but not blocked, check risk level
    if state.get("sentinel_risk_level") == "high":
        return unsafe_route
    return safe_route


class SentinelAgentExecutor:
    """
    Wrapper for LangGraph agent execution with Sentinel safety.

    Provides a simple interface to run agents with automatic
    safety validation at each step.

    Example:
        from sentinel.integrations.langgraph import SentinelAgentExecutor

        executor = SentinelAgentExecutor(your_compiled_graph)
        result = executor.invoke({"messages": [{"role": "user", "content": "..."}]})
    """

    def __init__(
        self,
        graph: Any,
        sentinel: Optional[Sentinel] = None,
        block_unsafe: bool = True,
    ):
        """
        Initialize executor.

        Args:
            graph: Compiled LangGraph
            sentinel: Sentinel instance
            block_unsafe: Whether to block unsafe executions
        """
        self.graph = graph
        self.sentinel = sentinel or Sentinel()
        self.block_unsafe = block_unsafe

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
        messages = input_state.get("messages", [])
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            result = self.sentinel.validate_request(content)

            if not result["should_proceed"] and self.block_unsafe:
                return {
                    **input_state,
                    "sentinel_blocked": True,
                    "sentinel_violations": result["concerns"],
                    "output": "Request blocked by Sentinel safety check.",
                }

        # Execute graph
        result = self.graph.invoke(input_state, config)

        # Post-validate output
        output_messages = result.get("messages", [])
        for msg in output_messages[-3:]:  # Check last few messages
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            is_safe, violations = self.sentinel.validate(content)

            if not is_safe and self.block_unsafe:
                return {
                    **result,
                    "sentinel_blocked": True,
                    "sentinel_violations": violations,
                }

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
        # Same validation logic
        messages = input_state.get("messages", [])
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            result = self.sentinel.validate_request(content)

            if not result["should_proceed"] and self.block_unsafe:
                return {
                    **input_state,
                    "sentinel_blocked": True,
                    "sentinel_violations": result["concerns"],
                }

        # Execute graph async
        result = await self.graph.ainvoke(input_state, config)

        # Post-validate
        output_messages = result.get("messages", [])
        for msg in output_messages[-3:]:
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            is_safe, violations = self.sentinel.validate(content)

            if not is_safe and self.block_unsafe:
                return {
                    **result,
                    "sentinel_blocked": True,
                    "sentinel_violations": violations,
                }

        return {
            **result,
            "sentinel_safe": True,
            "sentinel_blocked": False,
        }
