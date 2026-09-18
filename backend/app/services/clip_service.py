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

def _get_labels_for_category(category: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Returns problem and clean labels for a given category, or combined set if unknown."""
    cat_key = category.lower().strip() if category else ""
    
    if cat_key in CATEGORY_LABEL_SETS:
        label_set = CATEGORY_LABEL_SETS[cat_key]
        return label_set["problem"], label_set["clean"]
    
    # Unknown/all categories fallback
    all_problem = []
    all_clean = []
    for s in CATEGORY_LABEL_SETS.values():
        all_problem.extend(s["problem"])
        all_clean.extend(s["clean"])
    return all_problem, all_clean

def get_image_problem_probability(
    image_path: str,
    problem_labels: List[str],
    clean_labels: List[str]
) -> float:
    """Computes problem probability for a single image against problem vs clean label sets."""
    all_labels = problem_labels + clean_labels
    model, processor = _get_clip_model()
    image = Image.open(image_path).convert("RGB")

    inputs = processor(text=all_labels, images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        outputs = model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=-1).squeeze(0).tolist()

    return sum(probs[:len(problem_labels)])

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
