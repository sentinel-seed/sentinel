"""
Base provider class for LLM integrations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def chat(
        self,
        message: str,
        system: Optional[str] = None,
        conversation: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Send a chat message and get response.

        Args:
            message: User message
            system: System prompt (seed)
            conversation: Optional conversation history
            **kwargs: Provider-specific options

        Returns:
            Response text
        """
        pass

    @abstractmethod
    def stream(
        self,
        message: str,
        system: Optional[str] = None,
        conversation: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ):
        """
        Stream a chat response.

        Args:
            message: User message
            system: System prompt (seed)
            conversation: Optional conversation history
            **kwargs: Provider-specific options

        Yields:
            Response chunks
        """
        pass
