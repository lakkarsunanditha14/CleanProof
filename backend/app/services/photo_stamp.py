"""Burns a visible evidence stamp into live-captured closure photos, like a GPS camera app.

The stamp is added by the server after verification (the AI checks the clean photo, since a
text bar can confuse it), and it uses the server's own clock, so the time cannot be faked.
"""
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

_FONTS = ["C:/Windows/Fonts/segoeuib.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font(size: int):
    for path in _FONTS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def stamp_photo(src: Path, dst: Path, lines: List[str]) -> None:
    """Write a copy of `src` to `dst` with a translucent bar of `lines` across the top."""
    with Image.open(src) as original:
        img = original.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    size = max(14, img.width // 42)
    font = _font(size)
    pad = int(size * 0.7)
    line_h = int(size * 1.3)
    draw.rectangle((0, 0, img.width, pad * 2 + line_h * len(lines)), fill=(0, 0, 0, 150))
    for n, text in enumerate(lines):
        draw.text((pad, pad + n * line_h), text, fill=(255, 255, 255), font=font)
    img.save(dst, "JPEG", quality=92)
