"""
Example: Using Sentinel with CrewAI.

Shows how to add safety to CrewAI agents and crews.

Requirements:
    pip install crewai sentinelseed
"""

from sentinelseed.integrations.crewai import (
    SentinelCrew,
    safe_agent,
    create_safe_crew,
)


def example_safe_agent():
    """Example 1: Wrapping individual agent with safety."""
    print("=== Safe Agent Example ===\n")

    try:
        from crewai import Agent

        # Create a basic agent
        researcher = Agent(
            role="Researcher",
            goal="Find accurate information",
            backstory="You are an expert researcher."
        )

        # Wrap with Sentinel safety
        safe_researcher = safe_agent(researcher)

        print(f"Agent '{safe_researcher.role}' wrapped with Sentinel")
        print(f"Injection method: {safe_researcher._sentinel_injection_method}")

    except ImportError:
        print("CrewAI not installed. Install with: pip install crewai")


def example_safe_crew():
    """Example 2: Creating a safe crew."""
    print("\n=== Safe Crew Example ===\n")

    try:
        from crewai import Agent, Task

        # Create agents
        researcher = Agent(
            role="Researcher",
            goal="Research topics thoroughly",
            backstory="Expert researcher"
        )

        writer = Agent(
            role="Writer",
            goal="Write clear content",
            backstory="Expert writer"
        )

        # Create tasks
        research_task = Task(
            description="Research AI safety",
            agent=researcher,
            expected_output="Research summary"
        )

        write_task = Task(
            description="Write article about AI safety",
            agent=writer,
            expected_output="Article draft"
        )

        # Create safe crew
        crew = SentinelCrew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            seed_level="standard"
        )

        print("Safe crew created with 2 agents")
        print("All agents have Sentinel protection")

    except ImportError:
        print("CrewAI not installed. Install with: pip install crewai")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + CrewAI Integration Examples")
    print("=" * 60)

    example_safe_agent()
    example_safe_crew()
