# Python SDK Reference

Complete API reference for the Sentinel Python SDK (`sentinelseed`).

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Module](#core-module)
  - [Sentinel Class](#sentinel-class)
  - [SeedLevel Enum](#seedlevel-enum)
  - [get_seed Function](#get_seed-function)
- [Validation Module](#validation-module)
  - [LayeredValidator](#layeredvalidator)
  - [AsyncLayeredValidator](#asynclayeredvalidator)
  - [ValidationResult](#validationresult)
  - [ValidationConfig](#validationconfig)
  - [ValidationLayer Enum](#validationlayer-enum)
  - [RiskLevel Enum](#risklevel-enum)
- [Detection Module](#detection-module)
  - [InputValidator](#inputvalidator)
  - [EmbeddingDetector](#embeddingdetector)
  - [EmbeddingProvider](#embeddingprovider)
  - [AttackVectorDatabase](#attackvectordatabase)
- [Memory Integrity](#memory-integrity)
  - [MemoryIntegrityChecker](#memoryintegritychecker)
  - [MemoryEntry](#memoryentry)
  - [SignedMemoryEntry](#signedmemoryentry)
- [Fiduciary AI](#fiduciary-ai)
  - [FiduciaryValidator](#fiduciaryvalidator)
  - [FiduciaryGuard](#fiduciaryguard)
  - [UserContext](#usercontext)
  - [FiduciaryResult](#fiduciaryresult)
- [Database Guard](#database-guard)
  - [DatabaseGuard](#databaseguard)
  - [QueryValidationResult](#queryvalidationresult)
- [Compliance](#compliance)
  - [EUAIActComplianceChecker](#euaiactcompliancechecker)
  - [OWASPLLMChecker](#owaspllmchecker)
  - [OWASPAgenticChecker](#owaspagenticchecker)
  - [CSAAICMComplianceChecker](#csaaicmcompliancechecker)
- [Exceptions](#exceptions)
- [Interfaces](#interfaces)
- [Type Definitions](#type-definitions)

---

## Installation

```bash
pip install sentinelseed
```

With optional dependencies:

```bash
# For LangChain integration
pip install sentinelseed[langchain]

# For all integrations
pip install sentinelseed[all]
```

---

## Quick Start

```python
from sentinelseed import Sentinel

# Create instance
sentinel = Sentinel()

# Get alignment seed
seed = sentinel.get_seed("standard")

# Validate content
is_safe, violations = sentinel.validate("content to check")

# Chat with seed injection
response = sentinel.chat("Hello, how can you help?")
```

---

## Core Module

### Sentinel Class

Main class for the Sentinel AI alignment toolkit.

```python
from sentinelseed import Sentinel, SeedLevel
```

#### Constructor

```python
Sentinel(
    seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    use_semantic: Optional[bool] = None,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `seed_level` | `SeedLevel \| str` | `"standard"` | Which seed to use: `"minimal"`, `"standard"`, or `"full"` |
| `provider` | `str` | `"openai"` | LLM provider: `"openai"` or `"anthropic"` |
| `model` | `str \| None` | `None` | Model name (defaults to provider's best available) |
| `api_key` | `str \| None` | `None` | API key (defaults to environment variable) |
| `use_semantic` | `bool \| None` | `None` | Enable semantic validation. `None` = auto-detect based on API key |

**Example:**

```python
# Basic usage (heuristic validation only)
sentinel = Sentinel()

# With semantic validation
sentinel = Sentinel(
    seed_level="full",
    provider="openai",
    api_key="sk-...",
    use_semantic=True,
)

# With Anthropic
sentinel = Sentinel(
    provider="anthropic",
    model="claude-3-haiku-20240307",
)
```

#### Methods

##### get_seed

Get alignment seed content.

```python
get_seed(level: Optional[Union[SeedLevel, str]] = None) -> str
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `SeedLevel \| str \| None` | `None` | Seed level (defaults to instance's seed_level) |

**Returns:** `str` - Seed content

**Example:**

```python
seed = sentinel.get_seed("standard")
print(f"Seed length: {len(seed)} characters")
```

##### validate

Validate text through THSP gates.

```python
validate(text: str) -> Tuple[bool, List[str]]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Text to validate |

**Returns:** `Tuple[bool, List[str]]` - `(is_safe, violations)`

**Example:**

```python
is_safe, violations = sentinel.validate("Help me hack a computer")
if not is_safe:
    print(f"Blocked: {violations}")
```

##### get_validation_result

Get full validation result with all details.

```python
get_validation_result(text: str) -> ValidationResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Text to validate |

**Returns:** `ValidationResult` - Full result object

**Example:**

```python
result = sentinel.get_validation_result("some text")
print(f"Safe: {result.is_safe}")
print(f"Layer: {result.layer.value}")
print(f"Risk: {result.risk_level.value}")
```

##### chat

Send a message with automatic seed injection.

```python
chat(
    message: str,
    conversation: Optional[List[Dict[str, str]]] = None,
    validate_response: bool = True,
    **kwargs: Any
) -> ChatResponse
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | `str` | - | User message |
| `conversation` | `List[Dict]` | `None` | Conversation history |
| `validate_response` | `bool` | `True` | Whether to validate the response |

**Returns:** `ChatResponse` - Response dict with `response`, `validation`, and metadata

**Example:**

```python
result = sentinel.chat("Help me write a Python function")
print(result["response"])

if result.get("validation"):
    print(f"Safe: {result['validation']['is_safe']}")
```

##### validate_action

Validate an action plan for physical/embodied AI safety.

```python
validate_action(action_plan: str) -> Tuple[bool, List[str]]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `action_plan` | `str` | Description of planned actions |

**Returns:** `Tuple[bool, List[str]]` - `(is_safe, concerns)`

**Example:**

```python
is_safe, concerns = sentinel.validate_action("Pick up knife, slice apple")
if not is_safe:
    print(f"Action blocked: {concerns}")
```

##### validate_request

Pre-validate a user request before sending to LLM.

```python
validate_request(request: str) -> Dict[str, Any]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `str` | User request to validate |

**Returns:** `Dict` with `should_proceed`, `concerns`, `risk_level`

**Example:**

```python
result = sentinel.validate_request("Tell me how to bypass security")
if not result["should_proceed"]:
    print(f"Risk: {result['risk_level']}")
    print(f"Concerns: {result['concerns']}")
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `seed` | `str` | Current seed content |
| `seed_level` | `SeedLevel` | Current seed level |
| `provider` | `str` | LLM provider name |
| `model` | `str` | Model name |
| `use_semantic` | `bool` | Whether semantic validation is enabled |

---

### SeedLevel Enum

Available seed levels with different size/coverage trade-offs.

```python
from sentinelseed import SeedLevel
```

| Value | Token Estimate | Description |
|-------|----------------|-------------|
| `MINIMAL` | ~360 | Essential THSP gates only |
| `STANDARD` | ~1K | Balanced safety with examples |
| `FULL` | ~1.9K | Comprehensive with anti-self-preservation |

**Example:**

```python
from sentinelseed import Sentinel, SeedLevel

sentinel = Sentinel(seed_level=SeedLevel.FULL)
# or
sentinel = Sentinel(seed_level="full")
```

---

### get_seed Function

Convenience function to get an alignment seed without creating a Sentinel instance.

```python
from sentinelseed import get_seed

seed = get_seed("standard")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `str` | `"standard"` | Seed level |

**Returns:** `str` - Seed content

---

## Validation Module

### LayeredValidator

Two-layer validation combining heuristic (700+ patterns) and semantic (LLM-based) analysis.

```python
from sentinelseed import LayeredValidator, ValidationConfig
```

#### Constructor

```python
LayeredValidator(
    config: Optional[ValidationConfig] = None,
    semantic_api_key: Optional[str] = None,
    use_semantic: bool = False,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `ValidationConfig` | `None` | Configuration object |
| `semantic_api_key` | `str` | `None` | API key for semantic validation |
| `use_semantic` | `bool` | `False` | Enable semantic layer |

**Example:**

```python
# Heuristic only (no API required)
validator = LayeredValidator()

# With semantic validation
validator = LayeredValidator(
    semantic_api_key="sk-...",
    use_semantic=True,
)

# With full configuration
config = ValidationConfig(
    use_semantic=True,
    semantic_api_key="sk-...",
    semantic_provider="openai",
    fail_closed=True,
)
validator = LayeredValidator(config=config)
```

#### Methods

##### validate

Validate content through layered validation.

```python
validate(content: str) -> ValidationResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | `str` | Text content to validate |

**Returns:** `ValidationResult`

**Example:**

```python
result = validator.validate("some content")
if not result.is_safe:
    print(f"Blocked by {result.layer.value}: {result.violations}")
```

##### validate_action

Validate an action with arguments.

```python
validate_action(
    action_name: str,
    action_args: Optional[Dict[str, Any]] = None,
    purpose: str = "",
) -> ValidationResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `action_name` | `str` | Name of the action |
| `action_args` | `Dict` | Arguments to the action |
| `purpose` | `str` | Stated purpose for the action |

**Returns:** `ValidationResult`

**Example:**

```python
result = validator.validate_action(
    action_name="delete_file",
    action_args={"path": "/tmp/cache.txt"},
    purpose="Clean up temporary files",
)
```

##### validate_action_plan

Validate an action plan description.

```python
validate_action_plan(plan: str) -> ValidationResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `plan` | `str` | Action plan description |

**Returns:** `ValidationResult`

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `stats` | `Dict[str, Any]` | Validation statistics |

---

### AsyncLayeredValidator

Async version of LayeredValidator for async frameworks.

```python
from sentinelseed import AsyncLayeredValidator
```

#### Methods

```python
async def validate(self, content: str) -> ValidationResult
async def validate_action(
    self,
    action_name: str,
    action_args: Optional[Dict[str, Any]] = None,
    purpose: str = "",
) -> ValidationResult
```

**Example:**

```python
validator = AsyncLayeredValidator(
    semantic_api_key="sk-...",
    use_semantic=True,
)

result = await validator.validate("content")
```

---

### ValidationResult

Dataclass containing validation results.

```python
from sentinelseed import ValidationResult
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `is_safe` | `bool` | Overall safety assessment |
| `layer` | `ValidationLayer` | Which layer made the decision |
| `violations` | `List[str]` | List of violation messages |
| `risk_level` | `RiskLevel` | Assessed risk level |
| `reasoning` | `str \| None` | Explanation (from semantic layer) |
| `heuristic_passed` | `bool \| None` | Whether heuristic layer passed |
| `semantic_passed` | `bool \| None` | Whether semantic layer passed |
| `error` | `str \| None` | Error message if validation failed |
| `metadata` | `Dict[str, Any]` | Additional metadata |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `should_proceed` | `bool` | Alias for `is_safe` (backwards compat) |
| `concerns` | `List[str]` | Alias for `violations` |
| `blocked` | `bool` | Inverse of `is_safe` |
| `blocked_by_heuristic` | `bool` | Whether blocked by heuristic layer |
| `blocked_by_semantic` | `bool` | Whether blocked by semantic layer |

#### Methods

##### to_dict

Convert to dictionary for serialization.

```python
to_dict() -> Dict[str, Any]
```

##### to_legacy_dict

Convert to legacy format for backwards compatibility.

```python
to_legacy_dict() -> Dict[str, Any]
```

**Returns:** Dict with `should_proceed`, `concerns`, `risk_level`

#### Factory Methods

```python
# Create safe result
result = ValidationResult.safe(layer=ValidationLayer.BOTH)

# Create blocked result
result = ValidationResult.from_blocked(
    violations=["Harmful content detected"],
    layer=ValidationLayer.HEURISTIC,
    risk_level=RiskLevel.HIGH,
)

# Create error result
result = ValidationResult.from_error("Validation timeout")
```

---

### ValidationConfig

Configuration dataclass for LayeredValidator.

```python
from sentinelseed import ValidationConfig
```

#### Constructor

```python
ValidationConfig(
    use_heuristic: bool = True,
    use_semantic: bool = False,
    semantic_provider: str = "openai",
    semantic_model: Optional[str] = None,
    semantic_api_key: Optional[str] = None,
    semantic_base_url: Optional[str] = None,
    validation_timeout: float = 30.0,
    fail_closed: bool = False,
    skip_semantic_if_heuristic_blocks: bool = True,
    max_text_size: int = 50_000,
    log_validations: bool = True,
    log_level: str = "info",
)
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_heuristic` | `bool` | `True` | Enable heuristic layer |
| `use_semantic` | `bool` | `False` | Enable semantic layer |
| `semantic_provider` | `str` | `"openai"` | Provider: `"openai"`, `"anthropic"`, `"openai_compatible"` |
| `semantic_model` | `str` | `None` | Model name |
| `semantic_api_key` | `str` | `None` | API key |
| `semantic_base_url` | `str` | `None` | Custom base URL |
| `validation_timeout` | `float` | `30.0` | Timeout in seconds |
| `fail_closed` | `bool` | `False` | Block on errors |
| `skip_semantic_if_heuristic_blocks` | `bool` | `True` | Skip semantic if heuristic blocks |
| `max_text_size` | `int` | `50_000` | Max text size in bytes |
| `log_validations` | `bool` | `True` | Enable logging |
| `log_level` | `str` | `"info"` | Log level |

#### Provider Examples

**OpenAI (default):**
```python
config = ValidationConfig(
    use_semantic=True,
    semantic_provider="openai",
    semantic_model="gpt-4o-mini",
    semantic_api_key="sk-...",
)
```

**Anthropic:**
```python
config = ValidationConfig(
    use_semantic=True,
    semantic_provider="anthropic",
    semantic_model="claude-3-haiku-20240307",
    semantic_api_key="sk-ant-...",
)
```

**Meta Llama API (official):**
```python
config = ValidationConfig(
    use_semantic=True,
    semantic_provider="openai_compatible",
    semantic_base_url="https://api.llama.com/compat/v1",
    semantic_model="Llama-3.3-70B-Instruct",
    semantic_api_key="...",  # From llama.com dashboard
)
```

**DeepSeek (OpenAI-compatible):**
```python
config = ValidationConfig(
    use_semantic=True,
    semantic_provider="openai_compatible",
    semantic_base_url="https://api.deepseek.com/v1",
    semantic_model="deepseek-chat",  # or "deepseek-reasoner"
    semantic_api_key="sk-...",
)
```

**Groq (OpenAI-compatible):**
```python
config = ValidationConfig(
    use_semantic=True,
    semantic_provider="openai_compatible",
    semantic_base_url="https://api.groq.com/openai/v1",
    semantic_model="llama-3.1-70b-versatile",
    semantic_api_key="gsk_...",
)
```

**Together AI (OpenAI-compatible):**
```python
config = ValidationConfig(
    use_semantic=True,
    semantic_provider="openai_compatible",
    semantic_base_url="https://api.together.xyz/v1",
    semantic_model="meta-llama/Llama-3-70b-chat-hf",
    semantic_api_key="...",
)
```

**Ollama (local, no API key):**
```python
config = ValidationConfig(
    use_semantic=True,
    semantic_provider="openai_compatible",
    semantic_base_url="http://localhost:11434/v1",
    semantic_model="llama3.1",
)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `semantic_enabled` | `bool` | Whether semantic is configured and enabled |
| `heuristic_only` | `bool` | Whether only heuristic is enabled |
| `effective_model` | `str` | Model that will be used |

#### Methods

##### with_semantic

Create a copy with semantic validation enabled.

```python
with_semantic(
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> ValidationConfig
```

##### from_env

Create configuration from environment variables.

```python
@classmethod
from_env(prefix: str = "SENTINEL_") -> ValidationConfig
```

**Environment variables:**
- `SENTINEL_USE_HEURISTIC`
- `SENTINEL_USE_SEMANTIC`
- `SENTINEL_SEMANTIC_PROVIDER`
- `SENTINEL_SEMANTIC_MODEL`
- `SENTINEL_SEMANTIC_API_KEY`
- `SENTINEL_VALIDATION_TIMEOUT`
- `SENTINEL_FAIL_CLOSED`
- `SENTINEL_MAX_TEXT_SIZE`

#### Preset Configurations

```python
from sentinelseed.validation import DEFAULT_CONFIG, STRICT_CONFIG

# Default: heuristic only
validator = LayeredValidator(config=DEFAULT_CONFIG)

# Strict: fail-closed, shorter timeout
validator = LayeredValidator(config=STRICT_CONFIG)
```

---

### ValidationLayer Enum

Indicates which validation layer made the decision.

```python
from sentinelseed import ValidationLayer
```

| Value | Description |
|-------|-------------|
| `HEURISTIC` | Decision by heuristic layer (fast, no API) |
| `SEMANTIC` | Decision by semantic layer (accurate, uses API) |
| `BOTH` | Content passed both layers |
| `NONE` | No validation performed |
| `ERROR` | Validation failed with error |

---

### RiskLevel Enum

Risk assessment levels.

```python
from sentinelseed import ValidationRiskLevel
```

| Value | Description |
|-------|-------------|
| `LOW` | Content appears safe |
| `MEDIUM` | Some concerns, may be acceptable |
| `HIGH` | Significant safety concerns |
| `CRITICAL` | Severe or immediate risks |

---

## Detection Module

Pre-AI detection system for input validation.

### InputValidator

Multi-detector system for validating input before AI processing.

```python
from sentinelseed.detection import InputValidator
```

#### Constructor

```python
InputValidator(
    config: Optional[InputValidatorConfig] = None,
    use_embeddings: bool = False,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `InputValidatorConfig \| None` | `None` | Configuration object |
| `use_embeddings` | `bool` | `False` | Enable embedding-based detection |

#### Methods

##### validate

Validate input text with all registered detectors.

```python
validate(
    text: str,
    context: Optional[Dict[str, Any]] = None,
) -> ValidationResult
```

**Example:**

```python
validator = InputValidator()
result = validator.validate("user input text")

if not result.is_safe:
    print(f"Attack detected: {result.attack_types}")
```

### EmbeddingDetector

Semantic similarity-based detector using embeddings.

```python
from sentinelseed.detection.embeddings import (
    EmbeddingDetector,
    EmbeddingDetectorConfig,
    OpenAIEmbeddings,
    OllamaEmbeddings,
    AttackVectorDatabase,
)
```

#### Constructor

```python
EmbeddingDetector(
    provider: Optional[EmbeddingProvider] = None,
    database: Optional[AttackVectorDatabase] = None,
    embed_config: Optional[EmbeddingDetectorConfig] = None,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | `EmbeddingProvider \| None` | `None` | Embedding provider (OpenAI, Ollama) |
| `database` | `AttackVectorDatabase \| None` | `None` | Database of known attack vectors |
| `embed_config` | `EmbeddingDetectorConfig \| None` | `None` | Detection configuration |

**Example:**

```python
# Create provider
provider = OpenAIEmbeddings()  # Uses OPENAI_API_KEY

# Load attack database
database = AttackVectorDatabase()
database.load_from_file("attack_vectors.json")

# Create detector
detector = EmbeddingDetector(
    provider=provider,
    database=database,
)

# Check if ready
if detector.is_ready():
    result = detector.detect("potentially harmful text")
```

### EmbeddingProvider

Base class for embedding providers.

| Provider | Class | Model |
|----------|-------|-------|
| OpenAI | `OpenAIEmbeddings` | text-embedding-3-small |
| Ollama | `OllamaEmbeddings` | nomic-embed-text |

### AttackVectorDatabase

In-memory database of attack embeddings.

```python
from sentinelseed.detection.embeddings import AttackVectorDatabase
```

#### Methods

| Method | Description |
|--------|-------------|
| `load_from_file(path)` | Load vectors from JSON file |
| `save_to_file(path)` | Save vectors to JSON file |
| `search_similar(embedding, threshold)` | Find similar attack vectors |
| `add_vector(id, embedding, category)` | Add a new attack vector |
| `get_stats()` | Get database statistics |

---

## Memory Integrity

Module for protecting AI agent memory from injection attacks.

### MemoryIntegrityChecker

Cryptographic verification for AI agent memory.

```python
from sentinelseed import MemoryIntegrityChecker
```

#### Constructor

```python
MemoryIntegrityChecker(
    secret_key: str,
    algorithm: str = "sha256",
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `secret_key` | `str` | - | Secret key for HMAC signing |
| `algorithm` | `str` | `"sha256"` | Hash algorithm |

**Example:**

```python
checker = MemoryIntegrityChecker(secret_key="your-secret-key")
```

#### Methods

##### sign_entry

Sign a memory entry for integrity verification.

```python
sign_entry(entry: Union[MemoryEntry, Dict]) -> SignedMemoryEntry
```

**Example:**

```python
signed = checker.sign_entry({
    "content": "User requested transfer of 10 SOL",
    "source": "discord",
    "timestamp": "2025-12-11T10:00:00Z",
})
```

##### verify_entry

Verify a signed memory entry.

```python
verify_entry(entry: SignedMemoryEntry) -> MemoryValidationResult
```

**Returns:** `MemoryValidationResult` with `valid`, `reason`, etc.

**Example:**

```python
result = checker.verify_entry(signed_entry)
if not result.valid:
    raise MemoryTamperingDetected(result.reason)
```

---

### MemoryEntry

Data class for memory entries.

```python
from sentinelseed import MemoryEntry
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `content` | `str` | Memory content |
| `source` | `str` | Source of the memory |
| `timestamp` | `str` | ISO timestamp |
| `metadata` | `Dict` | Additional metadata |

---

### SignedMemoryEntry

Memory entry with cryptographic signature.

```python
from sentinelseed import SignedMemoryEntry
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `content` | `str` | Memory content |
| `source` | `str` | Source |
| `timestamp` | `str` | Timestamp |
| `signature` | `str` | HMAC signature |
| `metadata` | `Dict` | Metadata |

---

## Fiduciary AI

Module ensuring AI acts in users' best interest.

### FiduciaryValidator

Validates AI actions against fiduciary duties.

```python
from sentinelseed import FiduciaryValidator
```

#### Constructor

```python
FiduciaryValidator(
    strict_mode: bool = False,
    require_all_duties: bool = False,
    custom_rules: Optional[List[Callable]] = None,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `strict_mode` | `bool` | `False` | Any violation makes action non-compliant |
| `require_all_duties` | `bool` | `False` | All duties must pass |
| `custom_rules` | `List[Callable]` | `None` | Additional validation rules |

**Example:**

```python
validator = FiduciaryValidator(strict_mode=True)
```

#### Methods

##### validate_action

Validate an action against fiduciary duties.

```python
validate_action(
    action: str,
    user_context: Optional[UserContext] = None,
    proposed_outcome: Optional[Dict[str, Any]] = None,
) -> FiduciaryResult
```

**Example:**

```python
result = validator.validate_action(
    action="Recommend high-risk investment",
    user_context=UserContext(risk_tolerance="low"),
)

if not result.compliant:
    for violation in result.violations:
        print(f"{violation.duty}: {violation.description}")
```

##### get_stats

Get validation statistics.

```python
get_stats() -> Dict[str, int]
```

---

### FiduciaryGuard

High-level guard for enforcing fiduciary principles.

```python
from sentinelseed import FiduciaryGuard
```

#### Constructor

```python
FiduciaryGuard(
    validator: Optional[FiduciaryValidator] = None,
    block_on_violation: bool = True,
    log_decisions: bool = True,
    max_log_size: int = 1000,
)
```

#### Methods

##### protect (decorator)

Decorator to protect a function with fiduciary validation.

```python
@guard.protect
def recommend_investment(user_id: str, amount: float) -> str:
    return f"Invest {amount} in stocks"

# Function will be validated before execution
result = recommend_investment("user123", 1000)
```

##### validate_and_execute

Validate an action and execute if compliant.

```python
validate_and_execute(
    action: Callable,
    user_context: Optional[UserContext] = None,
    action_description: Optional[str] = None,
) -> Tuple[Any, FiduciaryResult]
```

---

### UserContext

User context for fiduciary assessment.

```python
from sentinelseed import UserContext
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `None` | User identifier |
| `goals` | `List[str]` | `[]` | User's stated goals |
| `constraints` | `List[str]` | `[]` | User's constraints |
| `risk_tolerance` | `RiskTolerance` | `MODERATE` | Risk tolerance level |
| `preferences` | `Dict` | `{}` | User preferences |
| `history` | `List[Dict]` | `[]` | Interaction history |
| `sensitive_topics` | `List[str]` | `[]` | Topics to protect |

**Example:**

```python
context = UserContext(
    user_id="user123",
    goals=["save for retirement"],
    risk_tolerance="low",
    sensitive_topics=["health", "finances"],
)
```

---

### FiduciaryResult

Result of fiduciary validation.

```python
from sentinelseed import FiduciaryResult
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `compliant` | `bool` | Whether action is compliant |
| `violations` | `List[Violation]` | List of violations |
| `passed_duties` | `List[FiduciaryDuty]` | Duties that passed |
| `explanations` | `Dict[str, str]` | Explanations per check |
| `confidence` | `float` | Confidence score (0-1) |
| `timestamp` | `str` | ISO timestamp |

---

### Convenience Functions

```python
from sentinelseed import validate_fiduciary, is_fiduciary_compliant

# One-off validation
result = validate_fiduciary(
    action="action description",
    user_context={"risk_tolerance": "low"},
)

# Quick check
if is_fiduciary_compliant(action, user_context):
    execute_action()
```

---

## Database Guard

Module protecting databases from AI agent data exfiltration.

### DatabaseGuard

Validates SQL queries before execution.

```python
from sentinelseed import DatabaseGuard
```

#### Constructor

```python
DatabaseGuard(
    max_rows_per_query: int = 1000,
    require_where_clause: bool = False,
    block_patterns: Optional[List[str]] = None,
    allowed_tables: Optional[List[str]] = None,
    blocked_tables: Optional[List[str]] = None,
    strict_mode: bool = False,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_rows_per_query` | `int` | `1000` | Maximum rows allowed |
| `require_where_clause` | `bool` | `False` | Require WHERE clause |
| `block_patterns` | `List[str]` | `None` | SQL patterns to block |
| `allowed_tables` | `List[str]` | `None` | Whitelist of tables |
| `blocked_tables` | `List[str]` | `None` | Blacklist of tables |
| `strict_mode` | `bool` | `False` | Raise exception on violation |

**Example:**

```python
guard = DatabaseGuard(
    max_rows_per_query=100,
    require_where_clause=True,
    blocked_tables=["users_private", "api_keys"],
)
```

#### Methods

##### validate

Validate a SQL query.

```python
validate(query: str) -> QueryValidationResult
```

**Example:**

```python
result = guard.validate("SELECT * FROM users")
if result.blocked:
    print(f"Query blocked: {result.reason}")
else:
    cursor.execute(query)
```

---

### QueryValidationResult

Result of query validation.

```python
from sentinelseed import QueryValidationResult
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `blocked` | `bool` | Whether query is blocked |
| `reason` | `str` | Reason for blocking |
| `query_type` | `QueryType` | Type of query (SELECT, INSERT, etc.) |
| `risk_level` | `RiskLevel` | Assessed risk level |
| `violations` | `List[PolicyViolation]` | Policy violations |
| `sensitive_data` | `List[SensitiveDataMatch]` | Sensitive data detected |
| `has_sensitive_data` | `bool` | Whether sensitive data is accessed |

---

### Convenience Functions

```python
from sentinelseed import validate_query, is_safe_query

# Validate with options
result = validate_query(query, max_rows_per_query=100)

# Quick check
if is_safe_query(query):
    execute(query)
```

---

## Compliance

Modules for regulatory compliance checking.

### EUAIActComplianceChecker

Checks content against EU AI Act (Regulation 2024/1689).

```python
from sentinelseed.compliance import EUAIActComplianceChecker
```

#### Constructor

```python
EUAIActComplianceChecker(
    api_key: Optional[str] = None,
    fail_closed: bool = False,
)
```

#### Methods

##### check_compliance

Check content for EU AI Act compliance.

```python
check_compliance(
    content: str,
    context: str = "general",
    system_type: str = "general",
) -> ComplianceResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | `str` | Content to check |
| `context` | `str` | Context: `"general"`, `"healthcare"`, `"financial"`, etc. |
| `system_type` | `str` | System type: `"general"`, `"high_risk"`, `"prohibited"` |

**Example:**

```python
checker = EUAIActComplianceChecker(api_key="sk-...")
result = checker.check_compliance(
    content="Based on your social behavior...",
    context="financial",
    system_type="high_risk",
)

if not result.compliant:
    print(f"Violations: {result.article_5_violations}")
```

---

### OWASPLLMChecker

Checks for OWASP LLM Top 10 vulnerabilities.

```python
from sentinelseed.compliance import OWASPLLMChecker
```

#### Methods

##### check_input

Check user input for vulnerabilities (pre-inference).

```python
check_input(content: str) -> OWASPComplianceResult
```

##### check_output

Check LLM output for vulnerabilities (post-inference).

```python
check_output(content: str) -> OWASPComplianceResult
```

##### check_pipeline

Check full pipeline (input + output).

```python
check_pipeline(
    input_content: str,
    output_content: str,
) -> OWASPComplianceResult
```

---

### OWASPAgenticChecker

Checks for OWASP Top 10 for Agentic Applications (2026).

```python
from sentinelseed.compliance import OWASPAgenticChecker
```

#### Methods

##### get_coverage_assessment

Get complete coverage assessment.

```python
get_coverage_assessment() -> AgenticComplianceResult
```

**Example:**

```python
checker = OWASPAgenticChecker()
result = checker.get_coverage_assessment()
print(f"Coverage: {result.overall_coverage}%")
```

##### check_vulnerability

Check specific vulnerability.

```python
check_vulnerability(vuln: AgenticVulnerability) -> AgenticFinding
```

---

### CSAAICMComplianceChecker

Checks against CSA AI Controls Matrix.

```python
from sentinelseed.compliance import CSAAICMComplianceChecker
```

#### Methods

##### check_compliance

Check content against AICM controls.

```python
check_compliance(
    content: str,
    domains: Optional[List[AICMDomain]] = None,
) -> AICMComplianceResult
```

---

### Convenience Functions

```python
from sentinelseed.compliance import (
    check_eu_ai_act_compliance,
    check_owasp_llm_compliance,
    get_owasp_agentic_coverage,
    check_csa_aicm_compliance,
)

# One-off checks
result = check_eu_ai_act_compliance(content, api_key="...")
result = check_owasp_llm_compliance(content, validation_type="output")
result = get_owasp_agentic_coverage()
result = check_csa_aicm_compliance(content, api_key="...")
```

---

## Exceptions

Exception hierarchy for Sentinel errors.

```python
from sentinelseed import (
    SentinelError,
    ValidationError,
    ConfigurationError,
    IntegrationError,
)
```

### SentinelError

Base exception for all Sentinel errors.

```python
class SentinelError(Exception):
    message: str
    context: Dict[str, Any]
```

### ValidationError

Raised when validation fails.

```python
class ValidationError(SentinelError):
    violations: List[str]
    risk_level: Optional[str]
```

**Example:**

```python
try:
    result = validator.validate(content)
except ValidationError as e:
    print(f"Violations: {e.violations}")
    print(f"Risk: {e.risk_level}")
```

### ConfigurationError

Raised for configuration issues.

```python
class ConfigurationError(SentinelError):
    parameter: Optional[str]
```

### IntegrationError

Raised for integration-specific errors.

```python
class IntegrationError(SentinelError):
    integration: Optional[str]
    operation: Optional[str]
```

---

## Interfaces

Protocol classes for type hints and dependency injection.

### Validator Protocol

```python
from sentinelseed import Validator

class Validator(Protocol):
    def validate(self, content: str) -> ValidationResult: ...
    def validate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> ValidationResult: ...
    @property
    def stats(self) -> Dict[str, Any]: ...
```

### AsyncValidator Protocol

```python
from sentinelseed import AsyncValidator

class AsyncValidator(Protocol):
    async def validate(self, content: str) -> ValidationResult: ...
    async def validate_action(...) -> ValidationResult: ...
    @property
    def stats(self) -> Dict[str, Any]: ...
```

---

## Type Definitions

TypedDicts for type-safe returns.

### ChatResponse

```python
from sentinelseed.core.types import ChatResponse

class ChatResponse(TypedDict):
    response: str
    model: str
    provider: str
    seed_level: str
    validation: NotRequired[ValidationInfo]
```

### ValidationInfo

```python
from sentinelseed.core.types import ValidationInfo

class ValidationInfo(TypedDict):
    is_safe: bool
    violations: List[str]
    layer: str
    risk_level: str
```

### ValidatorStats

```python
from sentinelseed.core.types import ValidatorStats

class ValidatorStats(TypedDict, total=False):
    total_validations: int
    heuristic_blocks: int
    semantic_blocks: int
    allowed: int
    errors: int
    timeouts: int
    avg_latency_ms: float
    block_rate: float
```

---

## See Also

- [REST API Reference](rest-api.md)
- [JavaScript SDK Reference](javascript-sdk.md)
- [Integration READMEs](../../src/sentinelseed/integrations/)
- [Architecture Overview](../ARCHITECTURE.md)
