"""Test the CLIP litter check on real photos from the TACO dataset (Trash Annotated in Context).

TACO: http://tacodataset.org, github.com/pedropro/TACO, license CC BY 4.0
(Proenca & Simoes, 2020). Photos are downloaded at 640 px into data/datasets/taco (not committed).

From each real street-like photo (pavement or dirt ground) two patches are cut:
  - a LITTER patch around a hand-marked piece of litter, with its surroundings
  - a CLEAN patch of the same size from the same photo with no marked litter
The check should say "problem" for litter patches and "clean" for clean patches.

The app never judges one photo alone: it compares the worker's after photo with the citizen's
before photo of the same place. The same-place test mimics that with patches from one photo:
  - litter patch -> clean patch  = cleaned, should PASS
  - litter patch -> litter patch = same dirty photo re-uploaded, should be FLAGGED

    backend\\venv\\Scripts\\python.exe scripts\\eval_taco.py [number_of_photos]
"""
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import CLIP_THRESHOLD  # noqa: E402
from app.services import clip_service  # noqa: E402

DATA = ROOT / "data" / "datasets" / "taco"
IMAGES = DATA / "images"
STREET_LIKE = {2, 3}      # Pavement; Sand, dirt, pebbles
EXCLUDED = {1, 6}         # Indoor; Water


def pick_photos(ann, count):
    scenes = {}
    for s in ann["scene_annotations"]:
        scenes.setdefault(s["image_id"], set()).update(s["background_ids"])
    boxes = {}
    for a in ann["annotations"]:
        boxes.setdefault(a["image_id"], []).append(a["bbox"])
    chosen = [img for img in sorted(ann["images"], key=lambda i: i["id"])
              if scenes.get(img["id"], set()) & STREET_LIKE and not scenes.get(img["id"], set()) & EXCLUDED
              and img["id"] in boxes and img.get("flickr_640_url")]
    return [(img, boxes[img["id"]]) for img in chosen[:count]]


def download(img):
    path = IMAGES / f"{img['id']}.jpg"
    if not path.exists():
        urllib.request.urlretrieve(img["flickr_640_url"], path)
    return path


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def patches(photo, img, boxes):
    """(litter patch, clean patch or None). Boxes are scaled from the original size to 640 px."""
    s = photo.width / img["width"]
    rects = [(x * s, y * s, (x + w) * s, (y + h) * s) for x, y, w, h in boxes]
    size = int(min(photo.width, photo.height) * 0.45)

    x0, y0, x1, y1 = max(rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    size = max(size, int(max(x1 - x0, y1 - y0) * 1.5))
    size = min(size, photo.width, photo.height)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left = int(min(max(cx - size / 2, 0), photo.width - size))
    top = int(min(max(cy - size / 2, 0), photo.height - size))
    litter = photo.crop((left, top, left + size, top + size))

    step = max(size // 4, 1)
    for top in range(0, photo.height - size + 1, step):
        for left in range(0, photo.width - size + 1, step):
            box = (left, top, left + size, top + size)
            if not any(overlaps(box, r) for r in rects):
                return litter, photo.crop(box)
    return litter, None


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    IMAGES.mkdir(parents=True, exist_ok=True)
    ann = json.load(open(DATA / "annotations.json", encoding="utf-8"))
    photos = pick_photos(ann, count)
    print(f"Using {len(photos)} real street-like TACO photos")

    labels = {
        "garbage dump": clip_service._get_labels_for_category("garbage dump"),
        "unswept street": clip_service._get_labels_for_category("unswept street"),
    }
    results = {name: {"litter": [0, 0], "clean": [0, 0], "litter_blur": [0, 0],
                      "pair_cleaned": [0, 0], "pair_reupload": [0, 0]} for name in labels}
    failed_downloads = 0

    for n, (img, boxes) in enumerate(photos, 1):
        try:
            photo = Image.open(download(img)).convert("RGB")
        except Exception:
            failed_downloads += 1
            continue
        litter, clean = patches(photo, img, boxes)
        for name, (problem, cleanl) in labels.items():
            r = results[name]
            r["litter"][0] += clip_service.image_problem_probability(litter, problem, cleanl) >= CLIP_THRESHOLD
            r["litter"][1] += 1
            blurred = litter.filter(ImageFilter.GaussianBlur(1.5))
            r["litter_blur"][0] += clip_service.image_problem_probability(blurred, problem, cleanl) >= CLIP_THRESHOLD
            r["litter_blur"][1] += 1
            if clean is not None:
                r["clean"][0] += clip_service.image_problem_probability(clean, problem, cleanl) < CLIP_THRESHOLD
                r["clean"][1] += 1
                # Same-place decision, exactly as the app makes it
                r["pair_cleaned"][0] += not clip_service.compare_images_with_clip(litter, clean, name)["issue_present"]
                r["pair_cleaned"][1] += 1
                r["pair_reupload"][0] += clip_service.compare_images_with_clip(litter, litter, name)["issue_present"]
                r["pair_reupload"][1] += 1
        if n % 25 == 0:
            print(f"  {n}/{len(photos)} photos done")

    if failed_downloads:
        print(f"({failed_downloads} photos could not be downloaded and were skipped)")
    for name, r in results.items():
        found, total = r["litter"]
        ok_clean, total_clean = r["clean"]
        blur_found, blur_total = r["litter_blur"]
        overall = (found + ok_clean) / max(total + total_clean, 1)
        print(f"\nLabels for '{name}':")
        print(f"  litter found in litter patches:          {found}/{total} ({100 * found / max(total, 1):.0f}%)")
        print(f"  litter found in slightly blurry patches:  {blur_found}/{blur_total} ({100 * blur_found / max(blur_total, 1):.0f}%)")
        print(f"  clean patches correctly called clean:     {ok_clean}/{total_clean} ({100 * ok_clean / max(total_clean, 1):.0f}%)")
        print(f"  single photo alone, overall:              {100 * overall:.0f}%")
        pc, pn = r["pair_cleaned"]
        rc, rn = r["pair_reupload"]
        print(f"  SAME-PLACE (how the app decides):")
        print(f"    litter -> clean passed as cleaned:      {pc}/{pn} ({100 * pc / max(pn, 1):.0f}%)")
        print(f"    dirty photo re-uploaded, flagged:       {rc}/{rn} ({100 * rc / max(rn, 1):.0f}%)")
        print(f"    overall:                                {100 * (pc + rc) / max(pn + rn, 1):.0f}%")
    print("\nDataset: TACO (tacodataset.org), CC BY 4.0.")


if __name__ == "__main__":
    main()
