import os
import threading
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
from PIL import Image
from app.config import CLIP_THRESHOLD, CLIP_RATIO

MODEL_NAME = "openai/clip-vit-base-patch32"
# "torch" runs the original model (laptop). "onnx" runs the same model's vision encoder with
# ONNX Runtime and precomputed label embeddings, small enough for free cloud hosting.
CLIP_ENGINE = os.getenv("CLIP_ENGINE", "torch")
TEXT_CACHE = Path(__file__).with_name("clip_text_embeddings.npz")
ONNX_URL = ("https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/"
            "d15189d7028b43f1d3e65039190477f6af591c2a/onnx/vision_model.onnx")
ONNX_FILE = Path(os.getenv("CLIP_ONNX_FILE", "/tmp/clip/vision_model.onnx"))
MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

# Cached singleton model and processor instances
_model = None
_processor = None
_onnx = None
_text = None
_lock = threading.Lock()

CATEGORY_LABEL_SETS = {
    "garbage dump": {
        "problem": [
            "a pile of garbage bags and litter on the ground",
            "trash and plastic waste dumped by the road",
            "a garbage bin overflowing with waste spilling onto the street"
        ],
        "clean": [
            "a clean street with no litter",
            "an empty garbage bin standing on a clean footpath",
            "a clean roadside with no waste"
        ]
    },
    "blocked drain": {
        "problem": [
            "a drain blocked with plastic waste and garbage",
            "a dirty clogged roadside drain full of trash"
        ],
        "clean": [
            "a clean open drain with flowing water",
            "a clear roadside drain with no garbage"
        ]
    },
    "construction debris": {
        "problem": [
            "a pile of broken bricks and concrete rubble on a footpath",
            "construction debris dumped on the pavement"
        ],
        "clean": [
            "a clean empty footpath",
            "a clear paved sidewalk with no debris"
        ]
    },
    "unswept street": {
        "problem": [
            "a footpath covered with litter, wrappers and dry leaves",
            "an unswept dirty street with scattered trash"
        ],
        "clean": [
            "a freshly swept clean footpath",
            "a clean street with no litter or leaves"
        ]
    }
}

def _get_clip_model():
    """Lazy-loads and caches the CLIP model and processor in memory."""
    global _model, _processor
    if _model is None or _processor is None:
        from transformers import CLIPProcessor, CLIPModel
        print(f"Loading local CLIP model '{MODEL_NAME}'...")
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _model.eval()
        print("Local CLIP model loaded successfully.")
    return _model, _processor

def _pixels(image: Image.Image) -> np.ndarray:
    """CLIP preprocessing (same steps as CLIPProcessor): shortest side 224 bicubic, centre crop, normalise."""
    w, h = image.size
    if w <= h:
        size = (224, int(224 * h / w))
    else:
        size = (int(224 * w / h), 224)
    img = image.resize(size, Image.Resampling.BICUBIC)
    left, top = int((size[0] - 224) / 2), int((size[1] - 224) / 2)
    arr = np.asarray(img.crop((left, top, left + 224, top + 224)), dtype=np.float32) / 255.0
    return ((arr - MEAN) / STD).transpose(2, 0, 1)


def _onnx_session():
    global _onnx
    with _lock:
        if _onnx is None:
            import onnxruntime as ort
            if not ONNX_FILE.exists():
                ONNX_FILE.parent.mkdir(parents=True, exist_ok=True)
                tmp = ONNX_FILE.with_suffix(".part")
                urllib.request.urlretrieve(ONNX_URL, tmp)
                tmp.replace(ONNX_FILE)
            _onnx = ort.InferenceSession(str(ONNX_FILE), providers=["CPUExecutionProvider"])
    return _onnx


def _label_probs(images: List[Image.Image], labels: List[str]) -> np.ndarray:
    """Softmax over `labels` for each image: one row per image (same maths as CLIP's logits_per_image)."""
    global _text
    if CLIP_ENGINE == "onnx":
        if _text is None:
            data = np.load(TEXT_CACHE)
            _text = (dict(zip(data["labels"].tolist(), data["embeds"])), float(data["scale"]))
        cache, scale = _text
        emb = _onnx_session().run(None, {"pixel_values": np.stack([_pixels(i) for i in images])})[0]
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        logits = scale * emb @ np.stack([cache[label] for label in labels]).T
    else:
        import torch
        model, processor = _get_clip_model()
        inputs = processor(text=labels, images=images, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits_per_image.numpy()
    logits = logits - logits.max(axis=1, keepdims=True)
    e = np.exp(logits)
    return e / e.sum(axis=1, keepdims=True)


# Added to every category, so scenes that are not a street (a table, a floor, a courtyard)
# are still judged on litter vs clean instead of on "street or not".
GENERAL_PROBLEM = ["wrappers, packets and litter lying on a surface", "rubbish and waste left on the ground"]
GENERAL_CLEAN = ["a clean empty surface with nothing on it", "a clean empty table or floor"]


def _get_labels_for_category(category: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Returns problem and clean labels for a given category, or combined set if unknown."""
    cat_key = category.lower().strip() if category else ""
    
    if cat_key in CATEGORY_LABEL_SETS:
        label_set = CATEGORY_LABEL_SETS[cat_key]
        return label_set["problem"] + GENERAL_PROBLEM, label_set["clean"] + GENERAL_CLEAN
    
    # Unknown/all categories fallback
    all_problem = []
    all_clean = []
    for s in CATEGORY_LABEL_SETS.values():
        all_problem.extend(s["problem"])
        all_clean.extend(s["clean"])
    return all_problem + GENERAL_PROBLEM, all_clean + GENERAL_CLEAN

# Also score 4 overlapping zoomed-in parts of the photo and keep the highest problem score,
# so small or scattered litter that is lost in the full view is still noticed.
MULTI_CROP = True


def _views(image: Image.Image, multi_crop: bool) -> List[Image.Image]:
    if not multi_crop:
        return [image]
    w, h = image.size
    cw, ch = int(w * 0.6), int(h * 0.6)
    corners = [(0, 0), (w - cw, 0), (0, h - ch), (w - cw, h - ch)]
    return [image] + [image.crop((x, y, x + cw, y + ch)) for x, y in corners]


def image_problem_probability(
    image: Image.Image,
    problem_labels: List[str],
    clean_labels: List[str],
    multi_crop: Optional[bool] = None
) -> float:
    """Problem probability for one image: problem labels vs clean labels (highest over the views)."""
    if multi_crop is None:
        multi_crop = MULTI_CROP
    views = _views(image.convert("RGB"), multi_crop)
    probs = _label_probs(views, problem_labels + clean_labels)  # one row per view
    return float(probs[:, :len(problem_labels)].sum(axis=1).max())


def get_image_problem_probability(
    image_path: str,
    problem_labels: List[str],
    clean_labels: List[str]
) -> float:
    """Computes problem probability for a single image file against problem vs clean label sets."""
    return image_problem_probability(Image.open(image_path), problem_labels, clean_labels)


def compare_images_with_clip(
    before_image: Image.Image,
    after_image: Image.Image,
    category: Optional[str] = None,
    threshold: Optional[float] = None,
    ratio: Optional[float] = None
) -> Dict[str, Any]:
    """Same decision as compare_photos_with_clip, for images already in memory."""
    threshold = CLIP_THRESHOLD if threshold is None else threshold
    ratio = CLIP_RATIO if ratio is None else ratio
    problem_labels, clean_labels = _get_labels_for_category(category)
    before_prob = image_problem_probability(before_image, problem_labels, clean_labels)
    after_prob = image_problem_probability(after_image, problem_labels, clean_labels)
    issue_present = (after_prob >= threshold) or (after_prob >= ratio * before_prob)
    return {"issue_present": issue_present, "before_problem_prob": before_prob, "after_problem_prob": after_prob}


def compare_photos_with_clip(
    before_image_path: str,
    after_image_path: str,
    category: Optional[str] = None,
    threshold: Optional[float] = None,
    ratio: Optional[float] = None
) -> Dict[str, Any]:
    """
    Compares the after photo against the before photo using local CLIP model.
    issue_present = True if after_problem_prob >= threshold OR after_problem_prob >= ratio * before_problem_prob.
    """
    if threshold is None:
        threshold = CLIP_THRESHOLD
    if ratio is None:
        ratio = CLIP_RATIO

    try:
        if not os.path.exists(before_image_path) or not os.path.exists(after_image_path):
            return {
                "status": "UNAVAILABLE",
                "issue_present": None,
                "confidence": None,
                "before_problem_prob": None,
                "after_problem_prob": None,
                "before_percent": None,
                "after_percent": None,
                "explanation": "AI Vision (CLIP): Check unavailable (skipped - image files not found)",
                "error": "Image file not found"
            }

        problem_labels, clean_labels = _get_labels_for_category(category)

        before_prob = get_image_problem_probability(before_image_path, problem_labels, clean_labels)
        after_prob = get_image_problem_probability(after_image_path, problem_labels, clean_labels)

        # issue_present = True if EITHER condition is met
        issue_present = (after_prob >= threshold) or (after_prob >= ratio * before_prob)

        before_percent = round(before_prob * 100.0, 1)
        after_percent = round(after_prob * 100.0, 1)

        if issue_present:
            explanation = f"AI Vision (CLIP): problem not reduced (before {before_percent}%, after {after_percent}%) (-50 pts)"
        else:
            explanation = f"AI Vision (CLIP): problem reduced from {before_percent}% to {after_percent}% (Pass)"

        return {
            "status": "COMPLETED",
            "issue_present": issue_present,
            "before_problem_prob": round(before_prob, 4),
            "after_problem_prob": round(after_prob, 4),
            "before_percent": before_percent,
            "after_percent": after_percent,
            "explanation": explanation,
            "error": None
        }

    except Exception as e:
        print(f"Error during CLIP photo comparison: {e}")
        return {
            "status": "UNAVAILABLE",
            "issue_present": None,
            "confidence": None,
            "before_problem_prob": None,
            "after_problem_prob": None,
            "before_percent": None,
            "after_percent": None,
            "explanation": "AI Vision (CLIP): Check unavailable (skipped)",
            "error": str(e)
        }

def analyze_resolution_with_clip(
    image_path: str,
    category: Optional[str] = None,
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """Single image CLIP classification fallback for convenience."""
    if threshold is None:
        threshold = CLIP_THRESHOLD

    try:
        if not os.path.exists(image_path):
            return {
                "status": "UNAVAILABLE",
                "issue_present": None,
                "confidence": None,
                "explanation": "AI Vision (CLIP): Check unavailable (skipped - image file not found)",
                "error": "Image file not found"
            }

        problem_labels, clean_labels = _get_labels_for_category(category)
        prob = get_image_problem_probability(image_path, problem_labels, clean_labels)
        issue_present = (prob >= threshold)
        percent = round(prob * 100.0, 1)

        return {
            "status": "COMPLETED",
            "issue_present": issue_present,
            "confidence": percent,
            "garbage_prob": round(prob, 4),
            "clean_prob": round(1.0 - prob, 4),
            "explanation": f"AI Vision (CLIP): {'issue still visible' if issue_present else 'area looks clean'} (confidence {percent}%)",
            "error": None
        }
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "issue_present": None,
            "confidence": None,
            "explanation": "AI Vision (CLIP): Check unavailable (skipped)",
            "error": str(e)
        }

RELEVANT_LABELS = [
    "garbage, litter or waste on the ground",
    "an overflowing garbage bin",
    "a drain blocked with rubbish",
    "construction debris or rubble",
    "a dirty unswept street",
    "empty snack packets and wrappers thrown on a table or floor",
    "plastic wrappers and litter left on a surface"
]
NOT_RELEVANT = {
    "a close-up photo of a person's face": "a person's face",
    "a photo of people posing or sitting together": "people",
    "a selfie of one or more people": "people",
    "a group of people in a room": "people",
    "a person looking at the camera": "people",
    "a screenshot, document or computer screen": "a screen or document",
    "a meal served on a plate": "food",
    "a dog, cat or other animal": "an animal",
    "a car, bike or other vehicle": "a vehicle",
    "a clean empty room": "a clean room",
    "a clean empty table or surface with nothing on it": "a clean surface"
}


def photo_relevance(image: Image.Image) -> Tuple[bool, Optional[str]]:
    """Checks if the photo is relevant to a civic problem using CLIP."""
    not_relevant_labels = list(NOT_RELEVANT.keys())
    probs = _label_probs([image.convert("RGB")], RELEVANT_LABELS + not_relevant_labels)[0]

    relevant_prob = float(probs[:len(RELEVANT_LABELS)].sum())
    if relevant_prob > 0.5:
        return True, None

    best = not_relevant_labels[int(probs[len(RELEVANT_LABELS):].argmax())]
    return False, NOT_RELEVANT[best]


def build_text_cache() -> None:
    """Precompute every label's text embedding with the original model (run on the laptop after
    changing any label): backend\venv\Scripts\python.exe -m app.services.clip_service"""
    import torch
    labels = list(dict.fromkeys(
        [l for s in CATEGORY_LABEL_SETS.values() for l in s["problem"] + s["clean"]]
        + GENERAL_PROBLEM + GENERAL_CLEAN + RELEVANT_LABELS + list(NOT_RELEVANT)))
    model, processor = _get_clip_model()
    with torch.no_grad():
        tokens = processor(text=labels, return_tensors="pt", padding=True)
        emb = model.text_projection(model.text_model(**tokens).pooler_output)
        emb = (emb / emb.norm(dim=-1, keepdim=True)).numpy()
        scale = float(model.logit_scale.exp())
    np.savez(TEXT_CACHE, labels=np.array(labels), embeds=emb, scale=scale)
    print(f"Saved {len(labels)} label embeddings to {TEXT_CACHE}")


if __name__ == "__main__":
    build_text_cache()
