import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path so app modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from reset_demo import reset_demo_database

client = TestClient(app)
upload_dir = PROJECT_ROOT / "data" / "demo" / "upload"

def resolve_via_api(complaint_id: int, filename: str):
    file_path = upload_dir / filename
    with open(file_path, "rb") as f:
        res = client.post(
            f"/api/complaints/{complaint_id}/resolve",
            files={"photo": (filename, f, "image/jpeg")}
        )
    assert res.status_code == 200, f"Failed to resolve complaint #{complaint_id} with {filename}: {res.text}"
    return res.json()

def reopen_via_api(complaint_id: int, filename: str, reason: str = "Reopening complaint for demo verification"):
    file_path = upload_dir / filename
    with open(file_path, "rb") as f:
        res = client.post(
            f"/api/complaints/{complaint_id}/reopen",
            data={"reason": reason},
            files={"photo": (filename, f, "image/jpeg")}
        )
    assert res.status_code == 200, f"Failed to reopen complaint #{complaint_id}: {res.text}"
    return res.json()

def review_via_api(resolution_id: int, decision: str = "Confirmed fake"):
    res = client.post(
        f"/api/verification/{resolution_id}/review",
        json={"decision": decision}
    )
    assert res.status_code == 200, f"Failed to review resolution #{resolution_id}: {res.text}"
    return res.json()

def run_demo_dry_run():
    print("=== STARTING DEMO DRY RUN SEQUENCE ===")
    
    # Step A: Rebuild database to initial demo state
    print("\nA) Rebuilding demo database to clean initial state...")
    reset_demo_database()

    # Step B: Perform exact demo sequence through API endpoints
    print("\nB) Executing Live Demo Sequence through FastAPI Endpoints...")

    dry_run_records = []

    # 1. Resolve #1 with genuine_after_1.jpg
    res1 = resolve_via_api(1, "genuine_after_1.jpg")
    dry_run_records.append({
        "step": "1",
        "complaint": "Complaint #1 (Ameerpet)",
        "file": "genuine_after_1.jpg",
        "score": res1["score"],
        "verdict": res1["verdict"],
        "reasons": res1["reasons"]
    })

    # 2. Resolve #4 with fake_reused_dirty_4.jpg
    res2 = resolve_via_api(4, "fake_reused_dirty_4.jpg")
    dry_run_records.append({
        "step": "2",
        "complaint": "Complaint #4 (Secunderabad)",
        "file": "fake_reused_dirty_4.jpg",
        "score": res2["score"],
        "verdict": res2["verdict"],
        "reasons": res2["reasons"]
    })

    # 3. Reopen #4 with a photo that still shows the litter (status becomes REOPENED, SLA clock restarts)
    reopen_res = reopen_via_api(4, "fake_reused_dirty_4.jpg", reason="Issue was not actually cleaned initially")
    dry_run_records.append({
        "step": "3",
        "complaint": "Complaint #4 (Reopened by citizen)",
        "file": "fake_reused_dirty_4.jpg",
        "score": "N/A",
        "verdict": reopen_res["status"],
        "reasons": [
            f"Status updated to {reopen_res['status']} (Reopen count: {reopen_res['reopen_count']})",
            f"Reopened At: {reopen_res['reopened_at']}",
            "SLA Clock restarted based on reopened_at timestamp"
        ]
    })

    # 4. Resolve #6 with fake_ai_clean_for_6.jpg, then review it as "Confirmed fake"
    res6 = resolve_via_api(6, "fake_ai_clean_for_6.jpg")
    review_res = review_via_api(res6["id"], decision="Confirmed fake")
    dry_run_records.append({
        "step": "4",
        "complaint": "Complaint #6 (Mehdipatnam -> Review: Confirmed fake)",
        "file": "fake_ai_clean_for_6.jpg",
        "score": res6["score"],
        "verdict": res6["verdict"],
        "reasons": res6["reasons"]
    })

    # 5. Resolve #5 with fake_wrong_place_for_1.jpg
    res5 = resolve_via_api(5, "fake_wrong_place_for_1.jpg")
    dry_run_records.append({
        "step": "5",
        "complaint": "Complaint #5 (Dilsukhnagar)",
        "file": "fake_wrong_place_for_1.jpg",
        "score": res5["score"],
        "verdict": res5["verdict"],
        "reasons": res5["reasons"]
    })

    # Step C: Print Table
    print("\n==========================================================================================================")
    print("                                      DEMO DRY RUN RESULTS TABLE                                          ")
    print("==========================================================================================================")
    header = f"{'Step':<5} | {'Complaint':<45} | {'Upload File':<26} | {'Score':<5} | {'Verdict':<12}"
    print(header)
    print("-" * len(header))

    for rec in dry_run_records:
        print(f"{rec['step']:<5} | {rec['complaint']:<45} | {rec['file']:<26} | {rec['score']:<5} | {rec['verdict']:<12}")
        print("      Reasons:")
        for r in rec["reasons"]:
            print(f"       • {r}")
        print("-" * len(header))

    # Step D: Reset database again so it is 100% clean for the live demo
    print("\nD) Resetting database back to clean initial state for live demo...")
    reset_demo_database()

    print("\n=== DEMO DRY RUN COMPLETED SUCCESSFULLY & DB CLEANED ===")

    return dry_run_records

if __name__ == "__main__":
    run_demo_dry_run()
