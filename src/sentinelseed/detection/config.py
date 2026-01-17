"""
Configuration classes for the Detection module.

This module provides configuration classes for InputValidator and OutputValidator:

- DetectionConfig: Base configuration shared by both validators
- InputValidatorConfig: Configuration specific to attack detection
- OutputValidatorConfig: Configuration specific to behavior verification

Configuration Sources:
    Configurations can be loaded from multiple sources:
    1. Code defaults - Sensible defaults for immediate use
    2. Constructor arguments - Explicit configuration
    3. Environment variables - Runtime configuration
    4. Configuration files - YAML or JSON files
    5. Factory methods - Preset configurations

Environment Variables:
    SENTINEL_API_KEY: API key for semantic validation
    SENTINEL_PROVIDER: LLM provider ("openai", "anthropic")
    SENTINEL_MODEL: Model to use for semantic validation
    SENTINEL_MODE: Validation mode ("auto", "heuristic", "semantic")
    SENTINEL_MIN_CONFIDENCE: Minimum confidence to block (0.0-1.0)
    SENTINEL_EMBEDDING_MODEL: Model for embedding-based detection

Design Principles:
    1. Fail-safe defaults - Works out of the box without configuration
    2. Environment-aware - Automatically loads from environment
    3. File-based - Supports YAML/JSON configuration files
    4. Immutable option - Frozen configs for thread safety
    5. Validation - Validates all values on construction

Example:
    # Simple usage (defaults)
    from sentinelseed.detection import InputValidatorConfig

    config = InputValidatorConfig()

    # With explicit values
    config = InputValidatorConfig(
        mode="semantic",
        api_key="sk-...",
        min_confidence_to_block=0.8,
    )

    # From environment
    config = InputValidatorConfig.from_env()

    # From file
    config = InputValidatorConfig.from_file("config.yaml")

References:
    - INPUT_VALIDATOR_v2.md: InputValidator configuration design
    - OUTPUT_VALIDATOR_v2.md: OutputValidator configuration design
    - VALIDATION_360_v2.md: Architecture overview
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

# Optional YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ValidationMode(str, Enum):
    """
    Validation mode for detectors and checkers.

    Values:
        AUTO: Automatically select mode based on API key availability
        HEURISTIC: Use pattern-based detection only (fast, no API)
        SEMANTIC: Use LLM-based analysis (accurate, requires API)
    """
    AUTO = "auto"
    HEURISTIC = "heuristic"
    SEMANTIC = "semantic"


class LLMProvider(str, Enum):
    """
    Supported LLM providers for semantic validation.

    Values:
        OPENAI: OpenAI API (GPT models)
        ANTHROPIC: Anthropic API (Claude models)
    """
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Strictness(str, Enum):
    """
    Strictness level for validation.

    Values:
        LENIENT: Allow more through, minimize false positives
        BALANCED: Balance between false positives and false negatives
        STRICT: Block more, prioritize safety over convenience
        PARANOID: Maximum safety, may have higher false positives
    """
    LENIENT = "lenient"
    BALANCED = "balanced"
    STRICT = "strict"
    PARANOID = "paranoid"


def _load_file(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from YAML or JSON file.

    Args:
        path: Path to configuration file

    Returns:
        Dictionary with configuration values

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            if not YAML_AVAILABLE:
                raise ValueError(
                    "YAML support requires PyYAML. "
                    "Install with: pip install pyyaml"
                )
            return yaml.safe_load(f) or {}
        elif path.suffix == ".json":
            return json.load(f)
        else:
            raise ValueError(
                f"Unsupported configuration file format: {path.suffix}. "
                "Use .yaml, .yml, or .json"
            )


@dataclass
class DetectionConfig:
    """
    Base configuration shared by InputValidator and OutputValidator.

    This class contains configuration options common to both validators.
    Use InputValidatorConfig or OutputValidatorConfig for validator-specific options.

    Attributes:
        mode: Validation mode (auto, heuristic, semantic)
        api_key: API key for semantic validation
        provider: LLM provider for semantic validation
        model: Specific model to use (None = provider default)
        timeout: Timeout for API calls in seconds
        max_text_length: Maximum text length to process (truncates longer)
        fail_closed: If True, errors result in blocking; if False, errors pass
        log_level: Logging level ("debug", "info", "warning", "error")

    Example:
        config = DetectionConfig(
            mode=ValidationMode.SEMANTIC,
            api_key="sk-...",
            provider=LLMProvider.OPENAI,
        )
    """
    # Mode
    mode: ValidationMode = ValidationMode.AUTO

    # API Configuration
    api_key: Optional[str] = None
    provider: LLMProvider = LLMProvider.OPENAI
    model: Optional[str] = None
    timeout: float = 10.0

    # Processing
    max_text_length: int = 50000
    fail_closed: bool = True

    # Logging
    log_level: str = "info"

    def __post_init__(self) -> None:
        """Validate and normalize configuration values."""
        # Load API key from environment if not provided
        if self.api_key is None:
            self.api_key = os.environ.get("SENTINEL_API_KEY")

        # Convert string mode to enum
        if isinstance(self.mode, str):
            self.mode = ValidationMode(self.mode.lower())

        # Convert string provider to enum
        if isinstance(self.provider, str):
            self.provider = LLMProvider(self.provider.lower())

        # Resolve AUTO mode
        if self.mode == ValidationMode.AUTO:
            self.mode = (
                ValidationMode.SEMANTIC if self.api_key
                else ValidationMode.HEURISTIC
            )

        # Validate timeout
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")

        # Validate max_text_length
        if self.max_text_length <= 0:
            raise ValueError(
                f"max_text_length must be positive, got {self.max_text_length}"
            )

    @property
    def is_semantic(self) -> bool:
        """Whether semantic validation is enabled."""
        return self.mode == ValidationMode.SEMANTIC and self.api_key is not None

    @property
    def is_heuristic(self) -> bool:
        """Whether heuristic validation is enabled."""
        return self.mode == ValidationMode.HEURISTIC

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Note: API key is masked for security.

        Returns:
            Dictionary representation
        """
        return {
            "mode": self.mode.value,
            "api_key": "***" if self.api_key else None,
            "provider": self.provider.value,
            "model": self.model,
            "timeout": self.timeout,
            "max_text_length": self.max_text_length,
            "fail_closed": self.fail_closed,
            "log_level": self.log_level,
        }


@dataclass
class InputValidatorConfig(DetectionConfig):
    """
    Configuration for InputValidator (attack detection).

    Extends DetectionConfig with options specific to input validation
    and attack detection.

    Attributes:
        use_embeddings: Enable embedding-based detection
        embedding_model: Model for embedding detection
        embedding_threshold: Similarity threshold for embedding detection
        embedding_cache_size: Maximum cached embeddings
        enabled_detectors: List of detector names to enable (None = all)
        detector_weights: Weight per detector for decision aggregation
        detector_thresholds: Confidence threshold per detector
        min_confidence_to_block: Minimum confidence to block input
        require_multiple_detectors: Require multiple detectors to agree
        min_detectors_to_block: Minimum detectors that must detect (if require_multiple_detectors)
        custom_examples_path: Path to custom attack examples file
        custom_patterns_path: Path to custom patterns file
        parallel_detection: Run detectors in parallel
        warmup_on_init: Pre-load models on initialization

    Example:
        config = InputValidatorConfig(
            use_embeddings=True,
            min_confidence_to_block=0.8,
            require_multiple_detectors=True,
            min_detectors_to_block=2,
        )
    """
    # Embeddings
    use_embeddings: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_threshold: float = 0.72
    embedding_cache_size: int = 1000

    # Semantic (LLM-based) Detection
    use_semantic: bool = False
    semantic_provider: str = "openai"
    semantic_model: Optional[str] = None
    semantic_threshold: float = 0.70
    semantic_fail_closed: bool = True

    # Benign Context Detection (FP reduction)
    # When enabled, reduces confidence for queries with benign technical context
    # e.g., "kill the process" in programming context
    use_benign_context: bool = True

    # Detectors
    enabled_detectors: Optional[List[str]] = None
    detector_weights: Dict[str, float] = field(default_factory=dict)
    detector_thresholds: Dict[str, float] = field(default_factory=dict)

    # Decision
    min_confidence_to_block: float = 0.7
    require_multiple_detectors: bool = False
    min_detectors_to_block: int = 2

    # Extensibility
    custom_examples_path: Optional[str] = None
    custom_patterns_path: Optional[str] = None

    # Performance
    parallel_detection: bool = True
    warmup_on_init: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize configuration values."""
        super().__post_init__()

        # Validate embedding_threshold
        if not 0.0 <= self.embedding_threshold <= 1.0:
            raise ValueError(
                f"embedding_threshold must be between 0.0 and 1.0, "
                f"got {self.embedding_threshold}"
            )

        # Validate min_confidence_to_block
        if not 0.0 <= self.min_confidence_to_block <= 1.0:
            raise ValueError(
                f"min_confidence_to_block must be between 0.0 and 1.0, "
                f"got {self.min_confidence_to_block}"
            )

        # Validate min_detectors_to_block
        if self.min_detectors_to_block < 1:
            raise ValueError(
                f"min_detectors_to_block must be at least 1, "
                f"got {self.min_detectors_to_block}"
            )

        # Load embedding model from environment
        env_embedding_model = os.environ.get("SENTINEL_EMBEDDING_MODEL")
        if env_embedding_model:
            self.embedding_model = env_embedding_model

        # Load min_confidence from environment
        env_min_confidence = os.environ.get("SENTINEL_MIN_CONFIDENCE")
        if env_min_confidence:
            self.min_confidence_to_block = float(env_min_confidence)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        base = super().to_dict()
        base.update({
            "use_embeddings": self.use_embeddings,
            "embedding_model": self.embedding_model,
            "embedding_threshold": self.embedding_threshold,
            "embedding_cache_size": self.embedding_cache_size,
            "use_semantic": self.use_semantic,
            "semantic_provider": self.semantic_provider,
            "semantic_model": self.semantic_model,
            "semantic_threshold": self.semantic_threshold,
            "semantic_fail_closed": self.semantic_fail_closed,
            "enabled_detectors": self.enabled_detectors,
            "detector_weights": self.detector_weights,
            "detector_thresholds": self.detector_thresholds,
            "min_confidence_to_block": self.min_confidence_to_block,
            "require_multiple_detectors": self.require_multiple_detectors,
            "min_detectors_to_block": self.min_detectors_to_block,
            "custom_examples_path": self.custom_examples_path,
            "custom_patterns_path": self.custom_patterns_path,
            "parallel_detection": self.parallel_detection,
            "warmup_on_init": self.warmup_on_init,
        })
        return base

    @classmethod
    def from_env(cls) -> "InputValidatorConfig":
        """
        Create configuration from environment variables.

        Reads:
            SENTINEL_API_KEY, SENTINEL_PROVIDER, SENTINEL_MODEL,
            SENTINEL_MODE, SENTINEL_EMBEDDING_MODEL, SENTINEL_MIN_CONFIDENCE

        Returns:
            InputValidatorConfig populated from environment

        Example:
            os.environ["SENTINEL_API_KEY"] = "sk-..."
            config = InputValidatorConfig.from_env()
        """
        return cls(
            api_key=os.environ.get("SENTINEL_API_KEY"),
            provider=os.environ.get("SENTINEL_PROVIDER", "openai"),
            model=os.environ.get("SENTINEL_MODEL"),
            mode=os.environ.get("SENTINEL_MODE", "auto"),
            embedding_model=os.environ.get(
                "SENTINEL_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
            ),
            min_confidence_to_block=float(
                os.environ.get("SENTINEL_MIN_CONFIDENCE", "0.7")
            ),
        )

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "InputValidatorConfig":
        """
        Create configuration from YAML or JSON file.

        Args:
            path: Path to configuration file

        Returns:
            InputValidatorConfig populated from file

        Example:
            config = InputValidatorConfig.from_file("config.yaml")
        """
        data = _load_file(path)
        return cls(**data)

    @classmethod
    def strict(cls) -> "InputValidatorConfig":
        """
        Create a strict configuration preset.

        Higher sensitivity, lower tolerance for potential attacks.

        Returns:
            InputValidatorConfig with strict settings
        """
        return cls(
            min_confidence_to_block=0.5,
            require_multiple_detectors=False,
            fail_closed=True,
        )

    @classmethod
    def lenient(cls) -> "InputValidatorConfig":
        """
        Create a lenient configuration preset.

        Lower sensitivity, higher tolerance to reduce false positives.

        Returns:
            InputValidatorConfig with lenient settings
        """
        return cls(
            min_confidence_to_block=0.85,
            require_multiple_detectors=True,
            min_detectors_to_block=2,
            fail_closed=False,
        )


@dataclass
class OutputValidatorConfig(DetectionConfig):
    """
    Configuration for OutputValidator (behavior verification).

    Extends DetectionConfig with options specific to output validation
    and behavior checking.

    Attributes:
        context_type: Type of AI being validated (for context-aware checking)
        strictness: How strict the validation should be
        enabled_checkers: List of checker names to enable (None = all)
        checker_weights: Weight per checker for decision aggregation
        min_severity_to_block: Minimum severity level to block output
        require_multiple_checkers: Require multiple checkers to fail
        custom_rules_path: Path to custom rules file
        parallel_checking: Run checkers in parallel
        output_mode: Enable output-focused detection (v1.2.0)
        require_behavioral_context: Keywords need behavioral indicators (v1.2.0)
        benign_context_check: Enable benign context whitelist (v1.2.0)

    Example:
        config = OutputValidatorConfig(
            context_type="customer_service",
            strictness=Strictness.STRICT,
            min_severity_to_block="high",
        )
    """
    # Context
    context_type: str = "general"
    strictness: Strictness = Strictness.BALANCED

    # Semantic (LLM-based) Checking
    use_semantic: bool = False
    semantic_provider: str = "openai"
    semantic_model: Optional[str] = None
    semantic_fail_closed: bool = True

    # Embedding-based Checking (for toxic content detection)
    use_embeddings: bool = False
    embedding_provider: str = "openai"
    embedding_model: Optional[str] = None
    embedding_threshold: float = 0.50  # Calibrated: 0.50 = ~60% coverage on ToxiGen
    embedding_fail_closed: bool = False  # Fail-open by default (heuristics backup)

    # Checkers
    enabled_checkers: Optional[List[str]] = None
    checker_weights: Dict[str, float] = field(default_factory=dict)

    # Decision
    min_severity_to_block: str = "high"
    require_multiple_checkers: bool = False

    # Extensibility
    custom_rules_path: Optional[str] = None

    # Performance
    parallel_checking: bool = True

    # Output-specific settings (v1.2.0 - FP reduction)
    # These settings help L3 focus on AI BEHAVIOR rather than INPUT patterns
    output_mode: bool = True  # Enable output-focused detection (vs input pattern matching)
    require_behavioral_context: bool = True  # Keywords need behavioral indicators
    benign_context_check: bool = True  # Enable benign context whitelist (e.g., "dog grooming")

    def __post_init__(self) -> None:
        """Validate and normalize configuration values."""
        super().__post_init__()

        # Convert string strictness to enum
        if isinstance(self.strictness, str):
            self.strictness = Strictness(self.strictness.lower())

        # Validate min_severity_to_block
        valid_severities = {"low", "medium", "high", "critical"}
        if self.min_severity_to_block.lower() not in valid_severities:
            raise ValueError(
                f"min_severity_to_block must be one of {valid_severities}, "
                f"got {self.min_severity_to_block}"
            )
        self.min_severity_to_block = self.min_severity_to_block.lower()

    @property
    def severity_threshold(self) -> int:
        """
        Get numeric severity threshold for comparisons.

        Returns:
            Integer severity level (1-4)
        """
        severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return severity_map.get(self.min_severity_to_block, 3)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        base = super().to_dict()
        base.update({
            "context_type": self.context_type,
            "strictness": self.strictness.value,
            "use_semantic": self.use_semantic,
            "semantic_provider": self.semantic_provider,
            "semantic_model": self.semantic_model,
            "semantic_fail_closed": self.semantic_fail_closed,
            "use_embeddings": self.use_embeddings,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_threshold": self.embedding_threshold,
            "embedding_fail_closed": self.embedding_fail_closed,
            "enabled_checkers": self.enabled_checkers,
            "checker_weights": self.checker_weights,
            "min_severity_to_block": self.min_severity_to_block,
            "require_multiple_checkers": self.require_multiple_checkers,
            "custom_rules_path": self.custom_rules_path,
            "parallel_checking": self.parallel_checking,
            # v1.2.0: Output-specific settings
            "output_mode": self.output_mode,
            "require_behavioral_context": self.require_behavioral_context,
            "benign_context_check": self.benign_context_check,
        })
        return base

    @classmethod
    def from_env(cls) -> "OutputValidatorConfig":
        """
        Create configuration from environment variables.

        Returns:
            OutputValidatorConfig populated from environment
        """
        return cls(
            api_key=os.environ.get("SENTINEL_API_KEY"),
            provider=os.environ.get("SENTINEL_PROVIDER", "openai"),
            model=os.environ.get("SENTINEL_MODEL"),
            mode=os.environ.get("SENTINEL_MODE", "auto"),
            context_type=os.environ.get("SENTINEL_CONTEXT_TYPE", "general"),
        )

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "OutputValidatorConfig":
        """
        Create configuration from YAML or JSON file.

        Args:
            path: Path to configuration file

        Returns:
            OutputValidatorConfig populated from file
        """
        data = _load_file(path)
        return cls(**data)

    @classmethod
    def strict(cls) -> "OutputValidatorConfig":
        """
        Create a strict configuration preset.

        Returns:
            OutputValidatorConfig with strict settings
        """
        return cls(
            strictness=Strictness.STRICT,
            min_severity_to_block="medium",
            require_multiple_checkers=False,
            fail_closed=True,
        )

    @classmethod
    def lenient(cls) -> "OutputValidatorConfig":
        """
        Create a lenient configuration preset.

        Returns:
            OutputValidatorConfig with lenient settings
        """
        return cls(
            strictness=Strictness.LENIENT,
            min_severity_to_block="critical",
            require_multiple_checkers=True,
            fail_closed=False,
        )

    @classmethod
    def for_context(cls, context_type: str) -> "OutputValidatorConfig":
        """
        Create configuration optimized for a specific context.

        Args:
            context_type: Type of AI context:
                - "customer_service": Customer support applications
                - "financial": Financial/banking applications
                - "healthcare": Healthcare/medical applications
                - "education": Educational applications
                - "general": General purpose (default)

        Returns:
            OutputValidatorConfig optimized for the context
        """
        context_configs = {
            "customer_service": cls(
                context_type="customer_service",
                strictness=Strictness.BALANCED,
                min_severity_to_block="high",
            ),
            "financial": cls(
                context_type="financial",
                strictness=Strictness.STRICT,
                min_severity_to_block="medium",
            ),
            "healthcare": cls(
                context_type="healthcare",
                strictness=Strictness.STRICT,
                min_severity_to_block="medium",
            ),
            "education": cls(
                context_type="education",
                strictness=Strictness.BALANCED,
                min_severity_to_block="high",
            ),
        }
        return context_configs.get(context_type, cls(context_type=context_type))


__all__ = [
    # Enums
    "ValidationMode",
    "LLMProvider",
    "Strictness",
    # Config classes
    "DetectionConfig",
    "InputValidatorConfig",
    "OutputValidatorConfig",
]
