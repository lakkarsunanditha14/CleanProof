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
from app.services.clip_service import compare_photos_with_clip

def run_resolution_verification_pipeline(
    db: Session,
    complaint: Complaint,
    after_image_path: str,
    after_latitude_input: Optional[float] = None,
    after_longitude_input: Optional[float] = None,
    after_timestamp_input: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Executes the 5-check resolution verification engine using local CLIP model photo comparison:
    - Base score: 100
    - AI Vision (CLIP) problem not reduced: -50 pts
    - GPS distance between before and after > 50m: -30 pts (Missing EXIF GPS: -30 pts)
    - After-photo timestamp earlier than complaint/reopen time: -30 pts (Missing EXIF Timestamp: -30 pts)
    - Duplicate after-photo (imagehash distance <= 5 with any previous after-photo): -30 pts
    - Missing EXIF metadata: -10 pts
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

    # CHECK 1: Local CLIP Vision Comparison (Before vs After)
    clip_res = compare_photos_with_clip(
        before_image_path=complaint.before_image_path,
        after_image_path=after_image_path,
        category=complaint.category
    )

    clip_status = clip_res.get("status", "UNAVAILABLE")
    clip_issue_present = clip_res.get("issue_present")
    before_pct = clip_res.get("before_percent")
    after_pct = clip_res.get("after_percent")
    clip_confidence = after_pct if after_pct is not None else 0.0

    if clip_status == "COMPLETED":
        if clip_issue_present is True:
            score -= 50
            reasons.append(f"AI Vision (CLIP): problem not reduced (before {before_pct}%, after {after_pct}%) (-50 pts)")
        else:
            reasons.append(f"AI Vision (CLIP): problem reduced from {before_pct}% to {after_pct}% (Pass)")
    else:
        # Check unavailable: skip deduction
        reasons.append("AI Vision (CLIP): Check unavailable (skipped)")

    # CHECK 2: GPS Distance Check (< 50m limit) - EXIF ONLY (-30 pts penalty)
    gps_passed = False
    gps_distance_meters = None

    if exif_lat is not None and exif_lon is not None:
        gps_distance_meters = haversine_distance(
            complaint.latitude, complaint.longitude,
            exif_lat, exif_lon
        )
        if gps_distance_meters > 50.0:
            score -= 30
            reasons.append(f"GPS Distance: Resolution photo is {round(gps_distance_meters, 1)}m away from complaint site (>50m limit) (-30 pts)")
        else:
            gps_passed = True
            reasons.append(f"GPS Distance: Location within {round(gps_distance_meters, 1)}m of complaint site (Pass)")
    else:
        # Missing EXIF GPS metadata
        score -= 30
        reasons.append("Location cannot be verified: photo has no GPS data (-30 pts)")

    # CHECK 3: Timestamp Order Check - EXIF ONLY (IST UTC+5:30 conversion)
    timestamp_passed = False

    if exif_ts is not None:
        # EXIF DateTimeOriginal is local Indian time (IST, UTC+5:30)
        # Convert EXIF timestamp to UTC before comparing with start time
        exif_ts_utc = exif_ts - timedelta(hours=5, minutes=30)

        is_reopened = (complaint.status == "REOPENED") or (complaint.reopened_at is not None)
        compare_time = complaint.reopened_at if (is_reopened and complaint.reopened_at) else complaint.created_at

        if exif_ts_utc < compare_time:
            score -= 30
            if is_reopened and complaint.reopened_at:
                reasons.append("Timestamp: After-photo was taken before the complaint was reopened (-30 pts)")
            else:
                reasons.append(f"Timestamp: After-photo timestamp ({exif_ts.strftime('%Y-%m-%d %H:%M')} IST) is earlier than complaint creation time ({(complaint.created_at + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M')} IST) (-30 pts)")
        else:
            timestamp_passed = True
            reasons.append("Timestamp: After-photo timestamp is later than complaint time (Pass)")
    else:
        # Missing EXIF timestamp
        score -= 30
        reasons.append("Time cannot be verified: photo has no timestamp (-30 pts)")

    # CHECK 4: Duplicate Image Check (imagehash distance <= 5, ignores null/empty hashes)
    duplicate_passed = True
    is_duplicate = False
    if after_phash and after_phash.strip():
        # Query all previous resolutions with non-empty perceptual hash
        previous_resolutions = (
            db.query(Resolution)
            .filter(Resolution.perceptual_hash.isnot(None))
            .filter(Resolution.perceptual_hash != "")
            .all()
        )
        for prev_res in previous_resolutions:
            if prev_res.perceptual_hash and prev_res.perceptual_hash.strip():
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
        reasons.append("Duplicate Image: Perceptual hash not available (Pass)")

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
        "clip_issue_present": clip_issue_present,
        "clip_confidence": clip_confidence,
        "clip_explanation": clip_res.get("explanation"),
        "clip_status": clip_status,
        "gps_distance_meters": gps_distance_meters,
        "gps_passed": gps_passed,
        "timestamp_passed": timestamp_passed,
        "duplicate_passed": duplicate_passed,
        "perceptual_hash": after_phash,
        "exif_passed": exif_passed,
        "has_exif_metadata": has_exif
    }
