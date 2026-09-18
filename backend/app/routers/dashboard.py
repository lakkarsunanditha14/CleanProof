from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import VALID_WARDS, VALID_CATEGORIES, SLA_HOURS
from app.models import Complaint, Resolution, ReopenLog
from app.schemas import (
    DashboardStatsResponse,
    WardSLABreakdown,
    CategorySLABreakdown,
    FalseClosureStat,
    MapPointResponse
)
from app.services.sla_service import calculate_sla_info

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Returns high-level platform statistics.
    """
    complaints = db.query(Complaint).all()
    total_complaints = len(complaints)
    
    active_complaints = sum(1 for c in complaints if c.status in ["OPEN", "REOPENED"])
    resolved_complaints = sum(1 for c in complaints if c.status == "RESOLVED")
    
    reopened_count = db.query(ReopenLog).count()
    
    # Calculate SLA status for all complaints
    breached_count = 0
    on_time_count = 0
    
    for c in complaints:
        latest_res = c.resolutions[0] if c.resolutions else None
        res_time = latest_res.created_at if latest_res else None
        
        sla = calculate_sla_info(
            created_at=c.created_at,
            sla_hours=c.sla_hours,
            current_status=c.status,
            resolution_time=res_time
        )
        
        if sla.is_breached:
            breached_count += 1
        else:
            on_time_count += 1

    sla_adherence_percent = round((on_time_count / total_complaints * 100.0), 1) if total_complaints > 0 else 100.0

    # False closures / flagged resolutions count
    resolutions = db.query(Resolution).all()
    false_closures_count = sum(
        1 for r in resolutions 
        if r.verdict in ["SUSPICIOUS", "LIKELY FAKE"] or r.human_review_status == "Confirmed fake"
    )
    
    flagged_pending_review_count = sum(
        1 for r in resolutions 
        if r.verdict in ["SUSPICIOUS", "LIKELY FAKE"] and r.human_review_status == "PENDING"
    )

    return DashboardStatsResponse(
        total_complaints=total_complaints,
        active_complaints=active_complaints,
        resolved_complaints=resolved_complaints,
        reopened_complaints=reopened_count,
        sla_adherence_percent=sla_adherence_percent,
        total_breached=breached_count,
        false_closures_count=false_closures_count,
        flagged_pending_review_count=flagged_pending_review_count
    )


@router.get("/sla-by-ward", response_model=List[WardSLABreakdown])
def get_sla_by_ward(db: Session = Depends(get_db)):
    """
    Returns SLA adherence breakdown per ward.
    """
    results = []
    complaints = db.query(Complaint).all()
    resolutions = db.query(Resolution).all()

    for ward in VALID_WARDS:
        ward_complaints = [c for c in complaints if c.ward == ward]
        total = len(ward_complaints)
        resolved = sum(1 for c in ward_complaints if c.status == "RESOLVED")
        
        on_time = 0
        breached = 0
        for c in ward_complaints:
            latest_res = c.resolutions[0] if c.resolutions else None
            res_time = latest_res.created_at if latest_res else None
            sla = calculate_sla_info(c.created_at, c.sla_hours, c.status, res_time)
            if sla.is_breached:
                breached += 1
            else:
                on_time += 1
                
        adherence_percent = round((on_time / total * 100.0), 1) if total > 0 else 100.0

        # False closures in this ward
        ward_complaint_ids = {c.id for c in ward_complaints}
        false_closures = sum(
            1 for r in resolutions 
            if r.complaint_id in ward_complaint_ids and (
                r.verdict in ["SUSPICIOUS", "LIKELY FAKE"] or r.human_review_status == "Confirmed fake"
            )
        )

        results.append(
            WardSLABreakdown(
                ward=ward,
                total=total,
                resolved=resolved,
                on_time=on_time,
                breached=breached,
                adherence_percent=adherence_percent,
                false_closures=false_closures
            )
        )

    return results


@router.get("/sla-by-category", response_model=List[CategorySLABreakdown])
def get_sla_by_category(db: Session = Depends(get_db)):
    """
    Returns SLA adherence breakdown per category.
    """
    results = []
    complaints = db.query(Complaint).all()

    for cat in VALID_CATEGORIES:
        cat_complaints = [c for c in complaints if c.category == cat]
        total = len(cat_complaints)
        resolved = sum(1 for c in cat_complaints if c.status == "RESOLVED")
        
        on_time = 0
        breached = 0
        for c in cat_complaints:
            latest_res = c.resolutions[0] if c.resolutions else None
            res_time = latest_res.created_at if latest_res else None
            sla = calculate_sla_info(c.created_at, c.sla_hours, c.status, res_time)
            if sla.is_breached:
                breached += 1
            else:
                on_time += 1
                
        adherence_percent = round((on_time / total * 100.0), 1) if total > 0 else 100.0

        results.append(
            CategorySLABreakdown(
                category=cat,
                sla_hours=SLA_HOURS[cat],
                total=total,
                resolved=resolved,
                on_time=on_time,
                breached=breached,
                adherence_percent=adherence_percent
            )
        )

    return results


@router.get("/false-closures", response_model=List[FalseClosureStat])
def get_false_closures_stat(db: Session = Depends(get_db)):
    """
    Returns counts of false closures and flagged resolutions per ward.
    """
    results = []
    complaints = db.query(Complaint).all()
    resolutions = db.query(Resolution).all()

    for ward in VALID_WARDS:
        ward_c_ids = {c.id for c in complaints if c.ward == ward}
        ward_resolutions = [r for r in resolutions if r.complaint_id in ward_c_ids]
        
        suspicious_cnt = sum(1 for r in ward_resolutions if r.verdict == "SUSPICIOUS")
        fake_cnt = sum(1 for r in ward_resolutions if r.verdict == "LIKELY FAKE")
        confirmed_fake_cnt = sum(1 for r in ward_resolutions if r.human_review_status == "Confirmed fake")
        
        total_false_closures = suspicious_cnt + fake_cnt + confirmed_fake_cnt

        results.append(
            FalseClosureStat(
                ward=ward,
                false_closure_count=total_false_closures,
                flagged_suspicious=suspicious_cnt,
                flagged_fake=fake_cnt
            )
        )

    return results


@router.get("/map-data", response_model=List[MapPointResponse])
def get_map_data(db: Session = Depends(get_db)):
    """
    Returns GeoJSON-style complaint points for Leaflet markers & heatmap intensity.
    """
    complaints = db.query(Complaint).all()
    points = []

    for c in complaints:
        latest_res = c.resolutions[0] if c.resolutions else None
        res_time = latest_res.created_at if latest_res else None
        
        sla = calculate_sla_info(c.created_at, c.sla_hours, c.status, res_time)

        points.append(
            MapPointResponse(
                id=c.id,
                title=c.title,
                category=c.category,
                ward=c.ward,
                latitude=c.latitude,
                longitude=c.longitude,
                status=c.status,
                created_at=c.created_at,
                sla_status=sla.status,
                verdict=latest_res.verdict if latest_res else None,
                score=latest_res.score if latest_res else None,
                before_image_path=c.before_image_path,
                after_image_path=latest_res.after_image_path if latest_res else None
            )
        )

    return points
