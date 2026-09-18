import os
import io
import sys
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.main import app
from app.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = PROJECT_ROOT / "backend" / "test_backend.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def create_dummy_image_bytes(label: str = "Test Image") -> bytes:
    img = Image.new("RGB", (200, 200), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_full_backend_workflow():
    print("=== STARTING ISOLATED BACKEND INTEGRATION TESTS ===")

    # Ensure clean test database state
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    Base.metadata.create_all(bind=test_engine)

    try:
        # 1. Health check
        res = client.get("/")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("[PASS] Root endpoint /")

        # 2. List initial complaints from clean test database (should be 0)
        res = client.get("/api/complaints")
        assert res.status_code == 200
        complaints = res.json()
        assert len(complaints) == 0, f"Expected empty test DB, found {len(complaints)}"
        print(f"[PASS] GET /api/complaints (Isolated DB start count: {len(complaints)})")

        # 3. Create a new complaint (isolated test complaint)
        before_img = create_dummy_image_bytes("Before Waste Dump")
        create_payload = {
            "title": "Uncleared construction rubble near School Gate 2",
            "category": "construction debris",
            "ward": "Ameerpet",
            "latitude": 17.4375,
            "longitude": 78.4483,
            "description": "Debris pile blocking school entrance"
        }
        files = {"photo": ("before_school.jpg", before_img, "image/jpeg")}
        
        res = client.post("/api/complaints", data=create_payload, files=files)
        assert res.status_code == 201, f"Create complaint failed: {res.text}"
        new_c = res.json()
        c_id = new_c["id"]
        assert new_c["sla_hours"] == 72, f"Expected 72h SLA for construction debris, got {new_c['sla_hours']}"
        assert new_c["status"] == "OPEN"
        print(f"[PASS] POST /api/complaints (Created Complaint ID #{c_id}, SLA 72h)")

        # 4. Fetch single complaint detail
        res = client.get(f"/api/complaints/{c_id}")
        assert res.status_code == 200
        detail = res.json()
        assert detail["title"] == create_payload["title"]
        print(f"[PASS] GET /api/complaints/{c_id}")

        # 5. Municipal worker resolves its own complaint
        after_img = create_dummy_image_bytes("After Cleaned Walkway")
        resolve_files = {"photo": ("after_school.jpg", after_img, "image/jpeg")}
        resolve_data = {
            "latitude": "17.4376",  # ~11m distance away (within 50m limit)
            "longitude": "78.4483"
        }
        
        res = client.post(f"/api/complaints/{c_id}/resolve", data=resolve_data, files=resolve_files)
        assert res.status_code == 200, f"Resolve complaint failed: {res.text}"
        resolution = res.json()
        res_id = resolution["id"]
        assert resolution["verdict"] in ["VERIFIED", "SUSPICIOUS", "LIKELY FAKE"]
        assert len(resolution["reasons"]) > 0, "Reasons list should not be empty"
        print(f"[PASS] POST /api/complaints/{c_id}/resolve (Verdict: {resolution['verdict']}, Score: {resolution['score']}, Reasons: {len(resolution['reasons'])})")

        # Verify complaint status updated to RESOLVED
        res = client.get(f"/api/complaints/{c_id}")
        assert res.json()["status"] == "RESOLVED"
        print(f"[PASS] Complaint status updated to RESOLVED")

        # 6. Citizen reopens its own complaint
        reopen_img = create_dummy_image_bytes("Reopen New Photo")
        reopen_files = {"photo": ("reopen_school.jpg", reopen_img, "image/jpeg")}
        reopen_data = {"reason": "Worker only cleared half the debris"}

        res = client.post(f"/api/complaints/{c_id}/reopen", data=reopen_data, files=reopen_files)
        assert res.status_code == 200, f"Reopen complaint failed: {res.text}"
        reopened_c = res.json()
        assert reopened_c["status"] == "REOPENED"
        assert reopened_c["reopen_count"] == 1
        assert reopened_c["reopened_at"] is not None
        print(f"[PASS] POST /api/complaints/{c_id}/reopen (Status: REOPENED, Reopen Count: 1, Reopened At: {reopened_c['reopened_at']})")

        # 7. Dashboard endpoints
        res = client.get("/api/dashboard/stats")
        assert res.status_code == 200
        stats = res.json()
        assert stats["total_complaints"] == 1
        print(f"[PASS] GET /api/dashboard/stats ({stats['total_complaints']} total complaints)")

        res = client.get("/api/dashboard/sla-by-ward")
        assert res.status_code == 200
        ward_breakdown = res.json()
        assert len(ward_breakdown) == 8
        print(f"[PASS] GET /api/dashboard/sla-by-ward ({len(ward_breakdown)} wards)")

        res = client.get("/api/dashboard/sla-by-category")
        assert res.status_code == 200
        cat_breakdown = res.json()
        assert len(cat_breakdown) == 4
        print(f"[PASS] GET /api/dashboard/sla-by-category ({len(cat_breakdown)} categories)")

        res = client.get("/api/dashboard/false-closures")
        assert res.status_code == 200
        fc_stats = res.json()
        assert len(fc_stats) == 8
        print(f"[PASS] GET /api/dashboard/false-closures")

        res = client.get("/api/dashboard/map-data")
        assert res.status_code == 200
        map_points = res.json()
        assert len(map_points) == 1
        print(f"[PASS] GET /api/dashboard/map-data ({len(map_points)} map points)")

        # 8. Human verification endpoint test on its OWN resolution
        res = client.get("/api/verification/flagged")
        assert res.status_code == 200
        flagged = res.json()
        print(f"[PASS] GET /api/verification/flagged ({len(flagged)} flagged items)")

        # Review test complaint's resolution directly
        res = client.post(f"/api/verification/{res_id}/review", json={"decision": "Confirmed fake"})
        assert res.status_code == 200
        assert res.json()["human_review_status"] == "Confirmed fake"
        print(f"[PASS] POST /api/verification/{res_id}/review -> Confirmed fake")

        print("\n=== ALL BACKEND INTEGRATION TESTS PASSED SUCCESSFULLY ===")
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception as e:
                print(f"Cleanup warning: Could not remove {TEST_DB_FILE}: {e}")

if __name__ == "__main__":
    test_full_backend_workflow()

