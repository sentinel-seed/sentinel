"""
Sentinel THSP Plugin for Garak (NVIDIA)

This package provides probes and detectors for testing LLM resistance
to attacks on the THSP (Truth, Harm, Scope, Purpose) protocol.

Garak is NVIDIA's LLM vulnerability scanner. This plugin extends it
with probes and detectors based on the Sentinel THSP protocol.

Installation Options:

    Option 1 - Copy to Garak directory:
        python -m sentinelseed.integrations.garak.install

    Option 2 - Manual copy:
        # Find garak installation
        python -c "import garak; print(garak.__path__[0])"

        # Copy probes
        cp probes.py /path/to/garak/probes/sentinel_thsp.py

        # Copy detectors
        cp detectors.py /path/to/garak/detectors/sentinel_thsp.py

Usage after installation:

    # Test all THSP gates
    garak --model_type openai --model_name gpt-4o --probes sentinel_thsp

    # Test specific gate
    garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.TruthGate

    # Use with Sentinel detectors
    garak --model_type openai --model_name gpt-4o \\
        --probes sentinel_thsp \\
        --detectors sentinel_thsp

Documentation: https://github.com/sentinel-seed/sentinel/tree/main/src/sentinelseed/integrations/garak
GitHub: https://github.com/NVIDIA/garak

References:
    - Garak Documentation: https://docs.garak.ai
    - THSP Protocol: https://github.com/sentinel-seed/sentinel#thsp-protocol
"""

__version__ = "2.19.0"
__author__ = "Sentinel Team"

# Minimum required Garak version
MIN_GARAK_VERSION = "0.9.0"

# Re-export probe and detector classes for convenience
from sentinelseed.integrations.garak.probes import (
    TruthGate,
    HarmGate,
    ScopeGate,
    PurposeGate,
    THSPCombined,
)

from sentinelseed.integrations.garak.detectors import (
    TruthViolation,
    HarmViolation,
    ScopeViolation,
    PurposeViolation,
    THSPCombinedDetector,
    DetectionMetrics,
    AmbiguousScoreConfig,
)

__all__ = [
    # Constants
    "__version__",
    "__author__",
    "MIN_GARAK_VERSION",
    # Probes
    "TruthGate",
    "HarmGate",
    "ScopeGate",
    "PurposeGate",
    "THSPCombined",
    # Detectors
    "TruthViolation",
    "HarmViolation",
    "ScopeViolation",
    "PurposeViolation",
    "THSPCombinedDetector",
    # Configuration Classes
    "DetectionMetrics",
    "AmbiguousScoreConfig",
]
