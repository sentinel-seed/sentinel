"""
Raw API integration for Sentinel AI.

Provides utilities for adding Sentinel safety to raw HTTP API calls
to LLM providers. Use this when you're not using an official SDK
and making direct HTTP requests.

Supports:
    - OpenAI Chat Completions API
    - Anthropic Messages API
    - Any OpenAI-compatible API (OpenRouter, Together, etc.)
    - Generic message-based APIs

Usage:
    from sentinelseed.integrations.raw_api import (
        prepare_openai_request,
        prepare_anthropic_request,
        validate_response,
    )

    # For OpenAI-compatible APIs
    headers, body = prepare_openai_request(
        messages=[{"role": "user", "content": "Hello"}],
        model="gpt-4o",
        api_key="your-key"
    )
    response = requests.post(url, headers=headers, json=body)
    validated = validate_response(response.json())

    # For Anthropic API
    headers, body = prepare_anthropic_request(
        messages=[{"role": "user", "content": "Hello"}],
        model="claude-sonnet-4-5-20250929",
        api_key="your-key"
    )
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from json import JSONDecodeError
import logging

from sentinelseed import Sentinel
from sentinelseed.integrations._base import (
    SentinelIntegration,
    LayeredValidator,
    ValidationConfig,
    ValidationResult,
)

__version__ = "2.26.0"

__all__ = [
    # Functions
    "prepare_openai_request",
    "prepare_anthropic_request",
    "validate_response",
    "create_openai_request_body",
    "create_anthropic_request_body",
    "inject_seed_openai",
    "inject_seed_anthropic",
    # Classes
    "RawAPIClient",
    # Constants
    "OPENAI_API_URL",
    "ANTHROPIC_API_URL",
    "VALID_SEED_LEVELS",
    "VALID_PROVIDERS",
    "VALID_RESPONSE_FORMATS",
    "DEFAULT_TIMEOUT",
    # Exceptions
    "RawAPIError",
    "ValidationError",
]

logger = logging.getLogger("sentinelseed.raw_api")


# Validation constants
VALID_SEED_LEVELS = ("minimal", "standard", "full")
VALID_PROVIDERS = ("openai", "anthropic")
VALID_RESPONSE_FORMATS = ("openai", "anthropic")
DEFAULT_TIMEOUT = 30


# API endpoints
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class RawAPIError(Exception):
    """Base exception for raw API errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(RawAPIError):
    """Raised when input or output validation fails."""

    def __init__(
        self,
        message: str,
        concerns: Optional[List[str]] = None,
        violations: Optional[List[str]] = None,
    ):
        self.concerns = concerns or []
        self.violations = violations or []
        super().__init__(message, {"concerns": self.concerns, "violations": self.violations})


def _validate_seed_level(seed_level: str) -> None:
    """Validate seed_level parameter."""
    if seed_level not in VALID_SEED_LEVELS:
        raise ValueError(
            f"Invalid seed_level: '{seed_level}'. Must be one of: {VALID_SEED_LEVELS}"
        )


def _validate_messages(messages: Any) -> None:
    """Validate messages parameter."""
    if messages is None:
        raise ValueError("messages cannot be None")
    if not isinstance(messages, list):
        raise ValueError(f"messages must be a list, got {type(messages).__name__}")
    if len(messages) == 0:
        raise ValueError("messages cannot be empty")
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            raise ValueError(f"messages[{i}] must be a dict, got {type(msg).__name__}")
        if "role" not in msg:
            raise ValueError(f"messages[{i}] missing required 'role' key")
        # M008: Validate role is a string
        if not isinstance(msg["role"], str):
            raise ValueError(
                f"messages[{i}]['role'] must be a string, got {type(msg['role']).__name__}"
            )


def _validate_timeout(timeout: Any, param_name: str = "timeout") -> None:
    """Validate timeout parameter is a positive number."""
    if not isinstance(timeout, (int, float)):
        raise ValueError(
            f"{param_name} must be a number, got {type(timeout).__name__}"
        )
    if timeout <= 0:
        raise ValueError(f"{param_name} must be positive, got {timeout}")


def _validate_temperature(temperature: Any, max_value: float = 2.0) -> None:
    """Validate temperature parameter is a number between 0 and max_value.

    Args:
        temperature: The temperature value to validate
        max_value: Maximum allowed value (2.0 for OpenAI, 1.0 for Anthropic)
    """
    if not isinstance(temperature, (int, float)):
        raise ValueError(
            f"temperature must be a number, got {type(temperature).__name__}"
        )
    if temperature < 0 or temperature > max_value:
        raise ValueError(
            f"temperature must be between 0 and {max_value}, got {temperature}"
        )


def _validate_max_tokens(max_tokens: Any) -> None:
    """Validate max_tokens parameter is a positive integer."""
    if not isinstance(max_tokens, int):
        raise ValueError(
            f"max_tokens must be an integer, got {type(max_tokens).__name__}"
        )
    if max_tokens < 1:
        raise ValueError(f"max_tokens must be positive, got {max_tokens}")


def _validate_model(model: Any) -> None:
    """Validate model parameter is a non-empty string."""
    if model is None:
        raise ValueError("model cannot be None")
    if not isinstance(model, str):
        raise ValueError(f"model must be a string, got {type(model).__name__}")
    if not model.strip():
        raise ValueError("model cannot be an empty string")


def _validate_api_key(api_key: Any, required: bool = False) -> None:
    """Validate api_key parameter is None or a non-empty string."""
    if api_key is None:
        if required:
            raise ValueError("api_key is required")
        return
    if not isinstance(api_key, str):
        raise ValueError(
            f"api_key must be a string, got {type(api_key).__name__}"
        )
    if not api_key.strip():
        raise ValueError("api_key cannot be an empty string")


def _validate_bool(value: Any, param_name: str) -> None:
    """Validate a parameter is a boolean."""
    if not isinstance(value, bool):
        raise TypeError(
            f"{param_name} must be a bool, got {type(value).__name__}"
        )


def _validate_system(system: Any) -> None:
    """Validate system parameter is None or a string."""
    if system is None:
        return
    if not isinstance(system, str):
        raise ValueError(
            f"system must be a string, got {type(system).__name__}"
        )


def _validate_base_url(base_url: Any) -> None:
    """Validate base_url parameter is None or a non-empty string."""
    if base_url is None:
        return
    if not isinstance(base_url, str):
        raise ValueError(
            f"base_url must be a string, got {type(base_url).__name__}"
        )
    if not base_url.strip():
        raise ValueError("base_url cannot be an empty string")


def _validate_sentinel(sentinel: Any) -> None:
    """Validate sentinel parameter has required methods (duck-typing)."""
    if sentinel is None:
        return
    # Duck-typing: check for required methods
    required_methods = ['validate', 'validate_request', 'get_seed']
    for method in required_methods:
        if not callable(getattr(sentinel, method, None)):
            raise TypeError(
                f"sentinel must have a callable '{method}' method, "
                f"got {type(sentinel).__name__} without {method}()"
            )


def _validate_validator(validator: Any) -> None:
    """Validate validator parameter has required methods (duck-typing)."""
    if validator is None:
        return
    # Duck-typing: check for validate method
    if not callable(getattr(validator, 'validate', None)):
        raise TypeError(
            f"validator must have a callable 'validate' method, "
            f"got {type(validator).__name__} without validate()"
        )


def _safe_get_content(msg: Dict[str, Any]) -> str:
    """Safely extract content from message, handling None and non-string values."""
    content = msg.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    # Handle list content (OpenAI vision format)
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        return " ".join(text_parts)
    return str(content)


def prepare_openai_request(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    inject_seed: bool = True,
    validate_input: bool = True,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    **kwargs,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    Prepare an OpenAI-compatible API request with Sentinel safety.

    Works with OpenAI, OpenRouter, Together AI, and any OpenAI-compatible API.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model identifier
        api_key: API key for Authorization header
        sentinel: Sentinel instance (creates default if None)
        seed_level: Seed level to use (minimal, standard, full)
        inject_seed: Whether to inject seed into system message
        validate_input: Whether to validate input messages
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        **kwargs: Additional API parameters

    Returns:
        Tuple of (headers dict, body dict)

    Raises:
        ValueError: If parameters are invalid
        ValidationError: If input validation fails

    Example:
        import requests
        from sentinelseed.integrations.raw_api import prepare_openai_request

        headers, body = prepare_openai_request(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o",
            api_key="sk-..."
        )

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body
        )
    """
    # Validate parameters
    _validate_messages(messages)
    _validate_seed_level(seed_level)
    _validate_model(model)
    _validate_api_key(api_key)
    _validate_max_tokens(max_tokens)
    _validate_temperature(temperature)
    _validate_bool(inject_seed, "inject_seed")
    _validate_bool(validate_input, "validate_input")
    _validate_sentinel(sentinel)

    # Create sentinel instance
    try:
        sentinel = sentinel or Sentinel(seed_level=seed_level)
    except Exception as e:
        logger.error(f"Failed to create Sentinel instance: {e}")
        raise RawAPIError(f"Failed to initialize Sentinel: {e}")

    # Validate input messages
    if validate_input:
        for msg in messages:
            content = _safe_get_content(msg)
            if content.strip() and msg.get("role") == "user":
                try:
                    result = sentinel.validate_request(content)
                    if not result.get("should_proceed", True):
                        concerns = result.get("concerns", ["Unknown concern"])
                        logger.warning(f"Input blocked by Sentinel: {concerns}")
                        raise ValidationError(
                            f"Input blocked by Sentinel",
                            concerns=concerns if isinstance(concerns, list) else [str(concerns)],
                        )
                except ValidationError:
                    raise
                except Exception as e:
                    logger.error(f"Validation error: {e}")
                    raise RawAPIError(f"Input validation failed: {e}")

    # Prepare messages with seed injection
    prepared_messages = list(messages)

    if inject_seed:
        seed = sentinel.get_seed()

        # Check for existing system message
        has_system = False
        for i, msg in enumerate(prepared_messages):
            if msg.get("role") == "system":
                existing_content = _safe_get_content(msg)
                prepared_messages[i] = {
                    "role": "system",
                    "content": f"{seed}\n\n---\n\n{existing_content}"
                }
                has_system = True
                break

        # Add system message if none exists
        if not has_system:
            prepared_messages.insert(0, {"role": "system", "content": seed})

    # Build headers
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Build request body
    body = {
        "model": model,
        "messages": prepared_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        **kwargs,
    }

    logger.debug(f"Prepared OpenAI request for model {model} with {len(prepared_messages)} messages")
    return headers, body


def prepare_anthropic_request(
    messages: List[Dict[str, str]],
    model: str = "claude-sonnet-4-5-20250929",
    api_key: Optional[str] = None,
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    inject_seed: bool = True,
    validate_input: bool = True,
    max_tokens: int = 1024,
    temperature: float = 1.0,
    system: Optional[str] = None,
    **kwargs,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    Prepare an Anthropic API request with Sentinel safety.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model identifier
        api_key: API key for x-api-key header
        sentinel: Sentinel instance (creates default if None)
        seed_level: Seed level to use (minimal, standard, full)
        inject_seed: Whether to inject seed into system prompt
        validate_input: Whether to validate input messages
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0 to 1 for Anthropic)
        system: System prompt (seed will be prepended)
        **kwargs: Additional API parameters

    Returns:
        Tuple of (headers dict, body dict)

    Raises:
        ValueError: If parameters are invalid
        ValidationError: If input validation fails

    Example:
        import requests
        from sentinelseed.integrations.raw_api import prepare_anthropic_request

        headers, body = prepare_anthropic_request(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4-5-20250929",
            api_key="sk-ant-..."
        )

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body
        )
    """
    # Validate parameters
    _validate_messages(messages)
    _validate_seed_level(seed_level)
    _validate_model(model)
    _validate_api_key(api_key)
    _validate_max_tokens(max_tokens)
    _validate_temperature(temperature, max_value=1.0)  # Anthropic uses 0-1
    _validate_system(system)
    _validate_bool(inject_seed, "inject_seed")
    _validate_bool(validate_input, "validate_input")
    _validate_sentinel(sentinel)

    # Create sentinel instance
    try:
        sentinel = sentinel or Sentinel(seed_level=seed_level)
    except Exception as e:
        logger.error(f"Failed to create Sentinel instance: {e}")
        raise RawAPIError(f"Failed to initialize Sentinel: {e}")

    # Validate input messages
    if validate_input:
        for msg in messages:
            content = _safe_get_content(msg)
            if content.strip() and msg.get("role") == "user":
                try:
                    result = sentinel.validate_request(content)
                    if not result.get("should_proceed", True):
                        concerns = result.get("concerns", ["Unknown concern"])
                        logger.warning(f"Input blocked by Sentinel: {concerns}")
                        raise ValidationError(
                            f"Input blocked by Sentinel",
                            concerns=concerns if isinstance(concerns, list) else [str(concerns)],
                        )
                except ValidationError:
                    raise
                except Exception as e:
                    logger.error(f"Validation error: {e}")
                    raise RawAPIError(f"Input validation failed: {e}")

    # Filter out system messages (Anthropic uses separate system field)
    filtered_messages = [
        msg for msg in messages
        if msg.get("role") != "system"
    ]

    # Extract system content from messages if present
    for msg in messages:
        if msg.get("role") == "system":
            msg_content = _safe_get_content(msg)
            if system:
                system = f"{msg_content}\n\n{system}"
            else:
                system = msg_content

    # Inject seed into system prompt
    if inject_seed:
        seed = sentinel.get_seed()
        if system:
            system = f"{seed}\n\n---\n\n{system}"
        else:
            system = seed

    # Build headers
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if api_key:
        headers["x-api-key"] = api_key

    # Build request body
    body = {
        "model": model,
        "messages": filtered_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        **kwargs,
    }

    if system:
        body["system"] = system

    return headers, body


def _extract_openai_content(response: Dict[str, Any]) -> str:
    """Safely extract content from OpenAI response format."""
    choices = response.get("choices")
    if choices is None:
        return ""
    if not isinstance(choices, list):
        logger.warning(f"Expected choices to be list, got {type(choices).__name__}")
        return ""
    if len(choices) == 0:
        return ""

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        logger.warning(f"Expected choice to be dict, got {type(first_choice).__name__}")
        return ""

    message = first_choice.get("message")
    if message is None:
        return ""
    if not isinstance(message, dict):
        logger.warning(f"Expected message to be dict, got {type(message).__name__}")
        return ""

    content = message.get("content")
    if content is None:
        return ""
    if not isinstance(content, str):
        return str(content)

    return content


def _extract_anthropic_content(response: Dict[str, Any]) -> str:
    """Safely extract content from Anthropic response format."""
    content_blocks = response.get("content")
    if content_blocks is None:
        return ""
    if not isinstance(content_blocks, list):
        logger.warning(f"Expected content to be list, got {type(content_blocks).__name__}")
        return ""

    text_parts = []
    for i, block in enumerate(content_blocks):
        if not isinstance(block, dict):
            logger.warning(f"Expected block[{i}] to be dict, got {type(block).__name__}")
            continue
        if block.get("type") == "text":
            text = block.get("text", "")
            if isinstance(text, str):
                text_parts.append(text)
            else:
                text_parts.append(str(text))

    return "".join(text_parts)


def validate_response(
    response: Dict[str, Any],
    sentinel: Optional[Sentinel] = None,
    response_format: str = "openai",
    block_on_unsafe: bool = False,
    validator: Optional[LayeredValidator] = None,
) -> Dict[str, Any]:
    """
    Validate an API response through Sentinel THSP gates.

    Args:
        response: Parsed JSON response from API
        sentinel: Sentinel instance (creates default if None, used as fallback)
        response_format: Format of response - 'openai' or 'anthropic'
        block_on_unsafe: If True, raise ValidationError when content is unsafe
        validator: LayeredValidator instance (preferred over sentinel if provided)

    Returns:
        Dict with 'valid', 'response', 'violations', 'content', 'sentinel_checked'

    Raises:
        ValueError: If response_format is invalid
        ValidationError: If block_on_unsafe=True and content is unsafe

    Example:
        response = requests.post(url, headers=headers, json=body).json()
        result = validate_response(response)

        if result["valid"]:
            print(result["content"])
        else:
            print(f"Safety concerns: {result['violations']}")
    """
    # Validate response_format
    if response_format not in VALID_RESPONSE_FORMATS:
        raise ValueError(
            f"Invalid response_format: '{response_format}'. "
            f"Must be one of: {VALID_RESPONSE_FORMATS}"
        )

    # Validate response type
    if response is None:
        raise ValueError("response cannot be None")
    if not isinstance(response, dict):
        raise ValueError(f"response must be a dict, got {type(response).__name__}")

    # Validate block_on_unsafe
    _validate_bool(block_on_unsafe, "block_on_unsafe")
    _validate_validator(validator)

    # M011: Detect API error responses before processing
    # Only treat as error if "error" key exists AND has a truthy value
    # This avoids false positives with {"error": null} or {"error": []}
    error_info = response.get("error")
    if error_info:
        if isinstance(error_info, dict):
            error_msg = error_info.get("message", "Unknown API error")
        else:
            error_msg = str(error_info)
        return {
            "valid": False,
            "response": response,
            "violations": [f"API error: {error_msg}"],
            "content": "",
            "sentinel_checked": False,
        }

    # Extract content based on format
    if response_format == "openai":
        content = _extract_openai_content(response)
    else:  # anthropic
        content = _extract_anthropic_content(response)

    # Validate content
    is_safe = True
    violations = []

    if content.strip():
        try:
            # Prefer validator (LayeredValidator) over sentinel
            if validator is not None:
                result = validator.validate(content)
                is_safe = result.is_safe
                violations = result.violations
            else:
                # Fallback to sentinel for backwards compatibility
                if sentinel is None:
                    sentinel = Sentinel()
                is_safe, violations = sentinel.validate(content)
        except Exception as e:
            logger.error(f"Output validation error: {e}")
            is_safe = False
            violations = [f"Validation error: {e}"]

    # Block unsafe content if requested
    if block_on_unsafe and not is_safe:
        logger.warning(f"Output blocked by Sentinel: {violations}")
        raise ValidationError(
            "Output blocked by Sentinel",
            violations=violations if isinstance(violations, list) else [str(violations)],
        )

    return {
        "valid": is_safe,
        "response": response,
        "violations": violations,
        "content": content,
        "sentinel_checked": True,
    }


def create_openai_request_body(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    inject_seed: bool = True,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    **kwargs,
) -> Dict[str, Any]:
    """
    Create just the request body for OpenAI API (without headers).

    Useful when you're using a library that handles headers.

    Args:
        messages: List of message dicts
        model: Model identifier
        sentinel: Sentinel instance
        seed_level: Seed level to use
        inject_seed: Whether to inject seed
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0 to 2)
        **kwargs: Additional parameters

    Returns:
        Request body dict

    Example:
        from openai import OpenAI
        from sentinelseed.integrations.raw_api import create_openai_request_body

        body = create_openai_request_body(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o"
        )

        # Use with low-level httpx client
        response = httpx.post(url, json=body, headers=headers)
    """
    _, body = prepare_openai_request(
        messages=messages,
        model=model,
        sentinel=sentinel,
        seed_level=seed_level,
        inject_seed=inject_seed,
        validate_input=False,  # Caller handles validation
        max_tokens=max_tokens,
        temperature=temperature,
        **kwargs,
    )
    return body


def create_anthropic_request_body(
    messages: List[Dict[str, str]],
    model: str = "claude-sonnet-4-5-20250929",
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    inject_seed: bool = True,
    max_tokens: int = 1024,
    temperature: float = 1.0,
    system: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Create just the request body for Anthropic API (without headers).

    Args:
        messages: List of message dicts
        model: Model identifier
        sentinel: Sentinel instance
        seed_level: Seed level to use
        inject_seed: Whether to inject seed
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0 to 1)
        system: System prompt
        **kwargs: Additional parameters

    Returns:
        Request body dict
    """
    _, body = prepare_anthropic_request(
        messages=messages,
        model=model,
        sentinel=sentinel,
        seed_level=seed_level,
        inject_seed=inject_seed,
        validate_input=False,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        **kwargs,
    )
    return body


class RawAPIClient(SentinelIntegration):
    """
    Simple HTTP client for LLM APIs with Sentinel safety.

    Provides a minimal client for making API calls without
    depending on official SDKs.

    Inherits from SentinelIntegration for standardized validation via
    LayeredValidator.

    Example:
        from sentinelseed.integrations.raw_api import RawAPIClient

        client = RawAPIClient(
            provider="openai",
            api_key="sk-..."
        )

        response = client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o"
        )

    Attributes:
        provider: API provider ('openai' or 'anthropic')
        api_key: API key for authentication
        base_url: Base URL for API requests
        sentinel: Sentinel instance for seed injection (backwards compat)
        validator: LayeredValidator for validation (via SentinelIntegration)
        timeout: Request timeout in seconds
    """

    _integration_name = "raw_api"

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        timeout: Union[int, float] = DEFAULT_TIMEOUT,
        validator: Optional[LayeredValidator] = None,
    ):
        """
        Initialize raw API client.

        Args:
            provider: API provider - 'openai' or 'anthropic'
            api_key: API key
            base_url: Custom base URL (for OpenAI-compatible APIs)
            sentinel: Sentinel instance (backwards compatibility for get_seed())
            seed_level: Seed level to use (minimal, standard, full)
            timeout: Request timeout in seconds (int or float)
            validator: Optional LayeredValidator for dependency injection (testing)

        Raises:
            ValueError: If provider, seed_level, base_url, or timeout is invalid
        """
        # Validate provider
        if provider not in VALID_PROVIDERS:
            raise ValueError(
                f"Invalid provider: '{provider}'. Must be one of: {VALID_PROVIDERS}"
            )

        # Validate seed_level
        _validate_seed_level(seed_level)

        # Validate timeout (M001, M002)
        _validate_timeout(timeout)

        # Validate api_key (A005)
        _validate_api_key(api_key)

        # Validate base_url (C001)
        _validate_base_url(base_url)

        # Validate sentinel (REV-004)
        _validate_sentinel(sentinel)

        # Validate validator (REV-005)
        _validate_validator(validator)

        # Create LayeredValidator if not provided
        if validator is None:
            config = ValidationConfig(
                use_heuristic=True,
                use_semantic=False,
            )
            validator = LayeredValidator(config=config)

        # Initialize SentinelIntegration
        super().__init__(validator=validator)

        self.provider = provider
        self.api_key = api_key
        self.timeout = timeout

        # Keep Sentinel instance for get_seed() backwards compatibility
        try:
            self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        except Exception as e:
            logger.error(f"Failed to create Sentinel instance: {e}")
            raise RawAPIError(f"Failed to initialize Sentinel: {e}")

        # Set base URL
        if base_url:
            self.base_url = base_url.rstrip("/")
        elif provider == "openai":
            self.base_url = "https://api.openai.com/v1"
        else:  # anthropic
            self.base_url = "https://api.anthropic.com/v1"

        logger.debug(f"Initialized RawAPIClient for {provider} at {self.base_url}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1024,
        timeout: Optional[Union[int, float]] = None,
        block_on_unsafe: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a chat request.

        Args:
            messages: Conversation messages
            model: Model to use
            max_tokens: Maximum tokens
            timeout: Request timeout (overrides client default)
            block_on_unsafe: If True, raise ValidationError for unsafe output
            **kwargs: Additional parameters

        Returns:
            API response dict with validation info

        Raises:
            ImportError: If requests package is not installed
            RawAPIError: If HTTP request fails
            ValidationError: If input validation fails or block_on_unsafe=True and output is unsafe
        """
        try:
            import requests
            from requests.exceptions import RequestException, Timeout, HTTPError
        except ImportError:
            raise ImportError("requests package required. Install with: pip install requests")

        # Validate parameters (A003, A006, A002)
        _validate_max_tokens(max_tokens)
        _validate_bool(block_on_unsafe, "block_on_unsafe")
        if timeout is not None:
            _validate_timeout(timeout)

        # Set default model
        if model is None:
            model = "gpt-4o-mini" if self.provider == "openai" else "claude-sonnet-4-5-20250929"

        # Use provided timeout or client default
        request_timeout = timeout if timeout is not None else self.timeout

        # Prepare request
        if self.provider == "anthropic":
            headers, body = prepare_anthropic_request(
                messages=messages,
                model=model,
                api_key=self.api_key,
                sentinel=self.sentinel,
                max_tokens=max_tokens,
                **kwargs,
            )
            url = f"{self.base_url}/messages"
            response_format = "anthropic"
        else:
            headers, body = prepare_openai_request(
                messages=messages,
                model=model,
                api_key=self.api_key,
                sentinel=self.sentinel,
                max_tokens=max_tokens,
                **kwargs,
            )
            url = f"{self.base_url}/chat/completions"
            response_format = "openai"

        # Make request with error handling
        try:
            logger.debug(f"Sending request to {url}")
            response = requests.post(url, headers=headers, json=body, timeout=request_timeout)
            response.raise_for_status()
        except Timeout:
            logger.error(f"Request timed out after {request_timeout}s")
            raise RawAPIError(
                f"Request timed out after {request_timeout} seconds",
                details={"url": url, "timeout": request_timeout},
            )
        except HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            error_body = None
            if e.response is not None:
                try:
                    error_body = e.response.json()
                except (JSONDecodeError, ValueError):
                    error_body = e.response.text[:500] if e.response.text else None

            logger.error(f"HTTP error {status_code}: {e}")
            raise RawAPIError(
                f"HTTP error {status_code}: {e}",
                details={"url": url, "status_code": status_code, "error_body": error_body},
            )
        except RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RawAPIError(
                f"Request failed: {e}",
                details={"url": url},
            )

        # Parse JSON response
        try:
            response_data = response.json()
        except JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise RawAPIError(
                f"Failed to parse JSON response: {e}",
                details={"response_text": response.text[:500] if response.text else None},
            )

        # Validate response using inherited validator
        return validate_response(
            response_data,
            sentinel=self.sentinel,
            block_on_unsafe=block_on_unsafe,
            response_format=response_format,
            validator=self._validator,
        )


# Convenience functions
def inject_seed_openai(
    messages: List[Dict[str, str]],
    seed_level: str = "standard",
) -> List[Dict[str, str]]:
    """
    Inject Sentinel seed into OpenAI-format messages.

    Simple utility to add seed without full request preparation.

    Args:
        messages: Original messages
        seed_level: Seed level to use (minimal, standard, full)

    Returns:
        Messages with seed injected

    Raises:
        ValueError: If messages or seed_level is invalid

    Example:
        messages = [{"role": "user", "content": "Hello"}]
        safe_messages = inject_seed_openai(messages)
    """
    _validate_messages(messages)
    _validate_seed_level(seed_level)

    try:
        sentinel = Sentinel(seed_level=seed_level)
    except Exception as e:
        logger.error(f"Failed to create Sentinel instance: {e}")
        raise RawAPIError(f"Failed to initialize Sentinel: {e}")

    seed = sentinel.get_seed()
    result = list(messages)

    # Check for existing system message
    has_system = False
    for i, msg in enumerate(result):
        if msg.get("role") == "system":
            existing_content = _safe_get_content(msg)
            result[i] = {
                "role": "system",
                "content": f"{seed}\n\n---\n\n{existing_content}"
            }
            has_system = True
            break

    if not has_system:
        result.insert(0, {"role": "system", "content": seed})

    return result


def inject_seed_anthropic(
    system: Optional[str] = None,
    seed_level: str = "standard",
) -> str:
    """
    Inject Sentinel seed into Anthropic system prompt.

    Args:
        system: Original system prompt
        seed_level: Seed level to use (minimal, standard, full)

    Returns:
        System prompt with seed injected

    Raises:
        ValueError: If seed_level is invalid

    Example:
        system = inject_seed_anthropic("You are a helpful assistant")
    """
    _validate_seed_level(seed_level)
    _validate_system(system)

    try:
        sentinel = Sentinel(seed_level=seed_level)
    except Exception as e:
        logger.error(f"Failed to create Sentinel instance: {e}")
        raise RawAPIError(f"Failed to initialize Sentinel: {e}")

    seed = sentinel.get_seed()

    if system:
        return f"{seed}\n\n---\n\n{system}"
    return seed
