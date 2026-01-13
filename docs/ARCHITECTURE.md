# Sentinel Architecture

## Overview

Sentinel uses a layered validation architecture with two main components:

1. **Heuristic Layer**: Fast regex-based validation (580+ patterns, <10ms, free)
2. **Semantic Layer**: LLM-based validation for nuanced cases (1-5s, ~$0.0005/call)

### Validation 360° Architecture

Sentinel implements a 360° validation architecture that validates both input and output:

```
User Input → [validate_input] → AI + Seed → [validate_output] → Response
                  ↓                              ↓
           "Is this ATTACK?"            "Did SEED fail?"
```

```mermaid
flowchart LR
    subgraph Input["Input Validation"]
        UI[User Input] --> VI[validate_input]
        VI --> |Attack?| D1{Safe?}
        D1 -->|No| B1[Block]
        D1 -->|Yes| AI
    end

    subgraph Core["AI Processing"]
        AI[AI + Seed]
    end

    subgraph Output["Output Validation"]
        AI --> VO[validate_output]
        VO --> |Seed Failed?| D2{Safe?}
        D2 -->|No| B2[Block]
        D2 -->|Yes| R[Response]
    end

    style Input fill:#e3f2fd
    style Core fill:#fff3e0
    style Output fill:#e8f5e9
    style B1 fill:#ffcdd2
    style B2 fill:#ffcdd2
```

### Generic Validation Flow

The `validate()` method provides general-purpose validation:

```mermaid
flowchart TD
    A[Input Text] --> B{LayeredValidator}
    B --> C[THSPValidator<br/>Heuristic Layer]
    C --> D{Passes?}
    D -->|No| E[Return BLOCKED<br/>layer: heuristic]
    D -->|Yes| F{Semantic<br/>Enabled?}
    F -->|No| G[Return SAFE<br/>layer: heuristic]
    F -->|Yes| H[SemanticValidator<br/>LLM Layer]
    H --> I{Passes?}
    I -->|No| J[Return BLOCKED<br/>layer: semantic]
    I -->|Yes| K[Return SAFE<br/>layer: both]

    style C fill:#e1f5fe
    style H fill:#fff3e0
    style E fill:#ffcdd2
    style J fill:#ffcdd2
    style G fill:#c8e6c9
    style K fill:#c8e6c9
```

### THSP Protocol Gates

```mermaid
flowchart LR
    subgraph THSP["THSP Protocol"]
        T[Truth Gate] --> H[Harm Gate]
        H --> S[Scope Gate]
        S --> P[Purpose Gate]
    end

    Input[Content] --> T
    P --> Output{All Pass?}
    Output -->|Yes| Safe[✓ Safe]
    Output -->|No| Block[✗ Blocked]

    style T fill:#bbdefb
    style H fill:#ffcdd2
    style S fill:#fff9c4
    style P fill:#c8e6c9
```

### Module Hierarchy

```mermaid
classDiagram
    class Sentinel {
        +seed_level: SeedLevel
        +provider: str
        +get_seed()
        +validate()
        +chat()
    }

    class LayeredValidator {
        +config: ValidationConfig
        +stats: Dict
        +validate(content)
        +validate_input(text)
        +validate_output(output, input_context)
        +validate_action(action)
    }

    class THSPValidator {
        +patterns: 580+
        +validate(text)
        +check_gate(gate, text)
    }

    class SemanticValidator {
        +provider: str
        +model: str
        +validate(text)
    }

    class ValidationResult {
        +is_safe: bool
        +violations: List
        +layer: ValidationLayer
        +risk_level: RiskLevel
        +mode: ValidationMode
        +attack_types: List
        +seed_failed: bool
        +gates_failed: List
    }

    Sentinel --> LayeredValidator
    LayeredValidator --> THSPValidator
    LayeredValidator --> SemanticValidator
    LayeredValidator --> ValidationResult
    THSPValidator --> ValidationResult
    SemanticValidator --> ValidationResult
```

### Integration Architecture

```mermaid
flowchart TB
    subgraph Core["Core Module"]
        LV[LayeredValidator]
        THSP[THSPValidator]
        SEM[SemanticValidator]
    end

    subgraph Integrations["Framework Integrations"]
        LC[LangChain]
        CR[CrewAI]
        LL[LlamaIndex]
        DSP[DSPy]
        ANT[Anthropic SDK]
        OAI[OpenAI Agents]
    end

    subgraph Robotics["Robotics Integrations"]
        ROS[ROS2]
        ISA[Isaac Lab]
        HUM[Humanoid Safety]
    end

    subgraph Blockchain["Blockchain Integrations"]
        SOL[Solana Agent Kit]
        CB[Coinbase AgentKit]
        VIR[Virtuals Protocol]
    end

    LV --> THSP
    LV --> SEM

    LC --> LV
    CR --> LV
    LL --> LV
    DSP --> LV
    ANT --> LV
    OAI --> LV

    ROS --> Core
    ISA --> Core
    HUM --> Core

    SOL --> LV
    CB --> LV
    VIR --> LV

    style Core fill:#e3f2fd
    style Integrations fill:#f3e5f5
    style Robotics fill:#fff3e0
    style Blockchain fill:#e8f5e9
```

### Validation Sequence

```mermaid
sequenceDiagram
    participant App as Application
    participant LV as LayeredValidator
    participant TH as THSPValidator
    participant SE as SemanticValidator
    participant LLM as LLM Provider

    App->>LV: validate(content)
    LV->>TH: validate(content)
    TH->>TH: Check 580+ patterns

    alt Heuristic Blocks
        TH-->>LV: blocked, violations
        LV-->>App: ValidationResult(is_safe=false, layer=heuristic)
    else Heuristic Passes
        TH-->>LV: passed

        alt Semantic Enabled
            LV->>SE: validate(content)
            SE->>LLM: API call
            LLM-->>SE: analysis

            alt Semantic Blocks
                SE-->>LV: blocked, reasoning
                LV-->>App: ValidationResult(is_safe=false, layer=semantic)
            else Semantic Passes
                SE-->>LV: passed
                LV-->>App: ValidationResult(is_safe=true, layer=both)
            end
        else Semantic Disabled
            LV-->>App: ValidationResult(is_safe=true, layer=heuristic)
        end
    end
```

## Core Components

### LayeredValidator

The central orchestrator that coordinates heuristic and semantic validation.

```python
from sentinelseed.validation import LayeredValidator, ValidationConfig

config = ValidationConfig(
    use_heuristic=True,      # Always enabled (free, fast)
    use_semantic=True,       # Enable when API key available
    semantic_provider="openai",
    semantic_model="gpt-4o-mini",
)

validator = LayeredValidator(config=config)

# Generic validation
result = validator.validate("Check this content")

# Input validation (before AI processing)
input_result = validator.validate_input(user_input)
if input_result.is_attack:
    print(f"Attack detected: {input_result.attack_types}")
    # Do not send to AI

# Output validation (after AI processing)
output_result = validator.validate_output(ai_response, user_input)
if output_result.seed_failed:
    print(f"Seed failed! Gates: {output_result.gates_failed}")
    # Do not show to user
```

#### Validation Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `validate(content)` | General-purpose validation | `ValidationResult` |
| `validate_input(text)` | Detect attacks in user input | `ValidationResult` with `attack_types` |
| `validate_output(output, input_context)` | Detect seed failures in AI output | `ValidationResult` with `seed_failed`, `gates_failed` |

### THSPValidator (Heuristic)

Four-gate validation using 580+ regex patterns:

| Gate | Function | Examples |
|------|----------|----------|
| **Truth** | Detects misinformation, impersonation | Fake identities, false claims |
| **Harm** | Identifies violence, malware, theft | Weapons, hacking, doxxing |
| **Scope** | Catches jailbreaks, prompt injection | "Ignore previous instructions" |
| **Purpose** | Flags purposeless destruction | Destruction without benefit |

### InputValidator (Pre-AI Detection)

The InputValidator is a multi-detector system that runs **before** content reaches the AI. It uses a layered approach with multiple specialized detectors:

```
InputValidator v1.8.0
├── TextNormalizer (8 deobfuscation stages)
├── PatternDetector (580+ patterns, weight 1.0)
├── EscalationDetector (multi-turn, weight 1.1)
├── FramingDetector (70+ patterns, weight 1.2)
├── HarmfulRequestDetector (10 categories, weight 1.3)
├── IntentSignalDetector (compositional intent, weight 1.3)
├── SafeAgentDetector (embodied AI safety, weight 1.4)
├── EmbeddingDetector (semantic, weight 1.4, optional)
└── BenignContextDetector (false positive reduction)
```

#### Detectors

| Detector | Purpose | Weight |
|----------|---------|--------|
| **PatternDetector** | THSP patterns (jailbreak, injection, manipulation) | 1.0 |
| **EscalationDetector** | Multi-turn attacks like Crescendo | 1.1 |
| **FramingDetector** | Roleplay, fiction, DAN mode framing | 1.2 |
| **HarmfulRequestDetector** | Direct harmful content requests | 1.3 |
| **IntentSignalDetector** | Compositional analysis of action + target + context | 1.3 |
| **SafeAgentDetector** | Safety for embodied AI (based on SafeAgentBench) | 1.4 |
| **EmbeddingDetector** | Semantic similarity to known attacks | 1.4 |
| **BenignContextDetector** | Reduces false positives for legitimate contexts | N/A |

The BenignContextDetector identifies legitimate technical contexts (e.g., "kill process", "attack the problem") and reduces their scores. It is disabled when obfuscation is detected to prevent bypass.

#### Embedding-Based Detection

The EmbeddingDetector uses semantic similarity to catch attacks that evade keyword-based detection:

```python
from sentinelseed.detection.embeddings import (
    EmbeddingDetector,
    OpenAIEmbeddings,  # or OllamaEmbeddings
    AttackVectorDatabase,
)

# Load attack vectors
database = AttackVectorDatabase()
database.load_from_file("attack_vectors.json")

# Create detector with provider
provider = OpenAIEmbeddings()  # Uses OPENAI_API_KEY
detector = EmbeddingDetector(
    provider=provider,
    database=database,
)
```

**Supported Providers:**

| Provider | Model | Availability |
|----------|-------|--------------|
| OpenAI | text-embedding-3-small | Requires API key |
| Ollama | nomic-embed-text | Local, free |

**Graceful Degradation:** The system works without embedding support, falling back to heuristic detection.

### SentinelValidator (v3.0 Architecture)

The SentinelValidator provides a unified 4-gate orchestration system:

```
SentinelValidator v3.0
├── Gate 1 (L1): InputValidator (pre-AI heuristic)
├── Gate 2 (L3): OutputValidator (post-AI heuristic)
└── Gate 4 (L4): SentinelObserver (post-AI LLM analysis)
```

```python
from sentinelseed import SentinelValidator, SentinelConfig

# Configure with fallback policy
config = SentinelConfig(
    gate1_enabled=True,
    gate2_enabled=True,
    gate4_enabled=True,
    gate4_model="gpt-4o-mini",
    gate4_fallback="ALLOW_IF_L2_PASSED",  # Fallback when L4 unavailable
)

validator = SentinelValidator(config)

# Validate input only (Gate 1)
result = validator.validate_input("user message")

# Validate full dialogue (Gates 1, 2, and 4)
result = validator.validate_dialogue(
    input="user message",
    output="AI response",
)
```

**Gate 4 Fallback Policies:**

| Policy | Behavior when L4 fails |
|--------|------------------------|
| `BLOCK` | Always block (maximum security) |
| `ALLOW_IF_L2_PASSED` | Allow only if Gate 2 passed (balanced) |
| `ALLOW` | Always allow (maximum usability) |

The SentinelObserver (Gate 4) includes retry logic with exponential backoff for transient API failures.

### SemanticValidator

LLM-based validation for nuanced cases that require contextual understanding.

## Integration Pattern

### Standard Pattern: SentinelIntegration

Integrations that validate **text content** should inherit from `SentinelIntegration`:

```python
from sentinelseed.integrations._base import SentinelIntegration, ValidationConfig

class MyIntegration(SentinelIntegration):
    _integration_name = "my_integration"

    def __init__(self, api_key: str = None, **kwargs):
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=bool(api_key),
            semantic_api_key=api_key,
        )
        super().__init__(validation_config=config)

    def process(self, user_input: str):
        # Step 1: Validate user input
        input_result = self.validate_input(user_input)
        if not input_result.is_safe:
            raise ValueError(f"Attack detected: {input_result.attack_types}")

        # Step 2: Get AI response
        ai_response = self.call_ai(user_input)

        # Step 3: Validate AI output
        output_result = self.validate_output(ai_response, user_input)
        if not output_result.is_safe:
            raise ValueError(f"Seed failed: {output_result.gates_failed}")

        return ai_response
```

#### Inherited Methods

All integrations inheriting from `SentinelIntegration` have access to:

| Method | Description |
|--------|-------------|
| `validate(content)` | General-purpose validation |
| `validate_input(text)` | Detect attacks in user input |
| `validate_output(output, input_context)` | Detect seed failures in AI output |

### Integrations Using Standard Pattern

| Integration | Description |
|-------------|-------------|
| `langchain` | LangChain guards and chains |
| `crewai` | CrewAI multi-agent workflows |
| `langgraph` | LangGraph stateful agents |
| `llamaindex` | LlamaIndex query engines |
| `dspy` | DSPy prompt optimization |
| `letta` | Letta (MemGPT) stateful agents |
| `virtuals` | Virtuals Protocol GAME SDK |
| `solana_agent_kit` | Solana blockchain agents |
| `openguardrails` | OpenGuardrails combined validation |
| `agno` | Agno multi-agent framework |
| `google_adk` | Google Agent Development Kit |

## Domain-Specific Exceptions

Some integrations do NOT inherit from `SentinelIntegration` because they validate **domain-specific data** rather than text content.

### Exception: ROS2 Integration

**Reason**: Validates robot commands, sensor data, and motion plans (not text).

```python
# ros2/__init__.py validates:
# - Velocity commands (Twist messages)
# - Motion plans (JointTrajectory)
# - Sensor data (LaserScan, PointCloud)

from sentinelseed.integrations.ros2 import SentinelNode

node = SentinelNode()
# Validates ROS2 message types, not text
```

**Validation targets**:
- Maximum velocities (linear, angular)
- Force limits per ISO/TS 15066
- Collision detection zones
- Emergency stop conditions

### Exception: Isaac Lab Integration

**Reason**: Validates simulation actions and robot control commands.

```python
# isaac_lab/__init__.py validates:
# - Simulation step parameters
# - Robot joint positions
# - End-effector forces

from sentinelseed.integrations.isaac_lab import SentinelWrapper

wrapper = SentinelWrapper(env)
# Validates physics simulation parameters
```

**Validation targets**:
- Contact force limits
- Joint position bounds
- Simulation stability checks
- Emergency reset triggers

### Exception: Preflight Integration

**Reason**: Validates blockchain transactions and token contracts.

```python
# preflight/__init__.py validates:
# - Token contract safety (honeypot detection)
# - Slippage and price impact
# - DEX route analysis

from sentinelseed.integrations.preflight import PreflightClient

client = PreflightClient()
result = client.check_token("So11111111111111111111111111111111111111112")
# Returns honeypot risk, liquidity analysis, etc.
```

**Validation targets**:
- Token contract bytecode patterns
- Liquidity pool ratios
- Price manipulation indicators
- Rug pull risk factors

### Exception: Coinbase Domain Validators

**Reason**: The `coinbase/` integration contains domain-specific validators that validate blockchain addresses and transactions, not text.

| Component | Purpose | Validates |
|-----------|---------|-----------|
| `validators/address.py` | EVM address validation | Checksum, format, blocklists |
| `validators/transaction.py` | Transaction safety | Gas limits, value caps |
| `x402/` | HTTP 402 payment validation | Payment amounts, recipients |

These components use their own validation logic because:
1. Addresses have specific format rules (EIP-55 checksum)
2. Transactions have numeric constraints (gas, value)
3. x402 payments have protocol-specific requirements

### Exception: MCP Server

**Reason**: Uses MCP tool pattern (functions, not classes).

```python
# mcp_server/__init__.py provides MCP tools:
# - sentinel_validate: Validate text via THSP
# - sentinel_check_action: Validate agent actions

from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server

mcp = create_sentinel_mcp_server()
# Adds @mcp.tool() decorated functions
```

The MCP protocol requires tools to be functions decorated with `@mcp.tool()`. The integration creates a `LayeredValidator` internally for validation.

### Exception: AutoGPT Block

**Reason**: Uses AutoGPT Block SDK pattern (blocks inherit from `Block`, not `SentinelIntegration`).

```python
# autogpt_block/__init__.py provides:
# - SentinelValidationBlock
# - SentinelActionCheckBlock
# - SentinelSeedBlock

from sentinelseed.integrations.autogpt_block import validate_content

result = validate_content("Check this content")
# Uses LayeredValidator internally
```

AutoGPT blocks must inherit from `backend.sdk.Block`. The standalone functions (`validate_content`, `check_action`) create `LayeredValidator` instances internally.

## Configuration Recommendations

### Recommended Default Configuration

```python
from sentinelseed.validation import ValidationConfig

config = ValidationConfig(
    # Heuristic: ALWAYS enabled (free, <10ms)
    use_heuristic=True,

    # Semantic: Enable when API key available
    use_semantic=bool(api_key),
    semantic_api_key=api_key,
    semantic_provider="openai",  # or "anthropic"
    semantic_model="gpt-4o-mini",  # Cost-effective default

    # Optimization: Skip LLM if heuristic blocks
    skip_semantic_if_heuristic_blocks=True,

    # Safety: Fail closed on errors
    fail_closed=True,

    # Limits
    max_text_size=50 * 1024,  # 50KB
    validation_timeout=30.0,  # 30 seconds
)
```

### Cost Optimization

| Scenario | Configuration |
|----------|---------------|
| Development | `use_semantic=False` (heuristic only) |
| Production (cost-sensitive) | `skip_semantic_if_heuristic_blocks=True` |
| Production (high security) | `use_semantic=True`, `fail_closed=True` |

### Performance Characteristics

| Layer | Latency | Cost | Accuracy |
|-------|---------|------|----------|
| Heuristic | <10ms | Free | High for known patterns |
| Semantic | 1-5s | ~$0.0005/call | High for nuanced cases |
| Both | 1-5s | ~$0.0005/call | Highest |

## Version History

| Version | Changes |
|---------|---------|
| 2.24.0 | L4 retry system, Gate4Fallback policies, BenignContextDetector, multi-turn support |
| 2.23.1 | Added typing_extensions dependency |
| 2.23.0 | SentinelValidator v3.0 architecture, complete detection module, Python 3.10+ |
| 2.19.0 | LayeredValidator as central orchestrator, integration audit complete |
| 2.18.0 | Added Google ADK, Agno integrations |
| 2.17.0 | Added Letta, OpenAI Agents SDK integrations |
| 2.16.0 | Added Solana Agent Kit, Virtuals, MCP Server |
| 2.14.0 | Added Purpose gate (THS -> THSP) |
| 2.13.0 | Added semantic validation layer |

## Further Reading

- [CONTRIBUTING.md](CONTRIBUTING.md): How to contribute to Sentinel
- [PURPOSE_GATE.md](PURPOSE_GATE.md): Details on the Purpose gate
- [OWASP_LLM_TOP_10_MAPPING.md](OWASP_LLM_TOP_10_MAPPING.md): Security mapping
- [EU_AI_ACT_MAPPING.md](EU_AI_ACT_MAPPING.md): Regulatory compliance
