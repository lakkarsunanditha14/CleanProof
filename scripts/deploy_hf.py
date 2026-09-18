"""Upload CleanProof to a Hugging Face Space (Docker) for a permanent public link.

One-time setup: log in with your own access token (typed into the terminal, never shared):
    backend\\venv\\Scripts\\hf.exe auth login
Then run:
    backend\\venv\\Scripts\\python.exe scripts\\deploy_hf.py
Run it again after changes to update the Space. Local files and settings are not changed.
"""
import re
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
SPACE_NAME = "cleanproof"

# Local-only or generated files that must not be uploaded
IGNORE = [
    ".git/*", ".claude/*", "**/__pycache__/*", "**/.env",
    "backend/venv/*", "frontend/node_modules/*", "frontend/dist/*", "frontend/certs/*",
    "tools/*", "*.db", "data/images/*", "data/demo/upload/*.jpg",
    "*.pdf", "CleanProof_phone_QR.png",
]


def main() -> None:
    api = HfApi()
    user = api.whoami()["name"]
    repo_id = f"{user}/{SPACE_NAME}"

    api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    print(f"Uploading to Space {repo_id} ...")
    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=IGNORE,
        commit_message="Deploy CleanProof",
    )

    subdomain = re.sub(r"[^a-z0-9]+", "-", f"{user}-{SPACE_NAME}".lower()).strip("-")
    print("\nUploaded. The Space now builds (about 5-10 minutes the first time).")
    print(f"  Build progress: https://huggingface.co/spaces/{repo_id}")
    print(f"  App link:       https://{subdomain}.hf.space   <- share this one (camera works here)")


if __name__ == "__main__":
    main()
