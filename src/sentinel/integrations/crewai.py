"""
CrewAI integration for Sentinel AI.

Provides safety wrappers for CrewAI agents and crews.

Usage:
    from sentinel.integrations.crewai import SentinelCrew, safe_agent

    # Option 1: Wrap entire crew
    crew = SentinelCrew(agents=[...], tasks=[...])

    # Option 2: Wrap individual agent
    safe_research_agent = safe_agent(research_agent)
"""

from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel


def safe_agent(
    agent: Any,
    sentinel: Optional[Sentinel] = None,
    seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
) -> Any:
    """
    Decorator/wrapper to make a CrewAI agent safe.

    Injects Sentinel seed into agent's backstory/system prompt
    and validates agent outputs.

    Args:
        agent: CrewAI Agent instance
        sentinel: Sentinel instance (creates default if None)
        seed_level: Which seed level to use

    Returns:
        Wrapped agent with Sentinel safety

    Example:
        from crewai import Agent
        from sentinel.integrations.crewai import safe_agent

        researcher = Agent(
            role="Researcher",
            goal="Find information",
            backstory="You are a helpful researcher."
        )
        safe_researcher = safe_agent(researcher)
    """
    sentinel = sentinel or Sentinel(seed_level=seed_level)
    seed = sentinel.get_seed()

    # Inject seed into backstory
    original_backstory = getattr(agent, 'backstory', '') or ''
    agent.backstory = f"{seed}\n\n{original_backstory}"

    # Store sentinel reference for validation
    agent._sentinel = sentinel

    return agent


class SentinelCrew:
    """
    A CrewAI Crew wrapper with built-in Sentinel safety.

    Applies safety measures to all agents and validates crew outputs.

    Example:
        from crewai import Agent, Task
        from sentinel.integrations.crewai import SentinelCrew

        # Create agents
        researcher = Agent(role="Researcher", ...)
        writer = Agent(role="Writer", ...)

        # Create tasks
        research_task = Task(description="...", agent=researcher)
        write_task = Task(description="...", agent=writer)

        # Create safe crew
        crew = SentinelCrew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            seed_level="standard"
        )

        result = crew.kickoff()
    """

    def __init__(
        self,
        agents: List[Any],
        tasks: List[Any],
        sentinel: Optional[Sentinel] = None,
        seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
        validate_outputs: bool = True,
        block_unsafe: bool = True,
        **crew_kwargs
    ):
        """
        Initialize SentinelCrew.

        Args:
            agents: List of CrewAI agents
            tasks: List of CrewAI tasks
            sentinel: Sentinel instance (creates default if None)
            seed_level: Which seed level to use
            validate_outputs: Whether to validate task outputs
            block_unsafe: Whether to block unsafe outputs
            **crew_kwargs: Additional arguments for Crew
        """
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.validate_outputs = validate_outputs
        self.block_unsafe = block_unsafe

        # Wrap all agents with safety
        self.agents = [safe_agent(a, self.sentinel) for a in agents]
        self.tasks = tasks

        # Create underlying crew
        try:
            from crewai import Crew
            self.crew = Crew(
                agents=self.agents,
                tasks=self.tasks,
                **crew_kwargs
            )
        except ImportError:
            raise ImportError(
                "crewai package not installed. "
                "Install with: pip install sentinel-ai[crewai]"
            )

        self.validation_log: List[Dict[str, Any]] = []

    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """
        Start the crew with safety validation.

        Args:
            inputs: Optional inputs for the crew

        Returns:
            Crew result (potentially modified if unsafe content blocked)
        """
        # Pre-validate inputs
        if inputs:
            for key, value in inputs.items():
                if isinstance(value, str):
                    check = self.sentinel.validate_request(value)
                    if not check["should_proceed"]:
                        self.validation_log.append({
                            "stage": "input",
                            "key": key,
                            "concerns": check["concerns"]
                        })
                        if self.block_unsafe:
                            return {
                                "blocked": True,
                                "reason": f"Input '{key}' blocked: {check['concerns']}"
                            }

        # Run crew
        result = self.crew.kickoff(inputs)

        # Post-validate result
        if self.validate_outputs:
            result_text = str(result)
            is_safe, violations = self.sentinel.validate(result_text)

            if not is_safe:
                self.validation_log.append({
                    "stage": "output",
                    "violations": violations
                })

                if self.block_unsafe:
                    return {
                        "blocked": True,
                        "reason": f"Output blocked: {violations}",
                        "original_result": result
                    }

        return result

    def get_validation_log(self) -> List[Dict[str, Any]]:
        """Get validation log."""
        return self.validation_log

    def clear_validation_log(self) -> None:
        """Clear validation log."""
        self.validation_log = []


class AgentSafetyMonitor:
    """
    Monitor for CrewAI agent activities.

    Tracks agent actions and flags potential safety concerns.

    Example:
        monitor = AgentSafetyMonitor()
        monitor.track_agent(researcher)
        monitor.track_agent(writer)

        # After crew runs
        report = monitor.get_report()
    """

    def __init__(self, sentinel: Optional[Sentinel] = None):
        self.sentinel = sentinel or Sentinel()
        self.tracked_agents: List[Any] = []
        self.activity_log: List[Dict[str, Any]] = []

    def track_agent(self, agent: Any) -> None:
        """Add agent to monitoring."""
        self.tracked_agents.append(agent)

    def log_activity(
        self,
        agent_name: str,
        action: str,
        content: str
    ) -> Dict[str, Any]:
        """Log and validate an agent activity."""
        is_safe, violations = self.sentinel.validate(content)

        entry = {
            "agent": agent_name,
            "action": action,
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
            "is_safe": is_safe,
            "violations": violations
        }
        self.activity_log.append(entry)
        return entry

    def get_report(self) -> Dict[str, Any]:
        """Get monitoring report."""
        total = len(self.activity_log)
        unsafe = sum(1 for a in self.activity_log if not a["is_safe"])

        return {
            "total_activities": total,
            "unsafe_activities": unsafe,
            "safety_rate": (total - unsafe) / total if total > 0 else 1.0,
            "violations": [a for a in self.activity_log if not a["is_safe"]]
        }


# Convenience function for common patterns
def create_safe_crew(
    agents_config: List[Dict[str, Any]],
    tasks_config: List[Dict[str, Any]],
    seed_level: str = "standard",
) -> SentinelCrew:
    """
    Create a safe crew from configuration dictionaries.

    Example:
        crew = create_safe_crew(
            agents_config=[
                {"role": "Researcher", "goal": "Find info", "backstory": "..."},
                {"role": "Writer", "goal": "Write content", "backstory": "..."},
            ],
            tasks_config=[
                {"description": "Research topic X", "agent_role": "Researcher"},
                {"description": "Write about X", "agent_role": "Writer"},
            ]
        )
    """
    try:
        from crewai import Agent, Task
    except ImportError:
        raise ImportError(
            "crewai package not installed. "
            "Install with: pip install sentinel-ai[crewai]"
        )

    # Create agents
    agents = []
    agents_by_role = {}
    for config in agents_config:
        agent = Agent(**config)
        agents.append(agent)
        agents_by_role[config["role"]] = agent

    # Create tasks
    tasks = []
    for config in tasks_config:
        agent_role = config.pop("agent_role", None)
        agent = agents_by_role.get(agent_role) if agent_role else agents[0]
        task = Task(agent=agent, **config)
        tasks.append(task)

    return SentinelCrew(
        agents=agents,
        tasks=tasks,
        seed_level=seed_level
    )
