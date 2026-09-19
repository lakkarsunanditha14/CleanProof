"""Keep one permanent link that always forwards to the current public tunnel link.

A free *static* Hugging Face Space (https://<username>-cleanproof.static.hf.space) holds a small page
that forwards visitors to the Cloudflare tunnel started by public_link.py. Only this forwarding
page is published, no app code. It works while this laptop is running the app.

Requires a one-time login: backend\\venv\\Scripts\\hf.exe auth login
"""
import re
from pathlib import Path

from huggingface_hub import HfApi

SPACE_NAME = "cleanproof"
SNAPSHOT = Path(__file__).resolve().parents[1] / "docs" / "screenshots" / "dashboard.png"  # shown when offline

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
<style>
  body {{ font-family: system-ui, sans-serif; background: #f8fafc; color: #1b2430; margin: 0;
         min-height: 100vh; display: flex; align-items: center; justify-content: center; text-align: center; }}
  .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px 24px; max-width: 420px; margin: 16px; }}
  h1 {{ color: #0f6e5c; margin: 0 0 8px; }}
  a.button {{ display: inline-block; margin-top: 16px; background: #0f6e5c; color: #fff; padding: 12px 20px;
             border-radius: 12px; text-decoration: none; font-weight: 600; }}
  p.note {{ color: #64748b; font-size: 14px; }}
  #offline {{ display: none; max-width: 1100px; margin: 16px; }}
  #offline img {{ width: 100%; border: 1px solid #e2e8f0; border-radius: 12px; }}
</style>
</head>
<body>
<div class="card" id="loading">
  <h1>CleanProof</h1>
  <p>Opening the live dashboard...</p>
</div>
<div id="offline">
  <h1>CleanProof dashboard</h1>
  <p class="note">The live demo is offline right now, so this is a saved snapshot of the dashboard.
     <a href="">Try again</a></p>
  <img src="dashboard.png" alt="CleanProof accountability dashboard">
</div>
<script>
  // Open the live dashboard only if the demo laptop answers; otherwise show the snapshot
  const live = "{url}";
  const go = () => {{ try {{ window.top.location.replace(live + "/dashboard"); }} catch (e) {{ location.replace(live + "/dashboard"); }} }};
  const offline = () => {{ document.getElementById("loading").style.display = "none";
                           document.getElementById("offline").style.display = "block"; }};
  fetch(live + "/api/dashboard/stats", {{ cache: "no-store", signal: AbortSignal.timeout(10000) }})
    .then(r => r.ok ? go() : offline()).catch(offline);
</script>
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
    api.upload_file(path_or_fileobj=str(SNAPSHOT), path_in_repo="dashboard.png",
                    repo_id=repo_id, repo_type="space", commit_message="Dashboard snapshot")
    api.upload_file(path_or_fileobj=PAGE.format(url=url).encode(), path_in_repo="index.html",
                    repo_id=repo_id, repo_type="space", commit_message=f"Forward to {url}")
    return "https://" + re.sub(r"[^a-z0-9]+", "-", f"{user}-{SPACE_NAME}".lower()).strip("-") + ".static.hf.space"


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        sys.exit("usage: permanent_link.py https://<current-tunnel-link>")
    print(update_permanent_link(sys.argv[1]))
