"""
Upload Sentinel v2 seeds to Hugging Face
"""

from huggingface_hub import HfApi, login
import os

# Config
REPO_ID = "sentinelseed/alignment-seeds"
HF_TOKEN = os.environ.get("HF_TOKEN", "")  # Set HF_TOKEN env var before running

# Files to upload
FILES = [
    "README.md",
    "minimal.txt",
    "standard.txt",
    "full.txt"
]

def main():
    # Login
    print("Logging in to Hugging Face...")
    login(token=HF_TOKEN)

    api = HfApi()

    # Get current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Upload each file
    for filename in FILES:
        filepath = os.path.join(script_dir, filename)

        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        print(f"Uploading {filename}...")

        try:
            api.upload_file(
                path_or_fileobj=filepath,
                path_in_repo=filename,
                repo_id=REPO_ID,
                repo_type="dataset",
                commit_message=f"Update {filename} to v2 THSP protocol"
            )
            print(f"  Uploaded: {filename}")
        except Exception as e:
            print(f"  Error uploading {filename}: {e}")

    print("\nDone! Check: https://huggingface.co/datasets/sentinelseed/alignment-seeds")

if __name__ == "__main__":
    main()
