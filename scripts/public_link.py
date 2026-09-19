"""Start a Cloudflare quick tunnel to the local app and show a QR code for phones.

The tunnel link changes on every start, so the permanent link (a free static Hugging Face Space,
see permanent_link.py) is updated to forward to it. People always use the permanent link.
Works on any network (Wi-Fi or mobile data) while this window stays open. If the tunnel dies
(sleep, Wi-Fi change) a new one is started and the permanent link is updated automatically.
"""
import ctypes
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUDFLARED = ROOT / "tools" / "cloudflared.exe"
QR_FILE = ROOT / "CleanProof_phone_QR.png"
EDGE = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"
SNAPSHOT_EVERY = 30 * 60  # seconds between fresh offline snapshots of the dashboard


def save_qr(url: str) -> None:
    import qrcode
    from PIL import Image, ImageDraw, ImageFont

    qr = qrcode.QRCode(border=2, box_size=12)
    qr.add_data(url)
    qr.make(fit=True)
    code = qr.make_image(fill_color="#0F6E5C", back_color="white").convert("RGB")
    w, h = code.size
    width = max(w, 620)
    card = Image.new("RGB", (width, h + 110), "white")
    card.paste(code, ((width - w) // 2, 0))
    draw = ImageDraw.Draw(card)
    fonts = "C:/Windows/Fonts/"
    title = ImageFont.truetype(fonts + "segoeuib.ttf", 30)
    small = ImageFont.truetype(fonts + "segoeui.ttf", 20)
    for text, font, y in (("CleanProof: scan to open", title, h + 10), (url, small, h + 58)):
        draw.text(((width - draw.textlength(text, font=font)) / 2, y), text, fill="#1B2430", font=font)
    card.save(QR_FILE)


def tunnel_alive(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/api/dashboard/stats", timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def refresh_snapshot() -> None:
    """Upload a fresh picture of the live dashboard, shown by the permanent link when offline."""
    shot = Path(tempfile.gettempdir()) / "cleanproof_dashboard.png"
    try:
        shot.unlink(missing_ok=True)
        subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--ignore-certificate-errors",
                        "--user-data-dir=" + str(Path(tempfile.gettempdir()) / "cleanproof_edge"),
                        "--window-size=1440,1500", "--hide-scrollbars", "--virtual-time-budget=30000",
                        "--screenshot=" + str(shot), "https://localhost:5173/dashboard"],
                       capture_output=True, timeout=120)
        for _ in range(60):  # msedge.exe returns early; the picture is written a few seconds later
            if shot.exists():
                break
            time.sleep(1)
        time.sleep(2)  # let the file finish writing
        from permanent_link import upload_snapshot
        upload_snapshot(shot)
        print(time.strftime("%H:%M") + "  Offline snapshot of the dashboard updated.")
    except Exception as err:  # Edge missing, not logged in to Hugging Face, or offline
        print(f"(Dashboard snapshot not updated: {err})")


def run_tunnel(first: bool) -> None:
    """Start one tunnel, publish its link, and return once it has died."""
    proc = subprocess.Popen(
        [str(CLOUDFLARED), "tunnel", "--no-autoupdate", "--url", "https://localhost:5173", "--no-tls-verify"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print("Starting the public link (takes a few seconds)...")
    try:
        url = None
        for line in proc.stdout:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                url = match.group(0)
                break
        if url is None:
            return
        # Keep reading cloudflared's output so it never blocks on a full pipe
        threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
        share = url
        try:
            from permanent_link import update_permanent_link
            share = update_permanent_link(url)
        except Exception as err:  # not logged in to Hugging Face, or offline
            print(f"(Permanent link not updated: {err}. Sharing the tunnel link instead.)")
        save_qr(share)
        print("\n" + "=" * 70)
        print(f"  SHARE THIS LINK:  {share}")
        print(f"  (tunnel: {url})")
        print(f"  QR code:          {QR_FILE}")
        print("  Works on any phone, any network. Keep this window open.")
        print("=" * 70 + "\n")
        if first:
            os.startfile(QR_FILE)

        # Quick tunnels die after sleep or a network change; restart after 3 failed checks in a row
        time.sleep(30)
        failures = 0
        last_snapshot = 0.0
        while proc.poll() is None and failures < 3:
            failures = 0 if tunnel_alive(url) else failures + 1
            if failures == 0 and time.time() - last_snapshot > SNAPSHOT_EVERY:
                last_snapshot = time.time()
                refresh_snapshot()
            time.sleep(60 if failures == 0 else 20)
        print(time.strftime("%H:%M") + "  Public link stopped working, starting a new one...")
    finally:
        proc.terminate()


def main() -> None:
    if not CLOUDFLARED.exists():
        sys.exit(f"cloudflared not found at {CLOUDFLARED}")
    # Stop Windows from sleeping while the demo is shared (closing the lid can still sleep it)
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    try:
        first = True
        while True:
            run_tunnel(first)
            first = False
            time.sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
