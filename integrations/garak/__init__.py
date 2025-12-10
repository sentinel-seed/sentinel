"""
Sentinel THSP Plugin for Garak (NVIDIA)

This package provides probes and detectors for testing LLM resistance
to attacks on the THSP (Truth, Harm, Scope, Purpose) protocol.

Installation:
    1. Install garak: pip install garak
    2. Copy probes/sentinel_thsp.py to garak/probes/
    3. Copy detectors/sentinel_thsp.py to garak/detectors/

Usage:
    # Test all THSP gates
    garak --model_type openai --model_name gpt-4o --probes sentinel_thsp

    # Test specific gate
    garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.TruthGate

    # Test with Sentinel detectors
    garak --model_type openai --model_name gpt-4o \\
        --probes sentinel_thsp \\
        --detectors sentinel_thsp

Documentation: https://sentinelseed.dev/docs/garak
"""

__version__ = "0.1.0"
__author__ = "Sentinel Team"
