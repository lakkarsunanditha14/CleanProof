"""Keep the permanent link (a free static Hugging Face Space) forwarding to the cloud app.

https://25215a6610-cleanproof.static.hf.space was shared earlier (forms, README), so it stays
valid and simply forwards visitors to the live dashboard on Vercel.

Requires a one-time login: backend\\venv\\Scripts\\hf.exe auth login
Run: backend\\venv\\Scripts\\python.exe scripts\\permanent_link.py [https://<app address>]
"""
import re
import sys

from huggingface_hub import HfApi

SPACE_NAME = "cleanproof"
APP_URL = "https://cleanproof-seven.vercel.app"

README = """---
title: CleanProof
emoji: 🧹
colorFrom: green
colorTo: gray
sdk: static
pinned: false
short_description: Permanent link to the CleanProof live demo
---

Forwards to the live CleanProof dashboard.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CleanProof</title>
<meta http-equiv="refresh" content="0; url={url}/dashboard">
</head>
<body style="font-family: system-ui, sans-serif; text-align: center; padding: 48px 16px; color: #1b2430">
<p>Opening the CleanProof dashboard...</p>
<p><a href="{url}/dashboard" target="_top" style="color: #0f6e5c">Open it here</a></p>
<script>try {{ window.top.location.replace("{url}/dashboard"); }} catch (e) {{ location.replace("{url}/dashboard"); }}</script>
</body>
</html>
"""


def update_permanent_link(url: str = APP_URL) -> str:
    """Point the permanent link at `url`. Returns the permanent link."""
    api = HfApi()
    user = api.whoami()["name"]
    repo_id = f"{user}/{SPACE_NAME}"
    api.create_repo(repo_id, repo_type="space", space_sdk="static", exist_ok=True)
    api.upload_file(path_or_fileobj=README.encode(), path_in_repo="README.md",
                    repo_id=repo_id, repo_type="space", commit_message="CleanProof permanent link")
    api.upload_file(path_or_fileobj=PAGE.format(url=url).encode(), path_in_repo="index.html",
                    repo_id=repo_id, repo_type="space", commit_message=f"Forward to {url}")
    return "https://" + re.sub(r"[^a-z0-9]+", "-", f"{user}-{SPACE_NAME}".lower()).strip("-") + ".static.hf.space"


if __name__ == "__main__":
    print(update_permanent_link(sys.argv[1] if len(sys.argv) > 1 else APP_URL))
