import io
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_dummy_image_bytes(label: str = "Test Image") -> bytes:
    img = Image.new("RGB", (200, 200), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_full_backend_workflow():
    print("=== STARTING BACKEND ENDPOINT INTEGRATION TESTS ===")

    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Root endpoint /")

    # 2. List initial complaints from seed data
    res = client.get("/api/complaints")
    assert res.status_code == 200
    complaints = res.json()
    assert len(complaints) > 0, "Expected seeded complaints"
    print(f"[PASS] GET /api/complaints (Found {len(complaints)} complaints)")

    # 3. Create a new complaint
    before_img = create_dummy_image_bytes("Before Waste Dump")
    create_payload = {
        "title": "Uncleared construction rubble near School Gate 2",
        "category": "construction debris",
        "ward": "Ward 1",
        "latitude": 28.6150,
        "longitude": 77.2100,
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

    # 5. Municipal worker resolves the complaint
    after_img = create_dummy_image_bytes("After Cleaned Walkway")
    resolve_files = {"photo": ("after_school.jpg", after_img, "image/jpeg")}
    resolve_data = {
        "latitude": "28.6151",  # ~11m distance away (within 50m limit)
        "longitude": "77.2100"
    }
    
    res = client.post(f"/api/complaints/{c_id}/resolve", data=resolve_data, files=resolve_files)
    assert res.status_code == 200, f"Resolve complaint failed: {res.text}"
    resolution = res.json()
    assert resolution["verdict"] in ["VERIFIED", "SUSPICIOUS", "LIKELY FAKE"]
    assert len(resolution["reasons"]) > 0, "Reasons list should not be empty"
    print(f"[PASS] POST /api/complaints/{c_id}/resolve (Verdict: {resolution['verdict']}, Score: {resolution['score']}, Reasons: {len(resolution['reasons'])})")

    # Verify complaint status updated to RESOLVED
    res = client.get(f"/api/complaints/{c_id}")
    assert res.json()["status"] == "RESOLVED"
    print(f"[PASS] Complaint status updated to RESOLVED")

    # 6. Citizen reopens the complaint
    reopen_img = create_dummy_image_bytes("Reopen New Photo")
    reopen_files = {"photo": ("reopen_school.jpg", reopen_img, "image/jpeg")}
    reopen_data = {"reason": "Worker only cleared half the debris"}

    res = client.post(f"/api/complaints/{c_id}/reopen", data=reopen_data, files=reopen_files)
    assert res.status_code == 200, f"Reopen complaint failed: {res.text}"
    reopened_c = res.json()
    assert reopened_c["status"] == "REOPENED"
    assert reopened_c["reopen_count"] == 1
    print(f"[PASS] POST /api/complaints/{c_id}/reopen (Status: REOPENED, Reopen Count: 1)")

    # 7. Dashboard endpoints
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_complaints"] >= 6
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
    assert len(map_points) >= 6
    print(f"[PASS] GET /api/dashboard/map-data ({len(map_points)} map points)")

    # 8. Human verification endpoints
    res = client.get("/api/verification/flagged")
    assert res.status_code == 200
    flagged = res.json()
    print(f"[PASS] GET /api/verification/flagged ({len(flagged)} flagged items)")

    if len(flagged) > 0:
        target_res_id = flagged[0]["id"]
        res = client.post(f"/api/verification/{target_res_id}/review", json={"decision": "Confirmed fake"})
        assert res.status_code == 200
        assert res.json()["human_review_status"] == "Confirmed fake"
        print(f"[PASS] POST /api/verification/{target_res_id}/review -> Confirmed fake")

    print("\n=== ALL BACKEND INTEGRATION TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_full_backend_workflow()
