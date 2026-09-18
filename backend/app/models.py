from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False) # 'garbage dump', 'unswept street', 'construction debris', 'blocked drain'
    description = Column(Text, nullable=True)
    ward = Column(String(50), nullable=False)       # 'Ward 1', 'Ward 2', etc.
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    before_image_path = Column(String(500), nullable=False)
    before_image_hash = Column(String(100), nullable=True)
    before_has_exif = Column(Boolean, default=False)
    status = Column(String(50), default="OPEN")     # 'OPEN', 'RESOLVED', 'REOPENED'
    created_at = Column(DateTime, default=datetime.utcnow)
    reopened_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sla_hours = Column(Integer, nullable=False)
    sla_deadline = Column(DateTime, nullable=False)
    reopen_count = Column(Integer, default=0)

    resolutions = relationship("Resolution", back_populates="complaint", cascade="all, delete-orphan", order_by="desc(Resolution.created_at)")
    reopen_logs = relationship("ReopenLog", back_populates="complaint", cascade="all, delete-orphan", order_by="desc(ReopenLog.created_at)")


class Resolution(Base):
    __tablename__ = "resolutions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    after_image_path = Column(String(500), nullable=False)
    after_latitude = Column(Float, nullable=True)
    after_longitude = Column(Float, nullable=True)
    after_timestamp = Column(DateTime, default=datetime.utcnow)
    
    score = Column(Integer, nullable=False) # 0 to 100
    verdict = Column(String(50), nullable=False) # 'VERIFIED', 'SUSPICIOUS', 'LIKELY FAKE'
    reasons = Column(JSON, nullable=False, default=list)

    clip_issue_present = Column(Boolean, nullable=True)
    clip_confidence = Column(Float, nullable=True)
    clip_explanation = Column(Text, nullable=True)
    clip_status = Column(String(50), default="COMPLETED") # 'COMPLETED', 'UNAVAILABLE'

    gps_distance_meters = Column(Float, nullable=True)
    gps_passed = Column(Boolean, nullable=True)
    timestamp_passed = Column(Boolean, nullable=True)
    duplicate_passed = Column(Boolean, nullable=True)
    perceptual_hash = Column(String(100), nullable=True)
    exif_passed = Column(Boolean, nullable=True)
    has_exif_metadata = Column(Boolean, default=False)

    human_review_status = Column(String(50), default="PENDING") # 'PENDING', 'Genuine', 'Confirmed fake'

    # Evidence read from the photo file (EXIF): when and where it was actually taken
    photo_taken_at = Column(DateTime, nullable=True)
    photo_latitude = Column(Float, nullable=True)
    photo_longitude = Column(Float, nullable=True)

    # Deadline accountability: was it closed after the deadline, by how much, and why
    closed_late = Column(Boolean, default=False)
    late_by_hours = Column(Float, nullable=True)
    delay_reason = Column(String(100), nullable=True)
    delay_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="resolutions")


class ReopenLog(Base):
    __tablename__ = "reopen_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    reopen_image_path = Column(String(500), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="reopen_logs")
