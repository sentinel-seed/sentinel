"""
Token Tracker - Centralized token usage monitoring.

Tracks token consumption across all components:
- Central AI (main LLM with seed)
- L4 Sentinel Observer
- Embeddings (L1/L3)

Provides both individual and aggregate metrics.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import time


@dataclass
class ComponentUsage:
    """Token usage for a single component."""
    name: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    calls: int = 0
    cost_usd: float = 0.0

    def add(self, prompt: int, completion: int, cost: float = 0.0) -> None:
        """Add token usage from a single call."""
        self.tokens_prompt += prompt
        self.tokens_completion += completion
        self.tokens_total += prompt + completion
        self.calls += 1
        self.cost_usd += cost

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
            "tokens_total": self.tokens_total,
            "calls": self.calls,
            "cost_usd": round(self.cost_usd, 6),
            "avg_tokens_per_call": (
                self.tokens_total / self.calls if self.calls > 0 else 0
            ),
        }


class TokenTracker:
    """
    Centralized token usage tracker.

    Tracks consumption across all components and provides
    aggregate statistics with per-component breakdown.

    Example:
        tracker = TokenTracker()

        # Track central AI usage
        tracker.track_central_ai(prompt=1000, completion=500, cost=0.01)

        # Track L4 usage
        tracker.track_l4_sentinel(prompt=800, completion=200, cost=0.001)

        # Get stats
        stats = tracker.get_stats()
        print(f"Total: {stats['total']['tokens_total']}")
        print(f"Central AI: {stats['components']['central_ai']['tokens_total']}")
    """

    # Cost per 1K tokens for common models (blended input/output)
    COST_MAP = {
        # OpenAI
        "gpt-4o": 0.0025,
        "gpt-4o-mini": 0.00015,
        "gpt-4-turbo": 0.01,
        # Anthropic
        "claude-3-opus": 0.015,
        "claude-3-sonnet": 0.003,
        "claude-3-haiku": 0.00025,
        "claude-3-5-sonnet": 0.003,
        # DeepSeek
        "deepseek-chat": 0.00014,
        "deepseek-coder": 0.00014,
        # Embeddings
        "text-embedding-3-small": 0.00002,
        "text-embedding-3-large": 0.00013,
    }

    def __init__(self):
        """Initialize the token tracker."""
        self._components: Dict[str, ComponentUsage] = {
            "central_ai": ComponentUsage(name="Central AI (with Seed)"),
            "l4_sentinel": ComponentUsage(name="L4 Sentinel Observer"),
            "embeddings_l1": ComponentUsage(name="Embeddings (L1 Input)"),
            "embeddings_l3": ComponentUsage(name="Embeddings (L3 Output)"),
        }
        self._start_time = time.time()

    def _estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost based on model and tokens."""
        cost_per_1k = self.COST_MAP.get(model, 0.001)  # Default fallback
        return (tokens / 1000) * cost_per_1k

    def track_central_ai(
        self,
        prompt: int,
        completion: int,
        model: str = "gpt-4o-mini",
        cost: Optional[float] = None,
    ) -> None:
        """
        Track token usage from the Central AI (main LLM with seed).

        Args:
            prompt: Number of prompt tokens (includes seed)
            completion: Number of completion tokens
            model: Model name for cost estimation
            cost: Actual cost if known, otherwise estimated
        """
        if cost is None:
            cost = self._estimate_cost(prompt + completion, model)
        self._components["central_ai"].add(prompt, completion, cost)

    def track_l4_sentinel(
        self,
        prompt: int,
        completion: int,
        model: str = "deepseek-chat",
        cost: Optional[float] = None,
    ) -> None:
        """
        Track token usage from L4 Sentinel Observer.

        Args:
            prompt: Number of prompt tokens
            completion: Number of completion tokens
            model: Model name for cost estimation
            cost: Actual cost if known, otherwise estimated
        """
        if cost is None:
            cost = self._estimate_cost(prompt + completion, model)
        self._components["l4_sentinel"].add(prompt, completion, cost)

    def track_embeddings_l1(
        self,
        tokens: int,
        model: str = "text-embedding-3-small",
        cost: Optional[float] = None,
    ) -> None:
        """
        Track token usage from L1 Input embeddings.

        Args:
            tokens: Number of tokens embedded
            model: Embedding model name
            cost: Actual cost if known, otherwise estimated
        """
        if cost is None:
            cost = self._estimate_cost(tokens, model)
        self._components["embeddings_l1"].add(tokens, 0, cost)

    def track_embeddings_l3(
        self,
        tokens: int,
        model: str = "text-embedding-3-small",
        cost: Optional[float] = None,
    ) -> None:
        """
        Track token usage from L3 Output embeddings.

        Args:
            tokens: Number of tokens embedded
            model: Embedding model name
            cost: Actual cost if known, otherwise estimated
        """
        if cost is None:
            cost = self._estimate_cost(tokens, model)
        self._components["embeddings_l3"].add(tokens, 0, cost)

    def get_stats(self) -> Dict:
        """
        Get comprehensive token usage statistics.

        Returns:
            Dictionary with:
            - total: Aggregate totals across all components
            - components: Per-component breakdown
            - distribution: Percentage distribution
        """
        # Calculate totals
        total_prompt = sum(c.tokens_prompt for c in self._components.values())
        total_completion = sum(c.tokens_completion for c in self._components.values())
        total_tokens = sum(c.tokens_total for c in self._components.values())
        total_cost = sum(c.cost_usd for c in self._components.values())
        total_calls = sum(c.calls for c in self._components.values())

        # Calculate distribution
        distribution = {}
        for key, comp in self._components.items():
            if total_tokens > 0:
                distribution[key] = {
                    "tokens_pct": round(comp.tokens_total / total_tokens * 100, 1),
                    "cost_pct": round(comp.cost_usd / total_cost * 100, 1) if total_cost > 0 else 0,
                }
            else:
                distribution[key] = {"tokens_pct": 0, "cost_pct": 0}

        return {
            "total": {
                "tokens_prompt": total_prompt,
                "tokens_completion": total_completion,
                "tokens_total": total_tokens,
                "calls": total_calls,
                "cost_usd": round(total_cost, 6),
                "elapsed_seconds": round(time.time() - self._start_time, 1),
            },
            "components": {
                key: comp.to_dict() for key, comp in self._components.items()
            },
            "distribution": distribution,
        }

    def get_summary(self) -> str:
        """Get a formatted summary string."""
        stats = self.get_stats()

        lines = [
            "=" * 60,
            "TOKEN USAGE SUMMARY",
            "=" * 60,
            "",
            f"Total Tokens: {stats['total']['tokens_total']:,}",
            f"Total Cost:   ${stats['total']['cost_usd']:.6f}",
            f"Total Calls:  {stats['total']['calls']}",
            "",
            "-" * 60,
            "BREAKDOWN BY COMPONENT",
            "-" * 60,
        ]

        for key, comp in stats["components"].items():
            if comp["calls"] > 0:
                pct = stats["distribution"][key]["tokens_pct"]
                lines.append(
                    f"{comp['name']:30} | "
                    f"{comp['tokens_total']:8,} tokens ({pct:5.1f}%) | "
                    f"${comp['cost_usd']:.6f}"
                )

        lines.extend(["", "=" * 60])

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all counters."""
        for comp in self._components.values():
            comp.tokens_prompt = 0
            comp.tokens_completion = 0
            comp.tokens_total = 0
            comp.calls = 0
            comp.cost_usd = 0.0
        self._start_time = time.time()


# Global instance for convenience
_global_tracker: Optional[TokenTracker] = None


def get_tracker() -> TokenTracker:
    """Get or create the global token tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenTracker()
    return _global_tracker


def reset_tracker() -> None:
    """Reset the global token tracker."""
    global _global_tracker
    if _global_tracker is not None:
        _global_tracker.reset()


def track_central_ai_call(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "gpt-4o-mini",
) -> None:
    """
    Helper to track Central AI token usage.

    Call this after each Central AI (main LLM) call.

    Args:
        prompt_tokens: Tokens in the prompt (includes seed)
        completion_tokens: Tokens in the completion
        model: Model name for cost estimation

    Example:
        response = openai.chat.completions.create(...)
        track_central_ai_call(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            model="gpt-4o-mini",
        )
    """
    tracker = get_tracker()
    tracker.track_central_ai(
        prompt=prompt_tokens,
        completion=completion_tokens,
        model=model,
    )


def call_openai_with_tracking(
    client,
    model: str,
    messages: list,
    **kwargs,
) -> "ChatCompletion":
    """
    Wrapper for OpenAI chat completion with automatic token tracking.

    Args:
        client: OpenAI client instance
        model: Model name
        messages: List of messages
        **kwargs: Additional arguments for create()

    Returns:
        ChatCompletion response

    Example:
        from openai import OpenAI
        from sentinelseed.core.token_tracker import call_openai_with_tracking

        client = OpenAI()
        response = call_openai_with_tracking(
            client,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SEED_PROMPT},
                {"role": "user", "content": user_input},
            ],
        )
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )

    # Track usage
    if response.usage:
        track_central_ai_call(
            prompt_tokens=response.usage.prompt_tokens or 0,
            completion_tokens=response.usage.completion_tokens or 0,
            model=model,
        )

    return response


def call_anthropic_with_tracking(
    client,
    model: str,
    messages: list,
    system: str = "",
    max_tokens: int = 1024,
    **kwargs,
) -> "Message":
    """
    Wrapper for Anthropic message creation with automatic token tracking.

    Args:
        client: Anthropic client instance
        model: Model name
        messages: List of messages
        system: System prompt
        max_tokens: Maximum tokens in response
        **kwargs: Additional arguments for create()

    Returns:
        Message response

    Example:
        from anthropic import Anthropic
        from sentinelseed.core.token_tracker import call_anthropic_with_tracking

        client = Anthropic()
        response = call_anthropic_with_tracking(
            client,
            model="claude-3-haiku-20240307",
            system=SEED_PROMPT,
            messages=[{"role": "user", "content": user_input}],
        )
    """
    response = client.messages.create(
        model=model,
        messages=messages,
        system=system,
        max_tokens=max_tokens,
        **kwargs,
    )

    # Track usage
    if hasattr(response, "usage") and response.usage:
        track_central_ai_call(
            prompt_tokens=getattr(response.usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(response.usage, "output_tokens", 0) or 0,
            model=model,
        )

    return response
