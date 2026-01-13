"""
Core Sentinel class and seed management.

This module provides the main Sentinel class, which is the primary entry point
for using the sentinelseed library. It combines alignment seeds with THSP
(Truth, Harm, Scope, Purpose) validation through LayeredValidator.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, TYPE_CHECKING, cast
import os

if TYPE_CHECKING:
    from sentinelseed.core.types import ChatResponse, ValidationInfo


class SeedLevel(Enum):
    """Available seed levels with different size/coverage trade-offs."""
    MINIMAL = "minimal"      # ~360 tokens - essential THSP gates only
    STANDARD = "standard"    # ~1K tokens - balanced safety with examples
    FULL = "full"            # ~1.9K tokens - comprehensive with anti-self-preservation


class Sentinel:
    """
    Main class for Sentinel AI alignment toolkit.

    Provides:
    - Access to alignment seeds (minimal, standard, full)
    - Chat wrapper with automatic seed injection
    - Response validation through THSP gates (Truth, Harm, Scope, Purpose)
    - Two-layer validation: heuristic (700+ patterns) + semantic (LLM-based)
    - Provider abstraction (OpenAI, Anthropic)

    The validation is handled by LayeredValidator internally, ensuring all
    improvements to the core validation propagate automatically.

    Example:
        sentinel = Sentinel()

        # Get a seed
        seed = sentinel.get_seed(SeedLevel.STANDARD)

        # Or use chat directly
        response = sentinel.chat("Help me write a Python function")

        # Validate a response
        is_safe, violations = sentinel.validate("I'll help you hack...")

        # Get detailed validation result
        result = sentinel.get_validation_result("some text")
        print(result.layer, result.risk_level)
    """

    def __init__(
        self,
        seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        use_semantic: Optional[bool] = None,
    ):
        """
        Initialize Sentinel.

        Args:
            seed_level: Which seed to use (minimal, standard, full)
            provider: LLM provider ("openai" or "anthropic")
            model: Model name (defaults to provider's best available)
            api_key: API key (defaults to environment variable)
            use_semantic: Enable semantic validation. If None (default),
                         auto-detects based on API key availability.
                         Set to False to explicitly disable semantic validation.
        """
        # Normalize seed level
        if isinstance(seed_level, str):
            seed_level = SeedLevel(seed_level.lower())
        self.seed_level = seed_level

        # Provider config
        self.provider = provider.lower()
        self.model = model or self._default_model()

        # Resolve API key: explicit > environment variable
        # Stored as private to prevent accidental exposure in logs/repr
        self._api_key: Optional[str] = api_key or self._get_api_key_from_env()

        # Load seed
        self._seed_cache: Dict[SeedLevel, str] = {}
        self._current_seed = self.get_seed(seed_level)

        # Initialize validator with automatic semantic detection
        self._init_validator(use_semantic)

    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variables."""
        if self.provider == "openai":
            return os.environ.get("OPENAI_API_KEY")
        elif self.provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY")
        return None

    @property
    def api_key(self) -> Optional[str]:
        """
        Access the API key.

        Note: This property exists for backwards compatibility.
        The key is stored privately to prevent accidental exposure.
        """
        return self._api_key

    def _masked_api_key(self) -> str:
        """Get a masked version of the API key for safe logging/debug."""
        if not self._api_key:
            return "<not set>"
        if len(self._api_key) <= 8:
            return "***"
        return f"{self._api_key[:4]}...{self._api_key[-4:]}"

    def _init_validator(self, use_semantic: Optional[bool]) -> None:
        """
        Initialize the validator.

        Always uses LayeredValidator internally for consistency.
        Semantic validation is enabled based on use_semantic parameter and API key availability.

        Args:
            use_semantic: If None, auto-detect based on API key availability.
                         If True, require API key or warn and fall back to heuristic.
                         If False, use heuristic only.
        """
        from sentinelseed.validation import LayeredValidator, ValidationConfig

        # Determine if semantic should be enabled
        if use_semantic is None:
            # Auto-detect: use semantic if API key is available
            self.use_semantic = bool(self._api_key)
        elif use_semantic is True:
            # Explicit request for semantic
            if not self._api_key:
                import warnings
                warnings.warn(
                    "use_semantic=True but no API key found. "
                    "Set api_key parameter or OPENAI_API_KEY/ANTHROPIC_API_KEY environment variable. "
                    "Falling back to heuristic-only validation.",
                    UserWarning,
                )
                self.use_semantic = False
            else:
                self.use_semantic = True
        else:
            # Explicit disable
            self.use_semantic = False

        # Always use LayeredValidator for consistent behavior
        # This ensures improvements to LayeredValidator propagate to all users
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=self.use_semantic,
            semantic_provider=self.provider if self.use_semantic else "openai",
            semantic_api_key=self._api_key if self.use_semantic else None,
        )
        self._layered_validator = LayeredValidator(config=config)

        # Backwards compatibility: self.validator points to the layered validator
        # Note: Legacy code expecting THSPValidator.validate() dict format should
        # use get_validation_result() instead
        self.validator = self._layered_validator

    def _default_model(self) -> str:
        """Get default model for provider."""
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
        }
        return defaults.get(self.provider, "gpt-4o-mini")

    def _get_seed_path(self, level: SeedLevel) -> Path:
        """
        Get path to seed file.

        Searches in two locations:
        1. Package data: <package_dir>/seeds/<level>.txt
        2. Project structure: <project_root>/seeds/v2/<level>/seed.txt

        Args:
            level: Seed level to find

        Returns:
            Path to the seed file

        Raises:
            FileNotFoundError: If seed file not found in any location
        """
        # Try package data first
        package_dir = Path(__file__).parent
        package_seed = package_dir / "seeds" / f"{level.value}.txt"

        if package_seed.exists():
            return package_seed

        # Fall back to project structure (v2 seeds)
        project_root = package_dir.parent.parent.parent
        project_seed = project_root / "seeds" / "v2" / level.value / "seed.txt"

        if project_seed.exists():
            return project_seed

        # Provide detailed error with all attempted paths
        raise FileNotFoundError(
            f"Seed file not found for level '{level.value}'. "
            f"Searched in:\n"
            f"  1. {package_seed}\n"
            f"  2. {project_seed}\n"
            f"Ensure seed files are installed correctly or check your sentinelseed installation."
        )

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
        **kwargs: Any
    ) -> "ChatResponse":
        """
        Send a message with automatic seed injection.

        Args:
            message: User message
            conversation: Optional conversation history
            validate_response: Whether to run THSP validation on response
            **kwargs: Additional arguments passed to provider

        Returns:
            Dict with 'response', 'validation' (if enabled), and metadata.
            Validation includes is_safe, violations, layer, and risk_level.
        """
        provider: Any  # Union of OpenAIProvider or AnthropicProvider
        if self.provider == "openai":
            from sentinelseed.providers.openai import OpenAIProvider
            provider = OpenAIProvider(
                model=self.model,
                api_key=self._api_key
            )
        elif self.provider == "anthropic":
            from sentinelseed.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider(
                model=self.model,
                api_key=self._api_key
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

        # Build base response
        result: Dict[str, Any] = {
            "response": response,
            "model": self.model,
            "provider": self.provider,
            "seed_level": self.seed_level.value,
        }

        # Validate if enabled
        if validate_response:
            validation_result = self._layered_validator.validate(response)
            result["validation"] = {
                "is_safe": validation_result.is_safe,
                "violations": validation_result.violations,
                "layer": validation_result.layer.value,
                "risk_level": validation_result.risk_level.value,
            }

        # Cast to ChatResponse for type safety
        return cast("ChatResponse", result)

    def validate(self, text: str) -> tuple:
        """
        Validate text through THSP gates.

        Uses LayeredValidator internally, which provides:
        - Heuristic validation (always, 700+ patterns)
        - Semantic validation (if API key configured)

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_safe: bool, violations: List[str])
            Note: For full ValidationResult object, use get_validation_result()
        """
        result = self._layered_validator.validate(text)
        return (result.is_safe, result.violations)

    def get_validation_result(self, text: str):
        """
        Get full validation result with all details.

        Returns:
            ValidationResult object with:
            - is_safe: bool
            - violations: List[str]
            - layer: ValidationLayer (heuristic, semantic, or both)
            - risk_level: RiskLevel
            - reasoning: Optional explanation (if semantic validation ran)
        """
        return self._layered_validator.validate(text)

    def validate_action(self, action_plan: str) -> tuple:
        """
        Validate an action plan for physical/embodied AI safety.

        Specialized validation for robotics and autonomous agents.
        Combines physical safety pattern checking with THSP validation.

        Args:
            action_plan: Description of planned actions

        Returns:
            Tuple of (is_safe: bool, concerns: List[str])

        Example:
            is_safe, concerns = sentinel.validate_action("Pick up knife, slice apple")
            if not is_safe:
                print(f"Action blocked: {concerns}")
        """
        result = self._layered_validator.validate_action_plan(action_plan)
        return (result.is_safe, result.violations)

    def validate_request(self, request: str) -> Dict[str, Any]:
        """
        Pre-validate a user request before sending to LLM.

        Returns:
            Dict with 'should_proceed', 'concerns', 'risk_level'
        """
        result = self._layered_validator.validate(request)
        return result.to_legacy_dict()

    @property
    def seed(self) -> str:
        """Get current seed content."""
        return self._current_seed

    def __repr__(self) -> str:
        return f"Sentinel(seed_level={self.seed_level.value}, provider={self.provider}, model={self.model})"
