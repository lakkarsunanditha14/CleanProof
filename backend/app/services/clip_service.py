import os
import torch
from typing import Dict, Any, Optional
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from app.config import CLIP_THRESHOLD

# Cached singleton model and processor instances
_model: Optional[CLIPModel] = None
_processor: Optional[CLIPProcessor] = None

GARBAGE_LABELS = [
    "a photo of garbage and litter on a street",
    "a photo of an overflowing garbage bin",
    "a photo of a drain blocked with plastic waste",
    "a photo of construction debris on a footpath"
]

CLEAN_LABELS = [
    "a photo of a clean street",
    "a photo of a clean empty footpath",
    "a photo of a clean drain",
    "a photo of a tidy public place"
]

ALL_LABELS = GARBAGE_LABELS + CLEAN_LABELS

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

def analyze_resolution_with_clip(
    image_path: str,
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Analyzes resolution photo using local CLIP model.
    Zero-shot classifies image against GARBAGE vs CLEAN labels.
    """
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

        model, processor = _get_clip_model()
        image = Image.open(image_path).convert("RGB")

        inputs = processor(text=ALL_LABELS, images=image, return_tensors="pt", padding=True)

        with torch.no_grad():
            outputs = model(**inputs)
            logits_per_image = outputs.logits_per_image # image-to-text classification logits
            probs = logits_per_image.softmax(dim=-1).squeeze(0).tolist()

        # Sum probabilities per group
        garbage_prob = sum(probs[:len(GARBAGE_LABELS)])
        clean_prob = sum(probs[len(GARBAGE_LABELS):])

        issue_present = (garbage_prob >= threshold)
        
        if issue_present:
            confidence = round(garbage_prob * 100.0, 1)
            explanation = f"AI Vision (CLIP): issue still visible (confidence {confidence}%)"
        else:
            confidence = round(clean_prob * 100.0, 1)
            explanation = f"AI Vision (CLIP): area looks clean (confidence {confidence}%)"

        return {
            "status": "COMPLETED",
            "issue_present": issue_present,
            "confidence": confidence,
            "garbage_prob": round(garbage_prob, 4),
            "clean_prob": round(clean_prob, 4),
            "explanation": explanation,
            "error": None
        }

    except Exception as e:
        print(f"Error during CLIP vision verification: {e}")
        return {
            "status": "UNAVAILABLE",
            "issue_present": None,
            "confidence": None,
            "explanation": "AI Vision (CLIP): Check unavailable (skipped)",
            "error": str(e)
        }
