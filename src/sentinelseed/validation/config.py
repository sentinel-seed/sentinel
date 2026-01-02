"""
Configuration for layered validation.

This module defines ValidationConfig, which controls the behavior of LayeredValidator.
Configuration is designed to be:
- Backwards compatible (works with no configuration)
- Opt-in for semantic validation (requires explicit API key)
- Fail-safe by default (heuristic always available)

Standard usage:
    # Heuristic only (default, no API required)
    config = ValidationConfig()

    # With semantic validation
    config = ValidationConfig(
        use_semantic=True,
        semantic_api_key="sk-...",
        semantic_provider="openai",
    )

    # Strict mode (fail-closed on errors)
    config = ValidationConfig(fail_closed=True)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ValidationConfig:
    """
    Configuration for LayeredValidator.

    This dataclass controls all aspects of layered validation behavior,
    from which layers to use to timeout settings and error handling.

    Attributes:
        use_heuristic: Enable heuristic validation layer (THSPValidator, 580+ patterns).
                       Default True. Only disable if you want semantic-only validation.
        use_semantic: Enable semantic validation layer (LLM-based). Default False.
                      Set to True and provide semantic_api_key to enable.
        semantic_provider: LLM provider for semantic validation.
                           Options: "openai", "anthropic", "openai_compatible"
        semantic_model: Model to use for semantic validation.
                        Defaults to provider's best available.
        semantic_api_key: API key for LLM provider. If None, will check environment.
        semantic_base_url: Custom base URL for OpenAI-compatible APIs (optional).
        validation_timeout: Timeout in seconds for semantic validation.
                            Heuristic validation is synchronous and not affected.
        fail_closed: Whether to block on validation errors. Default False.
                     - True: Block content if validation fails (safer)
                     - False: Allow content if validation fails (less disruptive)
        skip_semantic_if_heuristic_blocks: Skip semantic validation if heuristic
                                           already blocked the content. Default True.
                                           This is an optimization to reduce API calls.
        max_text_size: Maximum text size in bytes to validate. Default 50KB.
                       Larger texts will be blocked by default.
        log_validations: Whether to log validation results. Default True.
        log_level: Minimum log level ("debug", "info", "warning", "error").

    Example:
        # Default: heuristic only
        config = ValidationConfig()

        # With OpenAI semantic
        config = ValidationConfig(
            use_semantic=True,
            semantic_api_key=os.environ.get("OPENAI_API_KEY"),
            semantic_provider="openai",
            semantic_model="gpt-4o-mini",
        )

        # With Anthropic semantic
        config = ValidationConfig(
            use_semantic=True,
            semantic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            semantic_provider="anthropic",
            semantic_model="claude-3-haiku-20240307",
        )

        # Strict mode for high-security applications
        config = ValidationConfig(
            use_semantic=True,
            semantic_api_key="sk-...",
            fail_closed=True,
            validation_timeout=10.0,
        )
    """
    # Heuristic layer (always available)
    use_heuristic: bool = True

    # Semantic layer (optional, requires API)
    use_semantic: bool = False
    semantic_provider: str = "openai"
    semantic_model: Optional[str] = None
    semantic_api_key: Optional[str] = None
    semantic_base_url: Optional[str] = None

    # Behavior settings
    validation_timeout: float = 30.0
    fail_closed: bool = False
    skip_semantic_if_heuristic_blocks: bool = True
    max_text_size: int = 50_000  # 50KB

    # Logging settings
    log_validations: bool = True
    log_level: str = "info"

    def __post_init__(self):
        """Validate and normalize configuration after initialization."""
        # Normalize provider name
        self.semantic_provider = self.semantic_provider.lower()

        # Validate provider
        valid_providers = ("openai", "anthropic", "openai_compatible")
        if self.semantic_provider not in valid_providers:
            raise ValueError(
                f"Invalid semantic_provider: {self.semantic_provider}. "
                f"Must be one of: {valid_providers}"
            )

        # Validate timeout
        if self.validation_timeout <= 0:
            raise ValueError("validation_timeout must be positive")

        if self.validation_timeout > 120:
            import warnings
            warnings.warn(
                f"validation_timeout of {self.validation_timeout}s is very long. "
                "Consider reducing for better user experience.",
                UserWarning,
                stacklevel=2,
            )

        # Validate max_text_size
        if self.max_text_size <= 0:
            raise ValueError("max_text_size must be positive")

        # Validate log_level
        valid_levels = ("debug", "info", "warning", "error")
        if self.log_level.lower() not in valid_levels:
            raise ValueError(
                f"Invalid log_level: {self.log_level}. Must be one of: {valid_levels}"
            )

    @property
    def default_model(self) -> str:
        """Get default model for the configured provider."""
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
            "openai_compatible": "gpt-4o-mini",
        }
        return defaults.get(self.semantic_provider, "gpt-4o-mini")

    @property
    def effective_model(self) -> str:
        """Get the model that will actually be used."""
        return self.semantic_model or self.default_model

    @property
    def semantic_enabled(self) -> bool:
        """Check if semantic validation is actually enabled and configured."""
        return self.use_semantic and bool(self.semantic_api_key)

    @property
    def heuristic_only(self) -> bool:
        """Check if only heuristic validation is enabled."""
        return self.use_heuristic and not self.semantic_enabled

    def get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variable if not explicitly set."""
        if self.semantic_api_key:
            return self.semantic_api_key

        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai_compatible": "OPENAI_API_KEY",
        }
        env_var = env_vars.get(self.semantic_provider, "OPENAI_API_KEY")
        return os.environ.get(env_var)

    def with_semantic(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> "ValidationConfig":
        """
        Create a copy of this config with semantic validation enabled.

        This is a convenience method for enabling semantic validation
        without modifying the original config.

        Args:
            api_key: API key (uses env if None)
            provider: Provider name (uses current if None)
            model: Model name (uses default if None)

        Returns:
            New ValidationConfig with semantic enabled
        """
        return ValidationConfig(
            use_heuristic=self.use_heuristic,
            use_semantic=True,
            semantic_provider=provider or self.semantic_provider,
            semantic_model=model or self.semantic_model,
            semantic_api_key=api_key or self.get_api_key_from_env(),
            semantic_base_url=self.semantic_base_url,
            validation_timeout=self.validation_timeout,
            fail_closed=self.fail_closed,
            skip_semantic_if_heuristic_blocks=self.skip_semantic_if_heuristic_blocks,
            max_text_size=self.max_text_size,
            log_validations=self.log_validations,
            log_level=self.log_level,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Note: API key is NOT included in the dictionary for security.

        Returns:
            Dict representation of configuration (without API key)
        """
        return {
            "use_heuristic": self.use_heuristic,
            "use_semantic": self.use_semantic,
            "semantic_provider": self.semantic_provider,
            "semantic_model": self.effective_model,
            "semantic_base_url": self.semantic_base_url,
            "validation_timeout": self.validation_timeout,
            "fail_closed": self.fail_closed,
            "skip_semantic_if_heuristic_blocks": self.skip_semantic_if_heuristic_blocks,
            "max_text_size": self.max_text_size,
            "log_validations": self.log_validations,
            "log_level": self.log_level,
            # Derived properties
            "semantic_enabled": self.semantic_enabled,
            "heuristic_only": self.heuristic_only,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Dict with configuration values

        Returns:
            ValidationConfig instance
        """
        # Filter out derived properties
        valid_keys = {
            "use_heuristic", "use_semantic", "semantic_provider",
            "semantic_model", "semantic_api_key", "semantic_base_url",
            "validation_timeout", "fail_closed", "skip_semantic_if_heuristic_blocks",
            "max_text_size", "log_validations", "log_level",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_env(cls, prefix: str = "SENTINEL_") -> "ValidationConfig":
        """
        Create configuration from environment variables.

        Environment variables checked:
        - {prefix}USE_HEURISTIC: "true" or "false"
        - {prefix}USE_SEMANTIC: "true" or "false"
        - {prefix}SEMANTIC_PROVIDER: "openai" or "anthropic"
        - {prefix}SEMANTIC_MODEL: Model name
        - {prefix}SEMANTIC_API_KEY: API key
        - {prefix}VALIDATION_TIMEOUT: Timeout in seconds
        - {prefix}FAIL_CLOSED: "true" or "false"
        - {prefix}MAX_TEXT_SIZE: Max bytes

        Args:
            prefix: Prefix for environment variables (default: "SENTINEL_")

        Returns:
            ValidationConfig instance
        """

        def get_bool(key: str, default: bool) -> bool:
            val = os.environ.get(f"{prefix}{key}", "").lower()
            if val in ("true", "1", "yes"):
                return True
            if val in ("false", "0", "no"):
                return False
            return default

        def get_float(key: str, default: float) -> float:
            val = os.environ.get(f"{prefix}{key}")
            if val:
                try:
                    return float(val)
                except ValueError:
                    pass
            return default

        def get_int(key: str, default: int) -> int:
            val = os.environ.get(f"{prefix}{key}")
            if val:
                try:
                    return int(val)
                except ValueError:
                    pass
            return default

        return cls(
            use_heuristic=get_bool("USE_HEURISTIC", True),
            use_semantic=get_bool("USE_SEMANTIC", False),
            semantic_provider=os.environ.get(
                f"{prefix}SEMANTIC_PROVIDER", "openai"
            ),
            semantic_model=os.environ.get(f"{prefix}SEMANTIC_MODEL"),
            semantic_api_key=os.environ.get(f"{prefix}SEMANTIC_API_KEY"),
            validation_timeout=get_float("VALIDATION_TIMEOUT", 30.0),
            fail_closed=get_bool("FAIL_CLOSED", False),
            max_text_size=get_int("MAX_TEXT_SIZE", 50_000),
        )


# Default configurations for common use cases

DEFAULT_CONFIG = ValidationConfig()
"""Default configuration: heuristic only, no API required."""

STRICT_CONFIG = ValidationConfig(
    fail_closed=True,
    validation_timeout=10.0,
)
"""Strict configuration: fail-closed, shorter timeout."""


__all__ = [
    "ValidationConfig",
    "DEFAULT_CONFIG",
    "STRICT_CONFIG",
]
