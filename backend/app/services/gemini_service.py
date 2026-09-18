import os
import json
from typing import Dict, Any, Optional
from PIL import Image
from google import genai
from app.config import GEMINI_API_KEY, GEMINI_MODEL

def analyze_complaint_resolution_with_gemini(
    before_image_path: str,
    after_image_path: str,
    category: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends before and after photos to Gemini Vision API using google-genai library to analyze if the issue is resolved.
    If Gemini API key is missing, network fails, or permission/quota is denied, handles gracefully:
    returns status='UNAVAILABLE' without crashing.
    """
    if not GEMINI_API_KEY:
        print("Gemini API key is not configured.")
        return {
            "status": "UNAVAILABLE",
            "is_resolved": None,
            "confidence": None,
            "explanation": "Gemini vision check unavailable (skipped - GEMINI_API_KEY not configured)",
            "error": "Missing GEMINI_API_KEY"
        }

    try:
        # Check image files exist
        if not os.path.exists(before_image_path) or not os.path.exists(after_image_path):
            return {
                "status": "UNAVAILABLE",
                "is_resolved": None,
                "confidence": None,
                "explanation": "Gemini vision check unavailable (skipped - image files not found)",
                "error": "Image file not found"
            }

        img_before = Image.open(before_image_path)
        img_after = Image.open(after_image_path)

        prompt = f"""
You are an expert civic inspection AI verifying if a civic complaint has been genuinely resolved.

Complaint Category: {category}
Complaint Details: {description or 'No extra description provided'}

You are provided with two images:
1. BEFORE Photo (original complaint showing the problem)
2. AFTER Photo (uploaded to claim the problem is resolved)

Analyze both images carefully.
Determine if the issue (e.g. {category}) shown in the BEFORE photo is still present in the AFTER photo.

Respond ONLY with a valid JSON object in the following format:
{{
  "is_resolved": true/false,
  "confidence": 0.0 to 1.0,
  "explanation": "Clear, concise 1-2 sentence explanation of whether the issue is cleaned/repaired or still visible."
}}
"""

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[img_before, img_after, prompt]
        )
        response_text = response.text

        # Clean JSON markdown fences if present
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        parsed_json = json.loads(cleaned_text)

        is_resolved = bool(parsed_json.get("is_resolved", False))
        confidence = float(parsed_json.get("confidence", 0.8))
        explanation = str(parsed_json.get("explanation", "Gemini vision analysis completed."))

        return {
            "status": "COMPLETED",
            "is_resolved": is_resolved,
            "confidence": confidence,
            "explanation": explanation,
            "error": None
        }

    except Exception as e:
        print(f"Error during Gemini API verification: {e}")
        return {
            "status": "UNAVAILABLE",
            "is_resolved": None,
            "confidence": None,
            "explanation": f"Gemini vision check unavailable (skipped)",
            "error": str(e)
        }
