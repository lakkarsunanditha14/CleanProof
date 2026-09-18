import uuid
import shutil
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.config import IMAGES_DIR, VALID_CATEGORIES, VALID_WARDS, SLA_HOURS
from app.models import Complaint, Resolution, ReopenLog
from app.schemas import (
    ComplaintResponse,
    ComplaintListItem,
    ResolutionResponse,
    ReopenLogResponse,
    SLAStatusSchema
)
from app.services.sla_service import calculate_sla_info, get_category_sla_hours
from app.services.exif_service import calculate_image_hash, extract_exif_metadata
from app.services.verification import run_resolution_verification_pipeline

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

def _format_complaint_response(complaint: Complaint) -> ComplaintResponse:
    latest_resolution = complaint.resolutions[0] if complaint.resolutions else None
    resolution_time = latest_resolution.created_at if latest_resolution else None
    
    sla_info = calculate_sla_info(
        created_at=complaint.created_at,
        sla_hours=complaint.sla_hours,
        current_status=complaint.status,
        resolution_time=resolution_time
    )

    resolutions_resp = [ResolutionResponse.model_validate(r) for r in complaint.resolutions]
    reopen_logs_resp = [ReopenLogResponse.model_validate(r) for r in complaint.reopen_logs]
    latest_res_resp = ResolutionResponse.model_validate(latest_resolution) if latest_resolution else None

    return ComplaintResponse(
        id=complaint.id,
        title=complaint.title,
        category=complaint.category,
        description=complaint.description,
        ward=complaint.ward,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        before_image_path=complaint.before_image_path,
        before_image_hash=complaint.before_image_hash,
        before_has_exif=complaint.before_has_exif,
        status=complaint.status,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        sla_hours=complaint.sla_hours,
        sla_deadline=complaint.sla_deadline,
        reopen_count=complaint.reopen_count,
        sla_info=sla_info,
        latest_resolution=latest_res_resp,
        resolutions=resolutions_resp,
        reopen_logs=reopen_logs_resp
    )

@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)

async def create_complaint(
    title: str = Form(...),
    category: str = Form(...),
    ward: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Citizen submits a new complaint with a 'before' photo.
    Calculates SLA deadline, image hash, and EXIF metadata.
    """
    cat_lower = category.lower().strip()
    if cat_lower not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Valid options: {VALID_CATEGORIES}"
        )

    # Save uploaded file
    file_ext = Path(photo.filename).suffix or ".jpg"
    filename = f"before_{uuid.uuid4().hex}{file_ext}"
    file_path = IMAGES_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    saved_path_str = str(file_path.resolve()).replace("\\", "/")

    # Extract EXIF & perceptual hash for before-photo
    exif_data = extract_exif_metadata(saved_path_str)
    before_hash = calculate_image_hash(saved_path_str)

    sla_h = get_category_sla_hours(cat_lower)
    now = datetime.utcnow()
    sla_dl = now + timedelta(hours=sla_h)

    complaint = Complaint(
        title=title.strip(),
        category=cat_lower,
        description=description.strip() if description else None,
        ward=ward.strip(),
        latitude=latitude,
        longitude=longitude,
        before_image_path=saved_path_str,
        before_image_hash=before_hash,
        before_has_exif=exif_data.get("has_exif", False),
        status="OPEN",
        created_at=now,
        updated_at=now,
        sla_hours=sla_h,
        sla_deadline=sla_dl,
        reopen_count=0
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return _format_complaint_response(complaint)


@router.get("", response_model=List[ComplaintListItem])
def list_complaints(
    ward: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sla_status: Optional[str] = Query(None),
    verdict: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List complaints with optional filters (ward, category, status, SLA status, verdict).
    """
    query = db.query(Complaint).order_by(desc(Complaint.created_at))

    if ward:
        query = query.filter(Complaint.ward == ward)
    if category:
        query = query.filter(Complaint.category == category.lower())
    if status:
        query = query.filter(Complaint.status == status.upper())

    complaints = query.all()
    results = []

    for c in complaints:
        latest_res = c.resolutions[0] if c.resolutions else None
        res_time = latest_res.created_at if latest_res else None
        
        sla = calculate_sla_info(
            created_at=c.created_at,
            sla_hours=c.sla_hours,
            current_status=c.status,
            resolution_time=res_time
        )

        # Filter by sla_status if requested
        if sla_status and sla.status.lower() != sla_status.lower():
            continue

        # Filter by verdict if requested
        c_verdict = latest_res.verdict if latest_res else None
        if verdict and (not c_verdict or c_verdict.upper() != verdict.upper()):
            continue

        results.append(
            ComplaintListItem(
                id=c.id,
                title=c.title,
                category=c.category,
                ward=c.ward,
                latitude=c.latitude,
                longitude=c.longitude,
                status=c.status,
                created_at=c.created_at,
                sla_hours=c.sla_hours,
                sla_deadline=c.sla_deadline,
                sla_status=sla.status,
                reopen_count=c.reopen_count,
                before_image_path=c.before_image_path,
                latest_verdict=c_verdict,
                latest_score=latest_res.score if latest_res else None,
                human_review_status=latest_res.human_review_status if latest_res else None
            )
        )

    return results


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a single complaint.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return _format_complaint_response(complaint)


@router.post("/{complaint_id}/resolve", response_model=ResolutionResponse)
async def resolve_complaint(
    complaint_id: int,
    photo: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Municipal worker uploads an 'after' photo to mark a complaint resolved.
    Runs the automated 5-check verification engine and records verdict & score.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Save resolution image
    file_ext = Path(photo.filename).suffix or ".jpg"
    filename = f"after_{uuid.uuid4().hex}{file_ext}"
    file_path = IMAGES_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    after_path_str = str(file_path.resolve()).replace("\\", "/")

    # Run verification engine
    verification_result = run_resolution_verification_pipeline(
        db=db,
        complaint=complaint,
        after_image_path=after_path_str,
        after_latitude_input=latitude,
        after_longitude_input=longitude,
        after_timestamp_input=datetime.utcnow()
    )

    # Save resolution record
    resolution = Resolution(
        complaint_id=complaint.id,
        after_image_path=after_path_str,
        after_latitude=verification_result["after_latitude"],
        after_longitude=verification_result["after_longitude"],
        after_timestamp=verification_result["after_timestamp"],
        score=verification_result["score"],
        verdict=verification_result["verdict"],
        reasons=verification_result["reasons"],
        clip_issue_present=verification_result["clip_issue_present"],
        clip_confidence=verification_result["clip_confidence"],
        clip_explanation=verification_result["clip_explanation"],
        clip_status=verification_result["clip_status"],
        gps_distance_meters=verification_result["gps_distance_meters"],
        gps_passed=verification_result["gps_passed"],
        timestamp_passed=verification_result["timestamp_passed"],
        duplicate_passed=verification_result["duplicate_passed"],
        perceptual_hash=verification_result["perceptual_hash"],
        exif_passed=verification_result["exif_passed"],
        has_exif_metadata=verification_result["has_exif_metadata"],
        human_review_status="PENDING",
        created_at=datetime.utcnow()
    )

    # Update complaint status to RESOLVED
    complaint.status = "RESOLVED"
    complaint.updated_at = datetime.utcnow()

    db.add(resolution)
    db.commit()
    db.refresh(resolution)

    return ResolutionResponse.model_validate(resolution)


@router.post("/{complaint_id}/reopen", response_model=ComplaintResponse)
async def reopen_complaint(
    complaint_id: int,
    photo: UploadFile = File(...),
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Citizen uploads a new photo to reopen a resolved complaint.
    Reopens the complaint and restarts the SLA clock.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.status != "RESOLVED":
        raise HTTPException(
            status_code=400,
            detail=f"Only RESOLVED complaints can be reopened. Current status is '{complaint.status}'."
        )

    # Save reopen photo
    file_ext = Path(photo.filename).suffix or ".jpg"
    filename = f"reopen_{uuid.uuid4().hex}{file_ext}"
    file_path = IMAGES_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    reopen_path_str = str(file_path.resolve()).replace("\\", "/")

    # Create ReopenLog
    log = ReopenLog(
        complaint_id=complaint.id,
        reopen_image_path=reopen_path_str,
        reason=reason.strip() if reason else None,
        created_at=datetime.utcnow()
    )

    # Update complaint status & restart SLA clock
    now = datetime.utcnow()
    complaint.status = "REOPENED"
    complaint.reopen_count += 1
    complaint.created_at = now  # Restart SLA clock!
    complaint.updated_at = now
    complaint.sla_deadline = now + timedelta(hours=complaint.sla_hours)

    db.add(log)
    db.commit()
    db.refresh(complaint)

    return _format_complaint_response(complaint)
