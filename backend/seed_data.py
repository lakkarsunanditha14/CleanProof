import os
import uuid
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import piexif
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app.config import IMAGES_DIR
from app.models import Complaint, Resolution, ReopenLog
from app.services.exif_service import calculate_image_hash

def create_synthetic_image(filename: str, color: tuple, label: str, add_exif: bool = True) -> str:
    filepath = IMAGES_DIR / filename
    img = Image.new("RGB", (400, 300), color=color)
    draw = ImageDraw.Draw(img)
    draw.text((20, 140), label, fill=(255, 255, 255))
    
    img.save(filepath, "JPEG")
    
    if add_exif:
        exif_dict = {"Exif": {piexif.ExifIFD.DateTimeOriginal: datetime.utcnow().strftime("%Y:%m:%d %H:%M:%S").encode("utf-8")}}
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(filepath))
        
    return str(filepath.resolve()).replace("\\", "/")

def seed_database():
    print("Resetting database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        print("Generating synthetic complaints and resolutions...")

        # Sample data definitions
        seeds = [
            # 1. Ward 1 - Garbage Dump - Resolved (VERIFIED)
            {
                "title": "Overflowing garbage dump near Sector 4 Market",
                "category": "garbage dump",
                "ward": "Ward 1",
                "lat": 28.6139, "lon": 77.2090,
                "created_offset_h": 6,
                "sla_hours": 12,
                "status": "RESOLVED",
                "before_label": "BEFORE: Garbage Pile Sector 4",
                "after_label": "AFTER: Cleaned Street Sector 4",
                "verdict": "VERIFIED",
                "score": 90,
                "reasons": ["AI Vision (CLIP): area looks clean (confidence 92.5%)", "GPS Distance: Location within 12m of complaint site (Pass)", "Timestamp: After-photo timestamp is later than complaint time (Pass)", "Duplicate Image: Perceptual hash is unique (Pass)", "EXIF Metadata: Original camera EXIF metadata present (Pass)"],
                "after_dist_m": 12.0
            },
            # 2. Ward 2 - Unswept Street - Resolved (SUSPICIOUS - Location mismatch)
            {
                "title": "Unswept leaves and waste on Main Road",
                "category": "unswept street",
                "ward": "Ward 2",
                "lat": 28.6200, "lon": 77.2150,
                "created_offset_h": 18,
                "sla_hours": 24,
                "status": "RESOLVED",
                "before_label": "BEFORE: Leaf pile Main Road",
                "after_label": "AFTER: Cleaned Park (Wrong Location)",
                "verdict": "SUSPICIOUS",
                "score": 65,
                "reasons": ["AI Vision (CLIP): area looks clean (confidence 88.0%)", "GPS Distance: Resolution photo is 120m away from complaint site (>50m limit) (-25 pts)", "Timestamp: After-photo timestamp is later than complaint time (Pass)", "Duplicate Image: Perceptual hash is unique (Pass)", "EXIF Metadata: Missing camera/EXIF metadata (-10 pts)"],
                "after_dist_m": 120.0
            },
            # 3. Ward 3 - Construction Debris - Resolved (LIKELY FAKE - Issue still present + Duplicate image)
            {
                "title": "Construction rubble blocking pedestrian walkway",
                "category": "construction debris",
                "ward": "Ward 3",
                "lat": 28.6250, "lon": 77.2200,
                "created_offset_h": 80, # Breached SLA
                "sla_hours": 72,
                "status": "RESOLVED",
                "before_label": "BEFORE: Bricks & Debris Walkway",
                "after_label": "AFTER: Debris Still Present Fake",
                "verdict": "LIKELY FAKE",
                "score": 20,
                "reasons": ["AI Vision (CLIP): issue still visible (confidence 85.0%) (-50 pts)", "GPS Distance: Location within 8m of complaint site (Pass)", "Timestamp: After-photo timestamp is later than complaint time (Pass)", "Duplicate Image: Perceptual image hash matches a previously submitted resolution photo (-30 pts)", "EXIF Metadata: Missing camera/EXIF metadata (-10 pts)"],
                "after_dist_m": 8.0
            },
            # 4. Ward 4 - Blocked Drain - Open (Near Deadline)
            {
                "title": "Severe drain blockage causing waterlogging",
                "category": "blocked drain",
                "ward": "Ward 4",
                "lat": 28.6300, "lon": 77.2250,
                "created_offset_h": 40, # 40h elapsed out of 48h SLA -> Near deadline
                "sla_hours": 48,
                "status": "OPEN",
                "before_label": "BEFORE: Blocked Drain Block B",
                "after_label": None
            },
            # 5. Ward 5 - Garbage Dump - Reopened
            {
                "title": "Uncollected trash bags behind Community Center",
                "category": "garbage dump",
                "ward": "Ward 5",
                "lat": 28.6350, "lon": 77.2300,
                "created_offset_h": 2, # Reopened 2h ago
                "sla_hours": 12,
                "status": "REOPENED",
                "before_label": "BEFORE: Trash Bags Community Center",
                "after_label": "AFTER: Allegedly Cleaned Bags",
                "reopen_label": "REOPEN: Trash dumped again same spot",
                "verdict": "SUSPICIOUS",
                "score": 60,
                "reasons": ["AI Vision (CLIP): area looks clean (confidence 80.0%)", "GPS Distance: Location within 45m of complaint site (Pass)", "Timestamp: After-photo timestamp is later than complaint time (Pass)", "Duplicate Image: Perceptual hash matches a previously submitted photo (-30 pts)", "EXIF Metadata: Original camera EXIF metadata present (Pass)"],
                "after_dist_m": 45.0
            }
        ]

        for idx, s in enumerate(seeds, start=1):
            created_dt = now - timedelta(hours=s["created_offset_h"])
            deadline_dt = created_dt + timedelta(hours=s["sla_hours"])

            before_file = f"seed_before_{idx}.jpg"
            before_path = create_synthetic_image(before_file, (180, 50, 50), s["before_label"], add_exif=True)
            before_hash = calculate_image_hash(before_path)

            complaint = Complaint(
                title=s["title"],
                category=s["category"],
                description=f"Synthetic test complaint #{idx} in {s['ward']}",
                ward=s["ward"],
                latitude=s["lat"],
                longitude=s["lon"],
                before_image_path=before_path,
                before_image_hash=before_hash,
                before_has_exif=True,
                status=s["status"],
                created_at=created_dt,
                updated_at=now,
                sla_hours=s["sla_hours"],
                sla_deadline=deadline_dt,
                reopen_count=1 if s["status"] == "REOPENED" else 0
            )

            db.add(complaint)
            db.commit()
            db.refresh(complaint)

            if s["after_label"]:
                after_file = f"seed_after_{idx}.jpg"
                after_color = (50, 150, 50) if s["verdict"] == "VERIFIED" else (150, 120, 40)
                after_path = create_synthetic_image(after_file, after_color, s["after_label"], add_exif=(s["verdict"] == "VERIFIED"))
                after_hash = calculate_image_hash(after_path)

                res_dt = created_dt + timedelta(hours=min(s["created_offset_h"] - 1, 5))

                resolution = Resolution(
                    complaint_id=complaint.id,
                    after_image_path=after_path,
                    after_latitude=s["lat"] + (s["after_dist_m"] / 111000.0),
                    after_longitude=s["lon"],
                    after_timestamp=res_dt,
                    score=s["score"],
                    verdict=s["verdict"],
                    reasons=s["reasons"],
                    clip_issue_present=(s["verdict"] != "VERIFIED"),
                    clip_confidence=85.0 if s["verdict"] != "VERIFIED" else 92.5,
                    clip_explanation="Synthetic seed CLIP analysis.",
                    clip_status="COMPLETED",
                    gps_distance_meters=s["after_dist_m"],
                    gps_passed=(s["after_dist_m"] <= 50.0),
                    timestamp_passed=True,
                    duplicate_passed=(s["score"] > 30),
                    perceptual_hash=after_hash,
                    exif_passed=(s["verdict"] == "VERIFIED"),
                    has_exif_metadata=(s["verdict"] == "VERIFIED"),
                    human_review_status="PENDING" if s["verdict"] != "VERIFIED" else "Genuine",
                    created_at=res_dt
                )
                db.add(resolution)
                db.commit()

            if s.get("reopen_label"):
                reopen_file = f"seed_reopen_{idx}.jpg"
                reopen_path = create_synthetic_image(reopen_file, (200, 80, 40), s["reopen_label"], add_exif=True)
                reopen_log = ReopenLog(
                    complaint_id=complaint.id,
                    reopen_image_path=reopen_path,
                    reason="Garbage was dumped again at the same spot right after worker left.",
                    created_at=now - timedelta(hours=1)
                )
                db.add(reopen_log)
                db.commit()

        print("Database successfully seeded with synthetic test data!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
