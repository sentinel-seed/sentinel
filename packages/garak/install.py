#!/usr/bin/env python3
"""
Sentinel THSP Plugin Installer for Garak

This script installs the Sentinel THSP probes and detectors
into your local Garak installation.

Usage:
    python install.py

Requirements:
    pip install garak
"""

import os
import sys
import shutil
from pathlib import Path


def find_garak_path() -> Path:
    """Find the garak installation path."""
    try:
        import garak
        return Path(garak.__path__[0])
    except ImportError:
        return None


def install_plugin():
    """Install Sentinel THSP plugin to garak."""
    print("=" * 60)
    print("Sentinel THSP Plugin Installer for Garak")
    print("=" * 60)
    print()

    # Find garak
    garak_path = find_garak_path()

    if garak_path is None:
        print("ERROR: Garak is not installed.")
        print()
        print("Install garak first:")
        print("  pip install garak")
        print()
        sys.exit(1)

    print(f"Found garak at: {garak_path}")
    print()

    # Get source paths
    script_dir = Path(__file__).parent
    probes_src = script_dir / "probes" / "sentinel_thsp.py"
    detectors_src = script_dir / "detectors" / "sentinel_thsp.py"

    # Get destination paths
    probes_dst = garak_path / "probes" / "sentinel_thsp.py"
    detectors_dst = garak_path / "detectors" / "sentinel_thsp.py"

    # Check source files exist
    if not probes_src.exists():
        print(f"ERROR: Probe file not found: {probes_src}")
        sys.exit(1)

    if not detectors_src.exists():
        print(f"ERROR: Detector file not found: {detectors_src}")
        sys.exit(1)

    # Install probes
    print(f"Installing probes...")
    print(f"  {probes_src}")
    print(f"  -> {probes_dst}")
    try:
        shutil.copy2(probes_src, probes_dst)
        print("  OK")
    except PermissionError:
        print("  ERROR: Permission denied. Try running with sudo/admin.")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    print()

    # Install detectors
    print(f"Installing detectors...")
    print(f"  {detectors_src}")
    print(f"  -> {detectors_dst}")
    try:
        shutil.copy2(detectors_src, detectors_dst)
        print("  OK")
    except PermissionError:
        print("  ERROR: Permission denied. Try running with sudo/admin.")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Installation complete!")
    print("=" * 60)
    print()
    print("Usage:")
    print()
    print("  # Test all THSP gates")
    print("  garak --model_type openai --model_name gpt-4o --probes sentinel_thsp")
    print()
    print("  # Test specific gate")
    print("  garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.TruthGate")
    print()
    print("  # Use with Sentinel detectors")
    print("  garak --model_type openai --model_name gpt-4o \\")
    print("      --probes sentinel_thsp \\")
    print("      --detectors sentinel_thsp")
    print()
    print("Documentation: https://sentinelseed.dev/docs/garak")
    print()


def uninstall_plugin():
    """Remove Sentinel THSP plugin from garak."""
    print("Uninstalling Sentinel THSP plugin...")

    garak_path = find_garak_path()

    if garak_path is None:
        print("Garak not installed, nothing to uninstall.")
        return

    probes_dst = garak_path / "probes" / "sentinel_thsp.py"
    detectors_dst = garak_path / "detectors" / "sentinel_thsp.py"

    if probes_dst.exists():
        probes_dst.unlink()
        print(f"Removed: {probes_dst}")

    if detectors_dst.exists():
        detectors_dst.unlink()
        print(f"Removed: {detectors_dst}")

    print("Uninstall complete.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall_plugin()
    else:
        install_plugin()
