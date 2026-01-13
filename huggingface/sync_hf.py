"""
Sync Sentinel alignment-seeds dataset to HuggingFace.

This script uploads seeds and all integrations to the HuggingFace dataset.
It replaces upload_to_hf.py and update_hf.py with a unified approach.

Usage:
    HF_TOKEN=hf_... python sync_hf.py

    Or set the token in environment:
    export HF_TOKEN=hf_...
    python sync_hf.py
"""

import os
from pathlib import Path
from huggingface_hub import HfApi, login

# Configuration
REPO_ID = "sentinelseed/alignment-seeds"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
INTEGRATIONS_DIR = PROJECT_ROOT / "src" / "sentinelseed" / "integrations"

# All integrations to sync (complete list - 25 integrations)
ALL_INTEGRATIONS = [
    "agent_validation",
    "agno",
    "anthropic_sdk",
    "autogpt",
    "autogpt_block",
    "coinbase",
    "crewai",
    "dspy",
    "garak",
    "google_adk",
    "isaac_lab",
    "langchain",
    "langgraph",
    "letta",
    "llamaindex",
    "mcp_server",
    "openai_agents",
    "openai_assistant",
    "openguardrails",
    "preflight",
    "pyrit",
    "raw_api",
    "ros2",
    "solana_agent_kit",
    "virtuals",
]

# Seed files
SEED_FILES = ["minimal.txt", "standard.txt", "full.txt"]


def main():
    if not HF_TOKEN:
        print("Error: HF_TOKEN environment variable not set")
        print("Usage: HF_TOKEN=hf_... python sync_hf.py")
        return 1

    print("=" * 60)
    print("Sentinel HuggingFace Sync")
    print("=" * 60)

    # Login
    print("\nLogging in to HuggingFace...")
    login(token=HF_TOKEN)
    api = HfApi()

    uploaded = 0
    errors = 0

    # 1. Upload README.md
    print("\n[1/3] Uploading README.md...")
    readme_path = SCRIPT_DIR / "README.md"
    if readme_path.exists():
        try:
            api.upload_file(
                path_or_fileobj=str(readme_path),
                path_in_repo="README.md",
                repo_id=REPO_ID,
                repo_type="dataset",
                commit_message="Update README"
            )
            print("  Uploaded: README.md")
            uploaded += 1
        except Exception as e:
            print(f"  Error: {e}")
            errors += 1

    # 2. Upload seed files
    print("\n[2/3] Uploading seeds...")
    for seed_file in SEED_FILES:
        seed_path = SCRIPT_DIR / seed_file
        if seed_path.exists():
            try:
                api.upload_file(
                    path_or_fileobj=str(seed_path),
                    path_in_repo=f"seeds/{seed_file}",
                    repo_id=REPO_ID,
                    repo_type="dataset",
                    commit_message=f"Update {seed_file}"
                )
                print(f"  Uploaded: seeds/{seed_file}")
                uploaded += 1
            except Exception as e:
                print(f"  Error uploading {seed_file}: {e}")
                errors += 1
        else:
            print(f"  Not found: {seed_path}")

    # 3. Upload all integrations
    print(f"\n[3/3] Uploading {len(ALL_INTEGRATIONS)} integrations...")
    for integration in ALL_INTEGRATIONS:
        integration_dir = INTEGRATIONS_DIR / integration

        if not integration_dir.exists():
            print(f"  Skip: {integration} (not found)")
            continue

        # Get all Python files
        py_files = list(integration_dir.glob("*.py"))

        # Also include README.md if exists
        readme = integration_dir / "README.md"
        if readme.exists():
            py_files.append(readme)

        for filepath in py_files:
            target_path = f"integrations/{integration}/{filepath.name}"
            try:
                api.upload_file(
                    path_or_fileobj=str(filepath),
                    path_in_repo=target_path,
                    repo_id=REPO_ID,
                    repo_type="dataset",
                    commit_message=f"Sync {integration}"
                )
                print(f"  Uploaded: {target_path}")
                uploaded += 1
            except Exception as e:
                print(f"  Error: {filepath.name} - {e}")
                errors += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Sync complete: {uploaded} files uploaded, {errors} errors")
    print(f"Dataset: https://huggingface.co/datasets/{REPO_ID}")
    print("=" * 60)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    exit(main())
