import os
import sys
import shutil
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw
import piexif
from sqlalchemy.orm import Session

# Add backend directory to sys.path so app modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import engine, Base, SessionLocal
from app.config import IMAGES_DIR, SLA_HOURS, VALID_WARDS, VALID_CATEGORIES, DELAY_REASONS
from app.models import Complaint, Resolution, ReopenLog
from app.services.exif_service import calculate_image_hash
from app.services.sla_service import calculate_sla_info

# Ward Center Coordinates (Hyderabad Wards)
WARD_CENTRES = {
    "Ameerpet": (17.4375, 78.4483),
    "Kukatpally": (17.4948, 78.3996),
    "Madhapur": (17.4483, 78.3915),
    "Secunderabad": (17.4399, 78.4983),
    "Dilsukhnagar": (17.3688, 78.5247),
    "Mehdipatnam": (17.3950, 78.4400),
    "Begumpet": (17.4447, 78.4664),
    "LB Nagar": (17.3457, 78.5522)
}

# Synthetic history closures: which checks failed, per verdict. Penalties match verification.py.
HISTORY_PENALTY = {"clip": 50, "gps": 30, "time": 30, "dup": 30, "exif": 10}
HISTORY_PROFILES = {
    "VERIFIED": [()],
    "SUSPICIOUS": [("gps",), ("time",), ("dup",), ("clip",)],
    "LIKELY FAKE": [("clip", "gps"), ("clip", "time"), ("gps", "time", "exif")],
}


def history_reasons(failed):
    no_exif = "exif" in failed
    return [
        "AI Vision (CLIP): problem not reduced (-50 pts)" if "clip" in failed else "AI Vision (CLIP): problem reduced (Pass)",
        ("Location cannot be verified: photo has no GPS data (-30 pts)" if no_exif else
         "GPS Distance: Resolution photo is 850m away from complaint site (>50m limit) (-30 pts)") if "gps" in failed
        else "GPS Distance: Location within 15m of complaint site (Pass)",
        ("Time cannot be verified: photo has no timestamp (-30 pts)" if no_exif else
         "Timestamp: After-photo was taken before the complaint (-30 pts)") if "time" in failed
        else "Timestamp: After-photo timestamp is later than complaint time (Pass)",
        "Duplicate Image: Perceptual image hash matches a previously submitted resolution photo (-30 pts)" if "dup" in failed
        else "Duplicate Image: Perceptual hash is unique (Pass)",
        "EXIF Metadata: Missing camera/EXIF metadata (-10 pts)" if no_exif else "EXIF Metadata: Original camera EXIF metadata present (Pass)",
    ]


def deg_to_exif_format(val: float):
    """Converts decimal degrees float into EXIF GPS tuple format ((d, 1), (m, 1), (s, 100))."""
    abs_val = abs(val)
    d = int(abs_val)
    m = int((abs_val - d) * 60)
    s = int(round(((abs_val - d) * 60 - m) * 60 * 100))
    return ((d, 1), (m, 1), (s, 100))

def add_exif_to_jpeg(file_path: str, lat: float, lon: float, dt_str: str):
    """Inserts EXIF GPS and DateTimeOriginal metadata into a JPEG file using piexif."""
    lat_tuple = deg_to_exif_format(lat)
    lon_tuple = deg_to_exif_format(lon)
    lat_ref = b'N' if lat >= 0 else b'S'
    lon_ref = b'E' if lon >= 0 else b'W'

    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: lat_ref,
        piexif.GPSIFD.GPSLatitude: lat_tuple,
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
        piexif.GPSIFD.GPSLongitude: lon_tuple
    }

    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: dt_str.encode('utf-8')
    }

    exif_dict = {"0th": {}, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}, "thumbnail": None}
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, file_path)

def convert_to_jpeg(src_path: Path, dst_path: Path):
    """Converts any image file to RGB JPEG format."""
    with Image.open(src_path) as img:
        rgb_img = img.convert("RGB")
        rgb_img.save(dst_path, "JPEG", quality=95)

def reset_demo_database():
    print("=== REBUILDING ENTIRE DEMO DATABASE & DEMO UPLOADS ===")
    
    # Fix random seed for 100% reproducible background dataset
    random.seed(42)

    delay_rng = random.Random(2026)  # separate stream so delay reasons do not shift other seeded data
    profile_rng = random.Random(7)  # separate stream for which checks failed in history records
    # 1. Wipe & Re-create DB tables
    print("1. Wiping & re-creating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Ensure directories exist
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    upload_dir = PROJECT_ROOT / "data" / "demo" / "upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    demo_before_dir = PROJECT_ROOT / "data" / "demo" / "before"
    demo_after_dir = PROJECT_ROOT / "data" / "demo" / "after"
    demo_fraud_dir = PROJECT_ROOT / "data" / "demo" / "fraud"

    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    dt_30m_ago_ist = (now_ist - timedelta(minutes=30)).strftime("%Y:%m:%d %H:%M:%S")

    db: Session = SessionLocal()

    try:
        # 2. Create 6 LIVE DEMO complaints (unresolved OPEN status)
        print("2. Creating 6 live demo complaints...")

        demo_complaints_def = [
            {
                "title": "Overflowing garbage dump near Ameerpet Metro Station",
                "category": "garbage dump",
                "ward": "Ameerpet",
                "lat": 17.4377, "lon": 78.4485,
                "created_offset_h": 2,
                "before_file": "before_1.jpg"
            },
            {
                "title": "Clogged drainage pipe causing waterlogging in Kukatpally Phase 3",
                "category": "blocked drain",
                "ward": "Kukatpally",
                "lat": 17.4950, "lon": 78.3998,
                "created_offset_h": 2,
                "before_file": "before_2.png"
            },
            {
                "title": "Broken bricks and concrete debris blocking Madhapur 100ft Road",
                "category": "construction debris",
                "ward": "Madhapur",
                "lat": 17.4485, "lon": 78.3917,
                "created_offset_h": 2,
                "before_file": "before_3.png"
            },
            {
                "title": "Unswept leaves and plastic litter along Secunderabad Clock Tower",
                "category": "unswept street",
                "ward": "Secunderabad",
                "lat": 17.4401, "lon": 78.4985,
                "created_offset_h": 26, # 24h SLA -> already 2h overdue: live demo of the delay reason
                "before_file": "before_4.png"
            },
            {
                "title": "Trash bags dumped outside Dilsukhnagar Bus Depot",
                "category": "garbage dump",
                "ward": "Dilsukhnagar",
                "lat": 17.3690, "lon": 78.5249,
                "created_offset_h": 2,
                "before_file": "before_5.png"
            },
            {
                "title": "Garbage pile spilling onto road near Mehdipatnam Flyover",
                "category": "garbage dump",
                "ward": "Mehdipatnam",
                "lat": 17.3952, "lon": 78.4402,
                "created_offset_h": 10, # 10h elapsed out of 12h SLA -> Near deadline!
                "before_file": "before_6.png"
            }
        ]

        live_complaint_ids = []

        for idx, dc in enumerate(demo_complaints_def, start=1):
            src_file = demo_before_dir / dc["before_file"]
            dst_filename = f"live_before_{idx}.jpg"
            dst_path = IMAGES_DIR / dst_filename

            # Convert to JPEG in uploads folder
            convert_to_jpeg(src_file, dst_path)
            path_str = str(dst_path.resolve()).replace("\\", "/")

            # Calculate phash
            b_hash = calculate_image_hash(path_str)

            c_time = now_utc - timedelta(hours=dc["created_offset_h"])
            sla_h = SLA_HOURS[dc["category"]]
            deadline = c_time + timedelta(hours=sla_h)

            c = Complaint(
                title=dc["title"],
                category=dc["category"],
                description=f"Live demo complaint #{idx} in {dc['ward']} ({dc['category']}).",
                ward=dc["ward"],
                latitude=dc["lat"],
                longitude=dc["lon"],
                before_image_path=path_str,
                before_image_hash=b_hash,
                before_has_exif=True,
                status="OPEN",
                created_at=c_time,
                updated_at=c_time,
                sla_hours=sla_h,
                sla_deadline=deadline,
                reopen_count=0
            )

            db.add(c)
            db.commit()
            db.refresh(c)
            live_complaint_ids.append(c.id)

        print(f"Created live demo complaint IDs: {live_complaint_ids}")

        # 3. Create data/demo/upload/ ready-to-upload files
        print("3. Generating data/demo/upload/ ready-to-upload files...")

        # genuine_after_1..6.jpg (EXIF GPS within ~8m of complaint location, DateTimeOriginal = 30m ago IST)
        for idx, dc in enumerate(demo_complaints_def, start=1):
            ext = ".jpg" if idx == 1 else ".png"
            src_after = demo_after_dir / f"after_{idx}{ext}"
            target_upload = upload_dir / f"genuine_after_{idx}.jpg"

            convert_to_jpeg(src_after, target_upload)

            # GPS within ~8m of complaint
            lat_exif = dc["lat"] + 0.00007
            lon_exif = dc["lon"] + 0.00007
            add_exif_to_jpeg(str(target_upload), lat_exif, lon_exif, dt_30m_ago_ist)

        # fake_reused_dirty_2.jpg (from before_2, EXIF GPS = complaint 2 location, DateTimeOriginal = 1 day ago)
        fake_2_path = upload_dir / "fake_reused_dirty_2.jpg"
        convert_to_jpeg(demo_before_dir / "before_2.png", fake_2_path)
        dt_1day_ago_ist = (now_ist - timedelta(days=1)).strftime("%Y:%m:%d %H:%M:%S")
        add_exif_to_jpeg(str(fake_2_path), 17.4950, 78.3998, dt_1day_ago_ist)

        # fake_wrong_place_for_1.jpg (from after_3, EXIF GPS = complaint 3 location in Madhapur, far from Ameerpet)
        fake_wrong_place_path = upload_dir / "fake_wrong_place_for_1.jpg"
        convert_to_jpeg(demo_after_dir / "after_3.png", fake_wrong_place_path)
        add_exif_to_jpeg(str(fake_wrong_place_path), 17.4485, 78.3917, dt_30m_ago_ist)

        # fake_ai_clean_for_6.jpg (from fraud_ai_clean.png, converted to JPEG with NO EXIF at all)
        fake_ai_clean_path = upload_dir / "fake_ai_clean_for_6.jpg"
        convert_to_jpeg(demo_fraud_dir / "fraud_ai_clean.png", fake_ai_clean_path)
        # Note: No piexif call -> NO EXIF metadata at all!

        # Write README.txt
        readme_path = upload_dir / "README.txt"
        ids = live_complaint_ids
        readme_content = f"""=== CLEANPROOF LIVE DEMO: WHAT TO UPLOAD, IN THIS ORDER ===
Run scripts/reset_demo.py right before the demo. It regenerates these photos
with fresh timestamps, so they only match the complaints from that reset.
Upload on the Worker page (Resolve button on the complaint card).

STEP 1  Genuine clean-up
  Upload genuine_after_1.jpg to complaint #{ids[0]} (Ameerpet)
  Expected: 100/100 VERIFIED (all 5 checks pass)

STEP 2  Dirty photo re-uploaded as "proof"
  Upload fake_reused_dirty_2.jpg to complaint #{ids[1]} (Kukatpally)
  Expected: 20/100 LIKELY FAKE
  (CLIP: problem not reduced -50, photo older than the complaint -30)

STEP 3  Citizen reopens
  Track page, complaint #{ids[1]}: Reopen with any photo
  Expected: status REOPENED, deadline restarts

STEP 4  AI-generated "clean" photo (no camera data)
  Upload fake_ai_clean_for_6.jpg to complaint #{ids[5]} (Mehdipatnam)
  Expected: 30/100 LIKELY FAKE (no GPS -30, no timestamp -30, no EXIF -10)
  Then on the Review page click "Confirmed fake"

STEP 5  Real clean photo from a different place
  Upload fake_wrong_place_for_1.jpg to complaint #{ids[4]} (Dilsukhnagar)
  Expected: 70/100 SUSPICIOUS (photo taken km away from the complaint -30)

STEP 6  Closed after the deadline (reason required)
  Complaint #{ids[3]} (Secunderabad) is already 2h past its 24h deadline.
  Click Resolve, upload genuine_after_4.jpg, pick a delay reason (e.g. Vehicle or staff shortage)
  Expected: 100/100 VERIFIED, "Closed 2h after the deadline. Reason: ..."
  (Without a reason the closure is refused.)

STEP 7  Live camera (the answer to "what if the worker uploads an old photo?")
  Report issue -> "Take live photo" of some paper litter on the floor -> category Garbage dump -> Submit
  Pick up the litter -> Worker -> that complaint -> "Take live photo" -> Mark resolved
  Expected: VERIFIED, evidence shows "Live in-app capture, time set by the server".
  Point: workers use the in-app camera, so an old gallery photo cannot even be selected.
  (Allow camera and location in Chrome when asked. Uses the laptop webcam.)

STEP 8  Dashboard
  Show the hotspots: Dilsukhnagar (fake closures) and Kukatpally (missed deadlines)
  and the "Why deadlines were missed" chart

Other files: genuine_after_2..6.jpg are genuine clean-ups for complaints #{ids[1]}..#{ids[5]}.
Only upload to complaints #{ids[0]}..#{ids[5]}. The other complaints are synthetic history with
no photos and no real location, so any upload to them is flagged.
Note: fake_wrong_place_for_1.jpg is the same photo as genuine_after_3.jpg,
so whichever of the two is uploaded second is also flagged as a duplicate (-30).
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # 4. Generate ~200 BACKGROUND complaints for dashboard analytics
        print("4. Generating ~200 synthetic background complaints across 8 wards...")

        sample_titles = {
            "garbage dump": [
                "Overflowing waste bins near market entrance",
                "Uncollected garbage bags dumping along main road",
                "Litter accumulation near residential colony corner",
                "Waste heap causing foul odor near bus stop",
                "Plastic trash and wet waste piled on pavement"
            ],
            "blocked drain": [
                "Drain clogged with plastic bottles and silt",
                "Roadside storm drain overflow during rain",
                "Sewage pipe blockage causing standing water",
                "Blocked open drain near vegetable market",
                "Stagnant water due to clogged drainage outlet"
            ],
            "construction debris": [
                "Concrete slabs and bricks dumped on sidewalk",
                "Construction gravel blocking side road lane",
                "Unused building material left on public path",
                "Demolition debris piled outside vacant plot",
                "Sand and stone rubble obstructing driveway"
            ],
            "unswept street": [
                "Dry leaves and food wrappers covering street",
                "Footpath unswept for multiple days near school",
                "Scattered paper litter along commercial stretch",
                "Dirty sidewalk with dust and fallen leaves",
                "Unswept pavement near metro station gate"
            ]
        }

        wards_list = list(WARD_CENTRES.keys())
        hotspot_wards = ["Kukatpally", "Dilsukhnagar"]

        total_bg = 194  # 194 bg + 6 live = 200 total complaints

        # Sample photos for history records, matched by category. Copies are named history_*
        # so the UI can tag them as samples. History resolutions keep a NULL perceptual hash,
        # so these copies never trigger the duplicate check on live uploads.
        history_pairs = {"garbage dump": [1, 5, 6], "blocked drain": [2], "construction debris": [3], "unswept street": [4]}
        for n in range(1, 7):
            for kind, folder in (("before", demo_before_dir), ("after", demo_after_dir)):
                src = next(folder.glob(f"{kind}_{n}.*"))
                convert_to_jpeg(src, IMAGES_DIR / f"history_{kind}_{n}.jpg")

        def history_photo(kind, n):
            return str((IMAGES_DIR / f"history_{kind}_{n}.jpg").resolve()).replace("\\", "/")

        for bg_i in range(1, total_bg + 1):
            ward = random.choice(wards_list)
            is_hotspot = ward in hotspot_wards

            category = random.choice(VALID_CATEGORIES)
            pair_n = history_pairs[category][bg_i % len(history_pairs[category])]
            title = random.choice(sample_titles[category])
            
            # Lat/Lng within ~1.5km of ward center
            center_lat, center_lon = WARD_CENTRES[ward]
            lat = round(center_lat + random.uniform(-0.012, 0.012), 4)
            lon = round(center_lon + random.uniform(-0.012, 0.012), 4)

            # Age between 0.5 days and 30 days
            days_ago = random.uniform(0.5, 30.0)
            c_created = now_utc - timedelta(days=days_ago)
            sla_h = SLA_HOURS[category]
            deadline = c_created + timedelta(hours=sla_h)

            # Determine status: 70% resolved, 30% open
            is_resolved = random.random() < (0.50 if is_hotspot else 0.75)
            c_status = "RESOLVED" if is_resolved else "OPEN"

            # Check SLA breach
            if not is_resolved and c_created + timedelta(hours=sla_h) < now_utc:
                # Some open ones are breached
                pass

            reopen_cnt = 0
            if is_hotspot and is_resolved and random.random() < 0.25:
                c_status = "REOPENED"
                reopen_cnt = random.randint(1, 2)

            bg_complaint = Complaint(
                title=f"{title} ({ward})",
                category=category,
                description=f"Synthetic background complaint #{bg_i} in {ward}.",
                ward=ward,
                latitude=lat,
                longitude=lon,
                before_image_path=history_photo("before", pair_n),
                before_image_hash=None, # NULL so it never interferes with live duplicate checks
                before_has_exif=True,
                status=c_status,
                created_at=c_created,
                updated_at=c_created + timedelta(hours=random.uniform(1, sla_h)),
                sla_hours=sla_h,
                sla_deadline=deadline,
                reopen_count=reopen_cnt
            )

            db.add(bg_complaint)
            db.commit()
            db.refresh(bg_complaint)

            # Add Synthetic Resolution for RESOLVED complaints
            if c_status in ["RESOLVED", "REOPENED"]:
                # Hotspots have ~3x higher false closures / suspicious / fake rates
                if is_hotspot:
                    verdict_rand = random.random()
                    if verdict_rand < 0.40:
                        verdict, score = "VERIFIED", random.randint(80, 95)
                    elif verdict_rand < 0.75:
                        verdict, score = "SUSPICIOUS", random.randint(45, 74)
                    else:
                        verdict, score = "LIKELY FAKE", random.randint(10, 39)
                else:
                    verdict_rand = random.random()
                    if verdict_rand < 0.85:
                        verdict, score = "VERIFIED", random.randint(82, 98)
                    elif verdict_rand < 0.95:
                        verdict, score = "SUSPICIOUS", random.randint(50, 74)
                    else:
                        verdict, score = "LIKELY FAKE", random.randint(15, 39)

                # Resolution time (on time vs breached)
                if is_hotspot and random.random() < 0.35:
                    res_dt = c_created + timedelta(hours=sla_h + random.uniform(2, 24))
                else:
                    res_dt = c_created + timedelta(hours=random.uniform(1, min(sla_h - 1, 20)))

                # Closed after the deadline: record by how much and a (synthetic) reason
                closed_late = res_dt > deadline
                late_by_hours = round((res_dt - deadline).total_seconds() / 3600, 2) if closed_late else None
                delay_reason = delay_rng.choices(
                    DELAY_REASONS[:-1], weights=[45, 20, 12, 13, 10]
                )[0] if closed_late else None

                # Human review status
                if verdict in ["SUSPICIOUS", "LIKELY FAKE"]:
                    h_rand = random.random()
                    if h_rand < 0.40:
                        human_rev = "Confirmed fake"
                    elif h_rand < 0.70:
                        human_rev = "Genuine"
                    else:
                        # History is already reviewed, so the live review queue starts empty
                        human_rev = "Confirmed fake"
                else:
                    human_rev = "Genuine"

                # Pick which checks failed; the score is exactly 100 minus those penalties
                failed = profile_rng.choice(HISTORY_PROFILES[verdict])
                score = 100 - sum(HISTORY_PENALTY[c] for c in failed)
                has_exif = "exif" not in failed
                reasons_list = history_reasons(failed)
                bg_res = Resolution(
                    complaint_id=bg_complaint.id,
                    # "Problem not reduced" closures show the still-dirty photo, others the clean one
                    after_image_path=history_photo("before" if "clip" in failed else "after", pair_n),
                    after_latitude=lat,
                    after_longitude=lon,
                    after_timestamp=res_dt,
                    score=score,
                    verdict=verdict,
                    reasons=reasons_list,
                    clip_issue_present=("clip" in failed),
                    clip_confidence=88.0,
                    clip_explanation="Synthetic background simulation.",
                    clip_status="COMPLETED",
                    gps_distance_meters=(850.0 if "gps" in failed else 15.0) if has_exif else None,
                    gps_passed=("gps" not in failed),
                    timestamp_passed=("time" not in failed),
                    duplicate_passed=("dup" not in failed),
                    perceptual_hash=None, # NULL hash so it never interferes with live duplicate checks
                    exif_passed=has_exif,
                    has_exif_metadata=has_exif,
                    human_review_status=human_rev,
                    # Photo evidence consistent with the checks above (no EXIF -> nothing recorded)
                    photo_taken_at=None if not has_exif else (
                        c_created - timedelta(days=2) if "time" in failed else res_dt - timedelta(minutes=25)),
                    photo_latitude=None if not has_exif else lat + (0.0077 if "gps" in failed else 0.0001),
                    photo_longitude=None if not has_exif else lon,
                    closed_late=closed_late,
                    late_by_hours=late_by_hours,
                    delay_reason=delay_reason,
                    delay_note=None,
                    created_at=res_dt
                )

                db.add(bg_res)
                db.commit()

        print("5. Calculating final summary metrics...")

        # Summary calculations
        all_c = db.query(Complaint).all()
        all_r = db.query(Resolution).all()

        total_count = len(all_c)
        on_time_total = 0
        breached_total = 0

        ward_counts = {}
        ward_false_closures = {}
        ward_on_time = {}
        ward_total = {}

        for w in VALID_WARDS:
            ward_counts[w] = sum(1 for c in all_c if c.ward == w)
            ward_total[w] = ward_counts[w]
            
            ward_c_ids = {c.id for c in all_c if c.ward == w}
            ward_false_closures[w] = sum(
                1 for r in all_r 
                if r.complaint_id in ward_c_ids and r.verdict in ["SUSPICIOUS", "LIKELY FAKE"] and r.human_review_status != "Genuine"
            )
            
            ward_on_time[w] = 0

        for c in all_c:
            latest_res = c.resolutions[0] if c.resolutions else None
            res_time = latest_res.created_at if latest_res else None
            sla = calculate_sla_info(c.created_at, c.sla_hours, c.status, res_time, reopened_at=c.reopened_at)
            
            if sla.is_breached:
                breached_total += 1
            else:
                on_time_total += 1
                ward_on_time[c.ward] += 1

        overall_sla_adherence = round(on_time_total / total_count * 100.0, 1)

        print("\n=================================================================")
        print("                 DEMO DATABASE RESET COMPLETE                    ")
        print("=================================================================")
        print(f"Total Complaints Created: {total_count} (6 Live + {total_bg} Background)")
        print(f"Overall SLA Adherence:   {overall_sla_adherence}% ({on_time_total} On time, {breached_total} Breached)")
        print("\n--- BREAKDOWN BY WARD ---")
        print(f"{'Ward':<15} | {'Total':<7} | {'SLA Adherence %':<16} | {'False Closures':<14}")
        print("-" * 60)
        for w in VALID_WARDS:
            tot = ward_total[w]
            adh = round(ward_on_time[w] / tot * 100.0, 1) if tot > 0 else 100.0
            fc = ward_false_closures[w]
            print(f"{w:<15} | {tot:<7} | {adh:<16.1f}% | {fc:<14}")
        print("-" * 60)

        print("\n--- 6 LIVE DEMO COMPLAINTS ---")
        print(f"{'ID':<4} | {'Category':<20} | {'Ward':<15} | {'SLA Status':<15} | {'Title'}")
        print("-" * 90)
        for idx, cid in enumerate(live_complaint_ids, start=1):
            c_obj = db.query(Complaint).filter(Complaint.id == cid).first()
            sla_info = calculate_sla_info(c_obj.created_at, c_obj.sla_hours, c_obj.status, reopened_at=c_obj.reopened_at)
            print(f"{c_obj.id:<4} | {c_obj.category:<20} | {c_obj.ward:<15} | {sla_info.status:<15} | {c_obj.title}")
        print("-" * 90)
        print(f"\nReady-to-upload files placed in: {upload_dir}")
        print("See README.txt in upload directory for step-by-step resolution test instructions.\n")

    finally:
        db.close()

if __name__ == "__main__":
    reset_demo_database()
