from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import Complaint, Resolution
from app.services.exif_service import (
    calculate_image_hash,
    compare_image_hashes,
    haversine_distance,
    extract_exif_metadata
)
from app.services.gemini_service import analyze_complaint_resolution_with_gemini

def run_resolution_verification_pipeline(
    db: Session,
    complaint: Complaint,
    after_image_path: str,
    after_latitude_input: Optional[float] = None,
    after_longitude_input: Optional[float] = None,
    after_timestamp_input: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Executes the 5-check resolution verification engine using EXACT scoring rules:
    - Verification uses ONLY EXIF data for GPS and timestamp checks.
    - Base score: 100
    - Gemini says issue still present: -50
    - GPS distance between before and after > 50m: -25 (Missing EXIF GPS: -25)
    - After-photo timestamp earlier than complaint time: -20 (Missing EXIF Timestamp: -20)
    - Duplicate after-photo (imagehash distance <= 5 with any previous after-photo): -30
    - Missing EXIF metadata: -10
    - Minimum score: 0
    - Verdict: >= 75 VERIFIED, 40-74 SUSPICIOUS, < 40 LIKELY FAKE
    - Always returns reasons list in plain English.
    """
    score = 100
    reasons: List[str] = []

    # 1. Extract EXIF metadata & calculate perceptual hash of after-photo
    exif_data = extract_exif_metadata(after_image_path)
    after_phash = calculate_image_hash(after_image_path)

    # EXIF-extracted values (used strictly for verification checks)
    exif_lat = exif_data.get("latitude")
    exif_lon = exif_data.get("longitude")
    exif_ts = exif_data.get("timestamp")

    # DB storage fallback values (saved to Resolution model record)
    db_after_lat = after_latitude_input or exif_lat
    db_after_lon = after_longitude_input or exif_lon
    db_after_ts = after_timestamp_input or exif_ts or datetime.utcnow()

    # CHECK 1: Gemini Vision Analysis
    gemini_res = analyze_complaint_resolution_with_gemini(
        before_image_path=complaint.before_image_path,
        after_image_path=after_image_path,
        category=complaint.category,
        description=complaint.description
    )

    gemini_status = gemini_res.get("status", "UNAVAILABLE")
    gemini_is_resolved = gemini_res.get("is_resolved")
    gemini_confidence = gemini_res.get("confidence")
    gemini_explanation = gemini_res.get("explanation")

    if gemini_status == "COMPLETED":
        if gemini_is_resolved is False:
            score -= 50
            reasons.append("Gemini Vision: AI analysis indicates issue is STILL PRESENT in resolution photo (-50 pts)")
        else:
            reasons.append(f"Gemini Vision: Confirmed issue appears resolved ({gemini_explanation}) (Pass)")
    else:
        # Check unavailable: skip deduction
        reasons.append("Gemini Vision: Check unavailable (skipped)")

    # CHECK 2: GPS Distance Check (< 50m limit) - EXIF ONLY
    gps_passed = False
    gps_distance_meters = None

    if exif_lat is not None and exif_lon is not None:
        gps_distance_meters = haversine_distance(
            complaint.latitude, complaint.longitude,
            exif_lat, exif_lon
        )
        if gps_distance_meters > 50.0:
            score -= 25
            reasons.append(f"GPS Distance: Resolution photo is {round(gps_distance_meters, 1)}m away from complaint site (>50m limit) (-25 pts)")
        else:
            gps_passed = True
            reasons.append(f"GPS Distance: Location within {round(gps_distance_meters, 1)}m of complaint site (Pass)")
    else:
        # Missing EXIF GPS metadata
        score -= 25
        reasons.append("Location cannot be verified: photo has no GPS data")

    # CHECK 3: Timestamp Order Check - EXIF ONLY (IST UTC+5:30 conversion)
    timestamp_passed = False

    if exif_ts is not None:
        # EXIF DateTimeOriginal is local Indian time (IST, UTC+5:30)
        # Convert EXIF timestamp to UTC before comparing with complaint.created_at
        exif_ts_utc = exif_ts - timedelta(hours=5, minutes=30)

        if exif_ts_utc < complaint.created_at:
            score -= 20
            reasons.append(f"Timestamp: After-photo timestamp ({exif_ts.strftime('%Y-%m-%d %H:%M')} IST) is earlier than complaint creation time ({complaint.created_at.strftime('%Y-%m-%d %H:%M')} UTC) (-20 pts)")
        else:
            timestamp_passed = True
            reasons.append("Timestamp: After-photo timestamp is later than complaint time (Pass)")
    else:
        # Missing EXIF timestamp
        score -= 20
        reasons.append("Time cannot be verified: photo has no timestamp")

    # CHECK 4: Duplicate Image Check (imagehash distance <= 5)
    duplicate_passed = True
    is_duplicate = False
    if after_phash:
        # Query all previous resolutions across DB
        previous_resolutions = db.query(Resolution).filter(Resolution.perceptual_hash.isnot(None)).all()
        for prev_res in previous_resolutions:
            if prev_res.perceptual_hash:
                dist = compare_image_hashes(after_phash, prev_res.perceptual_hash)
                if dist is not None and dist <= 5:
                    is_duplicate = True
                    break
        
        if is_duplicate:
            duplicate_passed = False
            score -= 30
            reasons.append("Duplicate Image: Perceptual image hash matches a previously submitted resolution photo (-30 pts)")
        else:
            reasons.append("Duplicate Image: Perceptual hash is unique (Pass)")
    else:
        reasons.append("Duplicate Image: Could not compute image hash")

    # CHECK 5: EXIF Metadata Check
    has_exif = exif_data.get("has_exif", False)
    exif_passed = has_exif
    if not has_exif:
        score -= 10
        reasons.append("EXIF Metadata: Missing camera/EXIF metadata (-10 pts)")
    else:
        reasons.append("EXIF Metadata: Original camera EXIF metadata present (Pass)")

    # Ensure score floor is 0
    final_score = max(0, score)

    # Determine Verdict
    if final_score >= 75:
        verdict = "VERIFIED"
    elif final_score >= 40:
        verdict = "SUSPICIOUS"
    else:
        verdict = "LIKELY FAKE"

    return {
        "score": final_score,
        "verdict": verdict,
        "reasons": reasons,
        "after_latitude": db_after_lat,
        "after_longitude": db_after_lon,
        "after_timestamp": db_after_ts,
        "gemini_is_resolved": gemini_is_resolved,
        "gemini_confidence": gemini_confidence,
        "gemini_explanation": gemini_explanation,
        "gemini_status": gemini_status,
        "gps_distance_meters": gps_distance_meters,
        "gps_passed": gps_passed,
        "timestamp_passed": timestamp_passed,
        "duplicate_passed": duplicate_passed,
        "perceptual_hash": after_phash,
        "exif_passed": exif_passed,
        "has_exif_metadata": has_exif
    }
