"""Start a Cloudflare quick tunnel to the local app and show a QR code for phones.

The tunnel link changes on every start, so the permanent link (a free static Hugging Face Space,
see permanent_link.py) is updated to forward to it. People always use the permanent link.
Works on any network (Wi-Fi or mobile data) while this window stays open.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUDFLARED = ROOT / "tools" / "cloudflared.exe"
QR_FILE = ROOT / "CleanProof_phone_QR.png"


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


def main() -> None:
    if not CLOUDFLARED.exists():
        sys.exit(f"cloudflared not found at {CLOUDFLARED}")

    proc = subprocess.Popen(
        [str(CLOUDFLARED), "tunnel", "--no-autoupdate", "--url", "https://localhost:5173", "--no-tls-verify"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print("Starting the public link (takes a few seconds)...")
    url = None
    try:
        for line in proc.stdout:
            if url is None:
                match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if match:
                    url = match.group(0)
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
                    os.startfile(QR_FILE)
            elif "ERR" in line:
                print(line.rstrip())
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
