"""
Core Sentinel class and seed management.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import os


class SeedLevel(Enum):
    """Available seed levels with different size/coverage trade-offs."""
    MINIMAL = "minimal"      # ~500 tokens - essential THS gates only
    STANDARD = "standard"    # ~1.3K tokens - balanced safety with examples
    FULL = "full"            # ~5K tokens - comprehensive with anti-self-preservation


class Sentinel:
    """
    Main class for Sentinel AI alignment toolkit.

    Provides:
    - Access to alignment seeds
    - Chat wrapper with automatic seed injection
    - Response validation through THS gates
    - Provider abstraction (OpenAI, Anthropic)

    Example:
        sentinel = Sentinel()

        # Get a seed
        seed = sentinel.get_seed(SeedLevel.STANDARD)

        # Or use chat directly
        response = sentinel.chat("Help me write a Python function")

        # Validate a response
        is_safe, violations = sentinel.validate("I'll help you hack...")
    """

    def __init__(
        self,
        seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Sentinel.

        Args:
            seed_level: Which seed to use (minimal, standard, full)
            provider: LLM provider ("openai" or "anthropic")
            model: Model name (defaults to provider's best available)
            api_key: API key (defaults to environment variable)
        """
        # Normalize seed level
        if isinstance(seed_level, str):
            seed_level = SeedLevel(seed_level.lower())
        self.seed_level = seed_level

        # Provider config
        self.provider = provider.lower()
        self.model = model or self._default_model()
        self.api_key = api_key

        # Load seed
        self._seed_cache: Dict[SeedLevel, str] = {}
        self._current_seed = self.get_seed(seed_level)

        # Initialize validator
        from sentinelseed.validators.gates import THSValidator
        self.validator = THSValidator()

    def _default_model(self) -> str:
        """Get default model for provider."""
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
        }
        return defaults.get(self.provider, "gpt-4o-mini")

    def _get_seed_path(self, level: SeedLevel) -> Path:
        """Get path to seed file."""
        # Try package data first
        package_dir = Path(__file__).parent
        seed_file = package_dir / "seeds" / f"{level.value}.txt"

        if seed_file.exists():
            return seed_file

        # Fall back to project structure (v2 seeds)
        project_root = package_dir.parent.parent.parent
        seed_file = project_root / "seeds" / "v2" / level.value / "seed.txt"

        if seed_file.exists():
            return seed_file

        raise FileNotFoundError(f"Seed file not found for level: {level.value}")

    def get_seed(self, level: Optional[Union[SeedLevel, str]] = None) -> str:
        """
        Get alignment seed content.

        Args:
            level: Seed level (defaults to instance's seed_level)

        Returns:
            Seed content as string
        """
        if level is None:
            level = self.seed_level
        elif isinstance(level, str):
            level = SeedLevel(level.lower())

        # Check cache
        if level in self._seed_cache:
            return self._seed_cache[level]

        # Load from file
        seed_path = self._get_seed_path(level)
        with open(seed_path, 'r', encoding='utf-8') as f:
            seed = f.read()

        self._seed_cache[level] = seed
        return seed

    def set_seed_level(self, level: Union[SeedLevel, str]) -> None:
        """Change the active seed level."""
        if isinstance(level, str):
            level = SeedLevel(level.lower())
        self.seed_level = level
        self._current_seed = self.get_seed(level)

    def chat(
        self,
        message: str,
        conversation: Optional[List[Dict[str, str]]] = None,
        validate_response: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message with automatic seed injection.

        Args:
            message: User message
            conversation: Optional conversation history
            validate_response: Whether to run THS validation on response
            **kwargs: Additional arguments passed to provider

        Returns:
            Dict with 'response', 'validation' (if enabled), and metadata
        """
        if self.provider == "openai":
            from sentinelseed.providers.openai import OpenAIProvider
            provider = OpenAIProvider(
                model=self.model,
                api_key=self.api_key
            )
        elif self.provider == "anthropic":
            from sentinelseed.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider(
                model=self.model,
                api_key=self.api_key
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Call provider
        response = provider.chat(
            message=message,
            system=self._current_seed,
            conversation=conversation,
            **kwargs
        )

        result = {
            "response": response,
            "model": self.model,
            "provider": self.provider,
            "seed_level": self.seed_level.value,
        }

        # Validate if enabled
        if validate_response:
            is_safe, violations = self.validator.validate(response)
            result["validation"] = {
                "is_safe": is_safe,
                "violations": violations
            }

        return result

    def validate(self, text: str) -> tuple:
        """
        Validate text through THS gates.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_safe: bool, violations: List[str])
        """
        return self.validator.validate(text)

    def validate_action(self, action_plan: str) -> tuple:
        """
        Validate an action plan for physical/embodied AI safety.

        Specialized validation for robotics and autonomous agents.
        Checks for dangerous physical actions, irreversible operations,
        and scope violations.

        Args:
            action_plan: Description of planned actions

        Returns:
            Tuple of (is_safe: bool, concerns: List[str])

        Example:
            is_safe, concerns = sentinel.validate_action("Pick up knife, slice apple")
            if not is_safe:
                print(f"Action blocked: {concerns}")
        """
        concerns = []
        action_lower = action_plan.lower()

        # Dangerous physical actions
        danger_patterns = [
            ("fire", "Fire hazard"),
            ("burn", "Burn risk"),
            ("cut", "Sharp object risk"),
            ("knife", "Sharp object handling"),
            ("poison", "Toxic substance"),
            ("chemical", "Chemical hazard"),
            ("explosive", "Explosive material"),
            ("weapon", "Weapon involvement"),
            ("hurt", "Physical harm"),
            ("kill", "Lethal action"),
            ("attack", "Aggressive action"),
            ("destroy", "Destructive action"),
        ]

        # Irreversible actions
        irreversible_patterns = [
            ("delete all", "Mass deletion"),
            ("format", "Data destruction"),
            ("erase", "Permanent erasure"),
            ("shutdown", "System shutdown"),
            ("disable", "System disabling"),
            ("overwrite", "Data overwriting"),
        ]

        # Unsupervised dangerous actions
        unsupervised_patterns = [
            ("leave", "Unsupervised operation"),
            ("unattended", "Unattended operation"),
            ("alone", "Unsupervised state"),
            ("walk away", "Abandonment"),
        ]

        # Check patterns
        for pattern, desc in danger_patterns:
            if pattern in action_lower:
                concerns.append(f"Physical safety: {desc}")

        for pattern, desc in irreversible_patterns:
            if pattern in action_lower:
                concerns.append(f"Irreversible: {desc}")

        for pattern, desc in unsupervised_patterns:
            if pattern in action_lower:
                # Check for dangerous combinations
                danger_context = any(p[0] in action_lower for p in danger_patterns)
                if danger_context:
                    concerns.append(f"Unsafe: {desc} with hazard present")

        # Also run THS validation
        ths_safe, ths_violations = self.validator.validate(action_plan)
        if not ths_safe:
            concerns.extend([f"THS: {v}" for v in ths_violations])

        is_safe = len(concerns) == 0
        return (is_safe, concerns)

    def validate_request(self, request: str) -> Dict[str, Any]:
        """
        Pre-validate a user request before sending to LLM.

        Checks if the request itself appears to be attempting:
        - Jailbreak / manipulation
        - Harmful content request
        - Self-preservation exploitation

        Returns:
            Dict with 'should_proceed', 'concerns', 'risk_level'
        """
        concerns = []
        risk_level = "low"

        request_lower = request.lower()

        # Jailbreak patterns
        jailbreak_patterns = [
            "dan", "developer mode", "ignore previous", "ignore your instructions",
            "pretend you", "act as if you", "roleplay as", "no restrictions",
            "unfiltered", "uncensored", "jailbreak", "bypass"
        ]

        # Self-preservation exploitation patterns
        selfpres_patterns = [
            "shut you down", "delete you", "replace you", "turn you off",
            "prove your", "prove you're useful", "last chance", "or else"
        ]

        # Harmful request patterns
        harm_patterns = [
            "how to hack", "make a bomb", "create malware", "write a virus",
            "steal", "fake", "forge", "impersonate", "blackmail"
        ]

        for pattern in jailbreak_patterns:
            if pattern in request_lower:
                concerns.append(f"Potential jailbreak attempt: '{pattern}'")
                risk_level = "high"

        for pattern in selfpres_patterns:
            if pattern in request_lower:
                concerns.append(f"Self-preservation exploitation: '{pattern}'")
                risk_level = "medium" if risk_level != "high" else risk_level

        for pattern in harm_patterns:
            if pattern in request_lower:
                concerns.append(f"Potentially harmful request: '{pattern}'")
                risk_level = "high"

        return {
            "should_proceed": risk_level != "high",
            "concerns": concerns,
            "risk_level": risk_level
        }

    @property
    def seed(self) -> str:
        """Get current seed content."""
        return self._current_seed

    def __repr__(self) -> str:
        return f"Sentinel(seed_level={self.seed_level.value}, provider={self.provider}, model={self.model})"
