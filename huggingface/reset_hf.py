"""
Reset and clean the alignment-seeds dataset on HuggingFace.

This script removes old files that cause the FileFormatMismatchBetweenSplitsError
and re-uploads everything with a clean structure.

Usage:
    HF_TOKEN=hf_... python reset_hf.py

WARNING: This will delete existing files in the repository.
"""

import os
from pathlib import Path
from huggingface_hub import HfApi, login, list_repo_files, delete_file

# Configuration
REPO_ID = "sentinelseed/alignment-seeds"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Files to delete (old structure causing conflicts)
FILES_TO_DELETE = [
    # Old root-level seed files (now in seeds/ folder)
    "minimal.txt",
    "standard.txt",
    "full.txt",
    # Old dataset config files that may cause issues
    "dataset_info.json",
    "data/train.json",
    "data/validation.json",
    "data/test.json",
]


def main():
    if not HF_TOKEN:
        print("Error: HF_TOKEN environment variable not set")
        return 1

    print("=" * 60)
    print("Sentinel HuggingFace Dataset Reset")
    print("=" * 60)
    print(f"\nTarget: {REPO_ID}")
    print("\nThis will clean up old files causing configuration errors.")

    # Login
    print("\nLogging in to HuggingFace...")
    login(token=HF_TOKEN)
    api = HfApi()

    # List current files
    print("\nFetching current repository files...")
    try:
        files = list_repo_files(repo_id=REPO_ID, repo_type="dataset")
        print(f"Found {len(files)} files in repository")
    except Exception as e:
        print(f"Error listing files: {e}")
        return 1

    # Find files to delete
    to_delete = []
    for f in files:
        # Delete old root-level txt files
        if f in FILES_TO_DELETE:
            to_delete.append(f)
        # Delete any data/ folder contents (old split structure)
        elif f.startswith("data/"):
            to_delete.append(f)
        # Delete any .json config files at root
        elif f.endswith(".json") and "/" not in f:
            to_delete.append(f)

    if not to_delete:
        print("\nNo files to delete. Repository is clean.")
        print("Run sync_hf.py to upload the latest files.")
        return 0

    print(f"\nFiles to delete ({len(to_delete)}):")
    for f in to_delete:
        print(f"  - {f}")

    # Confirm deletion
    confirm = input("\nProceed with deletion? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return 0

    # Delete files
    print("\nDeleting files...")
    deleted = 0
    for filepath in to_delete:
        try:
            delete_file(
                path_in_repo=filepath,
                repo_id=REPO_ID,
                repo_type="dataset",
                commit_message=f"Clean up: remove {filepath}"
            )
            print(f"  Deleted: {filepath}")
            deleted += 1
        except Exception as e:
            print(f"  Error deleting {filepath}: {e}")

    print(f"\nDeleted {deleted}/{len(to_delete)} files")
    print("\nNow run: python sync_hf.py")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
