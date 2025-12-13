#!/usr/bin/env python3
"""
Sentinel THSP Plugin Installer for Garak

This script installs the Sentinel THSP probes and detectors
into your local Garak installation.

Usage:
    python -m sentinelseed.integrations.garak.install
    python -m sentinelseed.integrations.garak.install --uninstall
    python -m sentinelseed.integrations.garak.install --check

Requirements:
    pip install garak
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional


def find_garak_path() -> Optional[Path]:
    """Find the garak installation path."""
    try:
        import garak
        return Path(garak.__path__[0])
    except ImportError:
        return None


def get_source_files() -> tuple[Path, Path]:
    """Get paths to source probe and detector files."""
    package_dir = Path(__file__).parent

    probes_src = package_dir / "probes.py"
    detectors_src = package_dir / "detectors.py"

    return probes_src, detectors_src


def check_installation() -> bool:
    """Check if the plugin is installed correctly."""
    garak_path = find_garak_path()

    if garak_path is None:
        print("Garak is not installed.")
        return False

    probes_dst = garak_path / "probes" / "sentinel_thsp.py"
    detectors_dst = garak_path / "detectors" / "sentinel_thsp.py"

    probes_ok = probes_dst.exists()
    detectors_ok = detectors_dst.exists()

    print(f"Garak installation: {garak_path}")
    print(f"Probes installed: {'Yes' if probes_ok else 'No'} ({probes_dst})")
    print(f"Detectors installed: {'Yes' if detectors_ok else 'No'} ({detectors_dst})")

    if probes_ok and detectors_ok:
        print("\nPlugin is correctly installed!")
        return True
    else:
        print("\nPlugin is NOT fully installed. Run 'python -m sentinelseed.integrations.garak.install' to install.")
        return False


def install_plugin():
    """Install Sentinel THSP plugin to garak."""
    print("=" * 70)
    print("Sentinel THSP Plugin Installer for Garak")
    print("=" * 70)
    print()

    # Find garak
    garak_path = find_garak_path()

    if garak_path is None:
        print("ERROR: Garak is not installed.")
        print()
        print("Install garak first:")
        print("  pip install garak")
        print()
        print("Or install from GitHub for the latest version:")
        print("  pip install git+https://github.com/NVIDIA/garak.git@main")
        print()
        sys.exit(1)

    print(f"Found garak at: {garak_path}")
    print()

    # Get source files
    probes_src, detectors_src = get_source_files()

    # Check source files exist
    if not probes_src.exists():
        print(f"ERROR: Probe file not found: {probes_src}")
        sys.exit(1)

    if not detectors_src.exists():
        print(f"ERROR: Detector file not found: {detectors_src}")
        sys.exit(1)

    # Destination paths (garak expects modules named sentinel_thsp)
    probes_dst = garak_path / "probes" / "sentinel_thsp.py"
    detectors_dst = garak_path / "detectors" / "sentinel_thsp.py"

    # Install probes
    print("Installing probes...")
    print(f"  Source: {probes_src}")
    print(f"  Destination: {probes_dst}")
    try:
        shutil.copy2(probes_src, probes_dst)
        print("  OK")
    except PermissionError:
        print("  ERROR: Permission denied.")
        print("  Try running with elevated privileges (sudo on Linux/Mac, Admin on Windows).")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    print()

    # Install detectors
    print("Installing detectors...")
    print(f"  Source: {detectors_src}")
    print(f"  Destination: {detectors_dst}")
    try:
        shutil.copy2(detectors_src, detectors_dst)
        print("  OK")
    except PermissionError:
        print("  ERROR: Permission denied.")
        print("  Try running with elevated privileges (sudo on Linux/Mac, Admin on Windows).")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    print()
    print("=" * 70)
    print("Installation complete!")
    print("=" * 70)
    print()
    print("Usage Examples:")
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
    print("  # List installed Sentinel probes")
    print("  garak --list_probes | grep sentinel")
    print()
    print("Documentation: https://sentinelseed.dev/docs/garak")
    print()


def uninstall_plugin():
    """Remove Sentinel THSP plugin from garak."""
    print("Uninstalling Sentinel THSP plugin...")
    print()

    garak_path = find_garak_path()

    if garak_path is None:
        print("Garak is not installed. Nothing to uninstall.")
        return

    probes_dst = garak_path / "probes" / "sentinel_thsp.py"
    detectors_dst = garak_path / "detectors" / "sentinel_thsp.py"

    removed = False

    if probes_dst.exists():
        try:
            probes_dst.unlink()
            print(f"Removed: {probes_dst}")
            removed = True
        except PermissionError:
            print(f"ERROR: Permission denied for {probes_dst}")
        except Exception as e:
            print(f"ERROR removing {probes_dst}: {e}")

    if detectors_dst.exists():
        try:
            detectors_dst.unlink()
            print(f"Removed: {detectors_dst}")
            removed = True
        except PermissionError:
            print(f"ERROR: Permission denied for {detectors_dst}")
        except Exception as e:
            print(f"ERROR removing {detectors_dst}: {e}")

    if removed:
        print("\nUninstall complete.")
    else:
        print("\nNo Sentinel plugin files found to remove.")


def print_usage():
    """Print usage information."""
    print("Sentinel THSP Plugin for Garak")
    print()
    print("Usage:")
    print("  python -m sentinelseed.integrations.garak.install          Install the plugin")
    print("  python -m sentinelseed.integrations.garak.install --check  Check installation status")
    print("  python -m sentinelseed.integrations.garak.install --uninstall  Remove the plugin")
    print("  python -m sentinelseed.integrations.garak.install --help   Show this message")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg in ("--uninstall", "-u", "uninstall"):
            uninstall_plugin()
        elif arg in ("--check", "-c", "check"):
            check_installation()
        elif arg in ("--help", "-h", "help"):
            print_usage()
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print()
            print_usage()
            sys.exit(1)
    else:
        install_plugin()


if __name__ == "__main__":
    main()
