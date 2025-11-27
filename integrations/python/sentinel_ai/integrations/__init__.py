"""
Integrations for Sentinel AI with popular frameworks.

Available integrations:
- huggingface: Hugging Face Transformers integration
- openai: OpenAI API wrapper
- langchain: LangChain callback and chain integration
"""

from typing import TYPE_CHECKING

# Lazy imports to avoid requiring all dependencies
if TYPE_CHECKING:
    from .huggingface import SentinelTransformersGuard
    from .openai_wrapper import SentinelOpenAI
    from .langchain_callback import SentinelCallback

__all__ = [
    "SentinelTransformersGuard",
    "SentinelOpenAI",
    "SentinelCallback",
]
