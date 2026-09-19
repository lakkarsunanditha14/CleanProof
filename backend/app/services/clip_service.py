import os
import torch
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from app.config import CLIP_THRESHOLD, CLIP_RATIO

# Cached singleton model and processor instances
_model: Optional[CLIPModel] = None
_processor: Optional[CLIPProcessor] = None

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
        model_name = "openai/clip-vit-base-patch32"
        print(f"Loading local CLIP model '{model_name}'...")
        _processor = CLIPProcessor.from_pretrained(model_name)
        _model = CLIPModel.from_pretrained(model_name)
        _model.eval()
        print("Local CLIP model loaded successfully.")
    return _model, _processor

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
    all_labels = problem_labels + clean_labels
    model, processor = _get_clip_model()
    views = _views(image.convert("RGB"), multi_crop)

    inputs = processor(text=all_labels, images=views, return_tensors="pt", padding=True)
    with torch.no_grad():
        probs = model(**inputs).logits_per_image.softmax(dim=-1)  # one row per view

    return float(probs[:, :len(problem_labels)].sum(dim=-1).max())


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

def photo_relevance(image: Image.Image) -> Tuple[bool, Optional[str]]:
    """Checks if the photo is relevant to a civic problem using CLIP."""
    model, processor = _get_clip_model()
    
    relevant_labels = [
        "garbage, litter or waste on the ground",
        "an overflowing garbage bin",
        "a drain blocked with rubbish",
        "construction debris or rubble",
        "a dirty unswept street",
        "empty snack packets and wrappers thrown on a table or floor",
        "plastic wrappers and litter left on a surface"
    ]
    not_relevant_mapping = {
        "a close-up photo of a person's face": "a person's face",
        "a photo of people posing or sitting together": "people, not a civic problem",
        "a selfie of one or more people": "people, not a civic problem",
        "a group of people in a room": "people, not a civic problem",
        "a person looking at the camera": "people, not a civic problem",
        "a screenshot, document or computer screen": "a screen or document",
        "a meal served on a plate": "food",
        "a dog, cat or other animal": "an animal",
        "a car, bike or other vehicle": "a vehicle",
        "a clean empty room": "a clean room",
        "a clean empty table or surface with nothing on it": "a clean surface"
    }
    not_relevant_labels = list(not_relevant_mapping.keys())
    all_labels = relevant_labels + not_relevant_labels
    
    inputs = processor(text=all_labels, images=[image.convert("RGB")], return_tensors="pt", padding=True)
    with torch.no_grad():
        probs = model(**inputs).logits_per_image.softmax(dim=-1)[0]
    
    relevant_prob = float(probs[:len(relevant_labels)].sum())
    
    if relevant_prob > 0.5:
        return True, None
        
    not_rel_idx = int(probs[len(relevant_labels):].argmax())
    best_not_rel_label = not_relevant_labels[not_rel_idx]
    best_not_rel_short = not_relevant_mapping[best_not_rel_label]
    
    return False, best_not_rel_short
