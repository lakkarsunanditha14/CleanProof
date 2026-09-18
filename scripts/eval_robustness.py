"""Stress-test the CLIP check on hard photos: blurry, dark, low resolution, and partly cleaned
(only a small patch of garbage left). Uses the 6 demo before/after pairs.

    backend\\venv\\Scripts\\python.exe scripts\\eval_robustness.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services import clip_service  # noqa: E402
from app.services.image_quality import quality_problem  # noqa: E402

CATEGORIES = {1: "garbage dump", 2: "construction debris", 3: "unswept street",
              4: "unswept street", 5: "garbage dump", 6: "garbage dump"}


def load(kind, i):
    return Image.open(next((ROOT / "data" / "demo" / kind).glob(f"{kind}_{i}.*"))).convert("RGB")


def blur(img, radius):
    return img.filter(ImageFilter.GaussianBlur(radius))


def dark(img):
    return ImageEnhance.Brightness(img).enhance(0.35)


def low_res(img):
    w, h = img.size
    return img.resize((160, int(160 * h / w))).resize((w, h))


def partly_cleaned(before, after):
    """After photo with the single dirtiest ninth of the scene left uncleaned."""
    w, h = after.size
    before = before.resize((w, h))
    diff = ImageChops.difference(before, after).convert("L")
    cells = [(c * w // 3, r * h // 3, (c + 1) * w // 3, (r + 1) * h // 3) for r in range(3) for c in range(3)]
    box = max(cells, key=lambda b: ImageStat.Stat(diff.crop(b)).mean[0])
    out = after.copy()
    out.paste(before.crop(box), box[:2])
    return out


def cases():
    """(name, before image, after image, category, garbage still present?)"""
    for i in range(1, 7):
        b, a, cat = load("before", i), load("after", i), CATEGORIES[i]
        yield "clean", b, a, cat, False
        yield "clean + light blur", b, blur(a, 2), cat, False
        yield "clean + heavy blur", b, blur(a, 6), cat, False
        yield "clean + dark", b, dark(a), cat, False
        yield "clean + low resolution", b, low_res(a), cat, False
        yield "dirty re-upload", b, b, cat, True
        yield "dirty + heavy blur", b, blur(b, 6), cat, True
        yield "dirty + dark", b, dark(b), cat, True
        yield "partly cleaned (1/9 left)", b, partly_cleaned(b, a), cat, True
        yield "partly cleaned + blur", b, blur(partly_cleaned(b, a), 3), cat, True


def run(quality_gate=True):
    """A photo the app asks to retake (too blurry/dark) counts as handled correctly."""
    totals, by_case = [0, 0], {}
    for name, b, a, cat, expected in cases():
        if quality_gate and quality_problem(a):
            ok = True
        else:
            ok = clip_service.compare_images_with_clip(b, a, cat)["issue_present"] == expected
        totals[0] += ok
        totals[1] += 1
        by_case.setdefault(name, [0, 0])
        by_case[name][0] += ok
        by_case[name][1] += 1
    print(f"{'case':30} correct")
    for name, (ok, n) in by_case.items():
        print(f"{name:30} {ok}/{n}")
    print(f"{'TOTAL':30} {totals[0]}/{totals[1]}  ({100 * totals[0] / totals[1]:.0f}%)")


if __name__ == "__main__":
    for multi, gate, title in ((False, False, "before: full photo only, no quality check"),
                               (True, True, "now: full photo + 4 zoomed parts + retake if too blurry/dark")):
        clip_service.MULTI_CROP = multi
        print(f"\n=== {title} ===")
        run(quality_gate=gate)
