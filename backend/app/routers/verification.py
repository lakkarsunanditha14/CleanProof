from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Resolution, Complaint
from app.schemas import ResolutionResponse, FlaggedResolutionResponse, HumanReviewRequest

router = APIRouter(prefix="/api/verification", tags=["Verification"])

@router.get("/flagged", response_model=List[FlaggedResolutionResponse])
def get_flagged_resolutions(db: Session = Depends(get_db)):
    """
    Returns list of resolutions flagged as SUSPICIOUS or LIKELY FAKE
    awaiting human inspection & review.
    """
    flagged = (
        db.query(Resolution)
        .filter(Resolution.verdict.in_(["SUSPICIOUS", "LIKELY FAKE"]))
        .order_by(desc(Resolution.created_at))
        .all()
    )
    return [
        FlaggedResolutionResponse(
            **ResolutionResponse.model_validate(r).model_dump(),
            complaint_title=r.complaint.title,
            complaint_category=r.complaint.category,
            complaint_ward=r.complaint.ward,
            complaint_before_image_path=r.complaint.before_image_path,
            complaint_status=r.complaint.status,
        )
        for r in flagged
    ]


@router.post("/{resolution_id}/review", response_model=ResolutionResponse)
def review_flagged_resolution(
    resolution_id: int,
    body: HumanReviewRequest,
    db: Session = Depends(get_db)
):
    """
    Human reviewer sets the decision for a flagged resolution ('Genuine' or 'Confirmed fake').
    If marked 'Confirmed fake', reopens the complaint for active worker resolution.
    """
    decision = body.decision.strip()
    if decision not in ["Genuine", "Confirmed fake"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid decision. Must be 'Genuine' or 'Confirmed fake'."
        )

    resolution = db.query(Resolution).filter(Resolution.id == resolution_id).first()
    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    resolution.human_review_status = decision

    complaint = db.query(Complaint).filter(Complaint.id == resolution.complaint_id).first()
    if complaint and decision == "Confirmed fake":
        # If confirmed fake by human inspector, reopen the complaint
        complaint.status = "REOPENED"
        complaint.reopen_count += 1

    db.commit()
    db.refresh(resolution)

    return ResolutionResponse.model_validate(resolution)
