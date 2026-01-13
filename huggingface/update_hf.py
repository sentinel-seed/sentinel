"""
Update Sentinel dataset on Hugging Face with new integrations.

Usage:
    HF_TOKEN=hf_... python update_hf.py
"""

import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, login

# Config
REPO_ID = "sentinelseed/alignment-seeds"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
INTEGRATIONS_DIR = PROJECT_ROOT / "src" / "sentinelseed" / "integrations"

# New integrations to upload (not in HuggingFace yet)
NEW_INTEGRATIONS = [
    "dspy",
    "isaac_lab",
    "letta",
    "preflight",
    "ros2",
    "pyrit",
    "openai_agents",
]


def main():
    if not HF_TOKEN:
        print("Error: HF_TOKEN environment variable not set")
        return 1

    print("Logging in to Hugging Face...")
    login(token=HF_TOKEN)

    api = HfApi()

    # Upload each new integration
    for integration in NEW_INTEGRATIONS:
        integration_dir = INTEGRATIONS_DIR / integration

        if not integration_dir.exists():
            print(f"Warning: {integration} not found at {integration_dir}")
            continue

        print(f"\nUploading {integration}...")

        # Get all Python files in the integration
        files_to_upload = list(integration_dir.glob("*.py"))

        # Also check for README.md
        readme = integration_dir / "README.md"
        if readme.exists():
            files_to_upload.append(readme)

        for filepath in files_to_upload:
            target_path = f"integrations/{integration}/{filepath.name}"

            try:
                api.upload_file(
                    path_or_fileobj=str(filepath),
                    path_in_repo=target_path,
                    repo_id=REPO_ID,
                    repo_type="dataset",
                    commit_message=f"Add {integration} integration"
                )
                print(f"  Uploaded: {target_path}")
            except Exception as e:
                print(f"  Error uploading {filepath.name}: {e}")

    print(f"\nDone! Check: https://huggingface.co/datasets/{REPO_ID}")
    return 0


if __name__ == "__main__":
    exit(main())
