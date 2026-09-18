from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class SLAStatusSchema(BaseModel):
    status: str              # "On time", "Near deadline", "Breached"
    hours_remaining: float
    hours_elapsed: float
    total_sla_hours: int
    deadline: datetime
    is_breached: bool

class ResolutionResponse(BaseModel):
    id: int
    complaint_id: int
    after_image_path: str
    after_latitude: Optional[float] = None
    after_longitude: Optional[float] = None
    after_timestamp: datetime
    score: int
    verdict: str
    reasons: List[str]
    clip_issue_present: Optional[bool] = None
    clip_confidence: Optional[float] = None
    clip_explanation: Optional[str] = None
    clip_status: str
    gps_distance_meters: Optional[float] = None
    gps_passed: Optional[bool] = None
    timestamp_passed: Optional[bool] = None
    duplicate_passed: Optional[bool] = None
    perceptual_hash: Optional[str] = None
    exif_passed: Optional[bool] = None
    has_exif_metadata: bool
    human_review_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReopenLogResponse(BaseModel):
    id: int
    complaint_id: int
    reopen_image_path: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ComplaintBase(BaseModel):
    title: str
    category: str
    description: Optional[str] = None
    ward: str
    latitude: float
    longitude: float

class ComplaintResponse(BaseModel):
    id: int
    title: str
    category: str
    description: Optional[str] = None
    ward: str
    latitude: float
    longitude: float
    before_image_path: str
    before_image_hash: Optional[str] = None
    before_has_exif: bool
    status: str
    created_at: datetime
    reopened_at: Optional[datetime] = None
    updated_at: datetime
    sla_hours: int
    sla_deadline: datetime
    reopen_count: int
    sla_info: SLAStatusSchema
    latest_resolution: Optional[ResolutionResponse] = None
    resolutions: List[ResolutionResponse] = []
    reopen_logs: List[ReopenLogResponse] = []

    class Config:
        from_attributes = True

class ComplaintListItem(BaseModel):
    id: int
    title: str
    category: str
    ward: str
    latitude: float
    longitude: float
    status: str
    created_at: datetime
    reopened_at: Optional[datetime] = None
    sla_hours: int
    sla_deadline: datetime
    sla_status: str
    reopen_count: int
    before_image_path: str
    latest_verdict: Optional[str] = None
    latest_score: Optional[int] = None
    human_review_status: Optional[str] = None

    class Config:
        from_attributes = True

class ReopenRequest(BaseModel):
    reason: Optional[str] = None

class HumanReviewRequest(BaseModel):
    decision: str = Field(..., description="'Genuine' or 'Confirmed fake'")

class DashboardStatsResponse(BaseModel):
    total_complaints: int
    active_complaints: int
    resolved_complaints: int
    reopened_complaints: int
    sla_adherence_percent: float
    total_breached: int
    false_closures_count: int
    flagged_pending_review_count: int

class WardSLABreakdown(BaseModel):
    ward: str
    total: int
    resolved: int
    on_time: int
    breached: int
    adherence_percent: float
    false_closures: int

class CategorySLABreakdown(BaseModel):
    category: str
    sla_hours: int
    total: int
    resolved: int
    on_time: int
    breached: int
    adherence_percent: float

class FalseClosureStat(BaseModel):
    ward: str
    false_closure_count: int
    flagged_suspicious: int
    flagged_fake: int

class MapPointResponse(BaseModel):
    id: int
    title: str
    category: str
    ward: str
    latitude: float
    longitude: float
    status: str
    created_at: datetime
    sla_status: str
    verdict: Optional[str] = None
    score: Optional[int] = None
    before_image_path: str
    after_image_path: Optional[str] = None
