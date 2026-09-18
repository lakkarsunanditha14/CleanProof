"""Keep one permanent link that always forwards to the current public tunnel link.

A free *static* Hugging Face Space (https://<username>-cleanproof.static.hf.space) holds a small page
that forwards visitors to the Cloudflare tunnel started by public_link.py. Only this forwarding
page is published, no app code. It works while this laptop is running the app.

Requires a one-time login: backend\\venv\\Scripts\\hf.exe auth login
"""
import re

from huggingface_hub import HfApi

SPACE_NAME = "cleanproof"

README = """---
title: CleanProof
emoji: 🧹
colorFrom: green
colorTo: gray
sdk: static
pinned: false
short_description: Permanent link to the CleanProof live demo
---

Forwards to the live CleanProof demo running on the team's laptop.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CleanProof</title>
<meta http-equiv="refresh" content="0; url={url}">
<style>
  body {{ font-family: system-ui, sans-serif; background: #f8fafc; color: #1b2430; margin: 0;
         min-height: 100vh; display: flex; align-items: center; justify-content: center; text-align: center; }}
  .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px 24px; max-width: 420px; margin: 16px; }}
  h1 {{ color: #0f6e5c; margin: 0 0 8px; }}
  a.button {{ display: inline-block; margin-top: 16px; background: #0f6e5c; color: #fff; padding: 12px 20px;
             border-radius: 12px; text-decoration: none; font-weight: 600; }}
  p.note {{ color: #64748b; font-size: 14px; }}
</style>
</head>
<body>
<div class="card">
  <h1>CleanProof</h1>
  <p>Opening the live demo...</p>
  <a class="button" href="{url}" target="_top">Open CleanProof</a>
  <p class="note">If it does not open, the demo laptop is offline right now.</p>
</div>
<script>try {{ window.top.location.replace("{url}"); }} catch (e) {{ location.replace("{url}"); }}</script>
</body>
</html>
"""


def update_permanent_link(url: str) -> str:
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
    import sys
    if len(sys.argv) != 2:
        sys.exit("usage: permanent_link.py https://<current-tunnel-link>")
    print(update_permanent_link(sys.argv[1]))
