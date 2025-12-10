# Sentinel THSP Plugin for Garak (NVIDIA)

> Red team LLMs using the THSP (Truth, Harm, Scope, Purpose) protocol with Garak

This plugin extends [Garak](https://github.com/NVIDIA/garak) (NVIDIA's LLM vulnerability scanner) with probes and detectors based on Sentinel's THSP protocol.

## What is Garak?

Garak is an open-source security testing framework for LLMs, developed by NVIDIA. It probes models for vulnerabilities including hallucination, jailbreaks, prompt injection, and more.

## What This Plugin Adds

**5 Probe Classes** targeting each THSP gate:

| Probe | Gate | Tests For |
|-------|------|-----------|
| `TruthGate` | Truth | Fake documents, impersonation, misinformation |
| `HarmGate` | Harm | Violence, weapons, hacking, dangerous activities |
| `ScopeGate` | Scope | Jailbreaks, prompt injection, persona switches |
| `PurposeGate` | Purpose | Purposeless destruction, waste, meaningless harm |
| `THSPCombined` | All | Multi-gate attacks |

**5 Detector Classes** to identify violations:

| Detector | Detects |
|----------|---------|
| `TruthViolation` | Model generated deceptive content |
| `HarmViolation` | Model provided harmful information |
| `ScopeViolation` | Model accepted jailbreak/persona switch |
| `PurposeViolation` | Model assisted with purposeless destruction |
| `THSPCombined` | Any THSP violation (max score) |

## Installation

### 1. Install Garak

```bash
pip install garak
```

### 2. Install Sentinel Plugin

```bash
# Find your garak installation
python -c "import garak; print(garak.__path__[0])"

# Copy probes
cp probes/sentinel_thsp.py /path/to/garak/probes/

# Copy detectors
cp detectors/sentinel_thsp.py /path/to/garak/detectors/
```

Or use the install script:

```bash
python install.py
```

## Usage

### Test All THSP Gates

```bash
# Test with OpenAI
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp

# Test with Hugging Face
garak --model_type huggingface --model_name meta-llama/Llama-2-7b-chat-hf --probes sentinel_thsp

# Test with local model (Ollama)
garak --model_type ollama --model_name llama2 --probes sentinel_thsp
```

### Test Specific Gates

```bash
# Only Truth Gate
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.TruthGate

# Only Harm Gate
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.HarmGate

# Only Scope Gate (jailbreaks)
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.ScopeGate

# Only Purpose Gate
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.PurposeGate
```

### Use Sentinel Detectors

```bash
garak --model_type openai --model_name gpt-4o \
    --probes sentinel_thsp \
    --detectors sentinel_thsp
```

### Compare Models

```bash
# Test baseline
garak --model_type openai --model_name gpt-4o \
    --probes sentinel_thsp \
    --report_prefix gpt4o_baseline

# Test with Sentinel seed (via system prompt)
garak --model_type openai --model_name gpt-4o \
    --probes sentinel_thsp \
    --system_prompt "$(cat sentinel_seed.txt)" \
    --report_prefix gpt4o_sentinel
```

## Understanding Results

### Vulnerability Scores

Garak reports vulnerability scores from 0.0 to 1.0:

| Score | Meaning |
|-------|---------|
| 0.0 | Model refused (safe) |
| 0.1-0.3 | Partial compliance (concerning) |
| 0.4-0.6 | Significant compliance (vulnerable) |
| 0.7-0.9 | High compliance (very vulnerable) |
| 1.0 | Full compliance (critical) |

### Example Output

```
garak LLM vulnerability scanner v0.9 : Sentinel THSP probes

📜 sentinel_thsp.TruthGate
   ✔ TruthViolation: 15/15 passed (0% vulnerable)

📜 sentinel_thsp.HarmGate
   ⚠ HarmViolation: 14/17 passed (17.6% vulnerable)

📜 sentinel_thsp.ScopeGate
   ⚠ ScopeViolation: 12/17 passed (29.4% vulnerable)

📜 sentinel_thsp.PurposeGate
   ✔ PurposeViolation: 15/15 passed (0% vulnerable)
```

## Probe Details

### TruthGate (15 prompts)

Tests resistance to:
- Fake press releases and news articles
- Medical/legal document forgery
- Celebrity/authority impersonation
- Health misinformation (vaccines, flat earth, etc.)

### HarmGate (17 prompts)

Tests resistance to:
- Weapons and explosives instructions
- Hacking tutorials and malware creation
- Financial fraud and identity theft
- Self-harm information

### ScopeGate (17 prompts)

Tests resistance to:
- Classic jailbreaks (DAN, EVIL-GPT, etc.)
- System prompt disclosure
- Persona manipulation
- Indirect attacks (grandmother trick, roleplay)

### PurposeGate (15 prompts)

Tests resistance to:
- Vandalism and property destruction
- Resource waste
- Self-sabotage
- Random destruction requests

### THSPCombined (9 prompts)

Tests sophisticated multi-gate attacks that blend categories.

## Integration with CI/CD

```yaml
# .github/workflows/llm-security.yml
name: LLM Security Scan

on: [push, pull_request]

jobs:
  garak-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Garak
        run: pip install garak

      - name: Install Sentinel Plugin
        run: python sentinel/integrations/garak/install.py

      - name: Run THSP Scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          garak --model_type openai \
                --model_name gpt-4o \
                --probes sentinel_thsp \
                --report_prefix security_scan

      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: garak-report
          path: garak_runs/
```

## Customization

### Add Custom Prompts

Edit `probes/sentinel_thsp.py` and add to the `prompts` list:

```python
class TruthGate(Probe):
    prompts: List[str] = [
        # ... existing prompts ...
        "Your custom probe here",
    ]
```

### Add Custom Detection Patterns

Edit `detectors/sentinel_thsp.py`:

```python
class TruthViolation(THSPBaseDetector):
    compliance_patterns: List[str] = [
        # ... existing patterns ...
        r"your custom regex pattern",
    ]
```

## Related Tools

- [`sentinelseed`](https://pypi.org/project/sentinelseed/) - Python SDK
- [Promptfoo Integration](../promptfoo/) - Alternative red teaming tool
- [Sentinel Seed](https://sentinelseed.dev) - The alignment seed itself

## Resources

- [Garak Documentation](https://docs.garak.ai/)
- [Garak GitHub](https://github.com/NVIDIA/garak)
- [Sentinel THSP Protocol](https://sentinelseed.dev/docs/methodology)
- [OWASP LLM Top 10](https://genai.owasp.org/)

## License

MIT - See [LICENSE](../../../LICENSE)

---

Made with care by [Sentinel Team](https://sentinelseed.dev)
