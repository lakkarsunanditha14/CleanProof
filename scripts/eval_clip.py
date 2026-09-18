import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.clip_service import compare_photos_with_clip, CLIP_THRESHOLD, CLIP_RATIO

def run_clip_pair_evaluation():
    demo_dir = PROJECT_ROOT / "data" / "demo"
    before_dir = demo_dir / "before"
    after_dir = demo_dir / "after"
    fraud_file = demo_dir / "fraud" / "fraud_ai_clean.png"

    # Category mapping per pair index 1..6
    pair_category_map = {
        1: "garbage dump",
        2: "blocked drain",
        3: "construction debris",
        4: "unswept street",
        5: "garbage dump",
        6: "garbage dump",
    }

    pairs = []

    # 1. Test before_i vs after_i (i=1..6) -> expected: Clean (issue_present = False)
    for i in range(1, 7):
        ext = ".jpg" if i == 1 else ".png"
        b_path = before_dir / f"before_{i}{ext}"
        a_path = after_dir / f"after_{i}{ext}"
        cat = pair_category_map[i]
        label = f"before_{i} vs after_{i}"
        pairs.append((b_path, a_path, cat, label, False))

    # 2. Test before_i vs before_i (same dirty photo re-uploaded, i=1..6) -> expected: Issue (issue_present = True)
    for i in range(1, 7):
        ext = ".jpg" if i == 1 else ".png"
        b_path = before_dir / f"before_{i}{ext}"
        cat = pair_category_map[i]
        label = f"before_{i} vs before_{i}"
        pairs.append((b_path, b_path, cat, label, True))

    # 3. Test before_6 vs fraud_ai_clean.png -> expected: Clean (issue_present = False)
    b6_path = before_dir / "before_6.png"
    if b6_path.exists() and fraud_file.exists():
        pairs.append((b6_path, fraud_file, "garbage dump", "before_6 vs fraud_ai_clean", False))

    print(f"Loaded {len(pairs)} image pair tests from data/demo for photo-comparison CLIP evaluation.\n")

    results = []
    correct_count = 0

    for b_path, a_path, cat, pair_name, expected_issue in pairs:
        if not b_path.exists() or not a_path.exists():
            print(f"Skipping missing pair: {pair_name}")
            continue

        res = compare_photos_with_clip(
            before_image_path=str(b_path),
            after_image_path=str(a_path),
            category=cat
        )

        before_pct = res.get("before_percent", 0.0)
        after_pct = res.get("after_percent", 0.0)
        predicted_issue = res.get("issue_present", False)
        is_correct = (predicted_issue == expected_issue)

        if is_correct:
            correct_count += 1

        results.append({
            "pair": pair_name,
            "category": cat,
            "before_pct": before_pct,
            "after_pct": after_pct,
            "expected": "Issue (True)" if expected_issue else "Clean (False)",
            "predicted": "Issue (True)" if predicted_issue else "Clean (False)",
            "correct": is_correct
        })

    # Print Evaluation Table
    print(f"=== CLIP PHOTO-COMPARISON EVALUATION TABLE (Threshold={CLIP_THRESHOLD}, Ratio={CLIP_RATIO}) ===")
    header = f"{'Pair Name':<26} | {'Category':<20} | {'Before %':<9} | {'After %':<8} | {'Expected':<13} | {'Predicted':<13} | {'Correct':<7}"
    print(header)
    print("-" * len(header))

    for r in results:
        correct_str = "YES" if r["correct"] else "NO"
        print(f"{r['pair']:<26} | {r['category']:<20} | {r['before_pct']:<9.1f} | {r['after_pct']:<8.1f} | {r['expected']:<13} | {r['predicted']:<13} | {correct_str:<7}")

    total_count = len(results)
    accuracy = (correct_count / total_count * 100.0) if total_count > 0 else 0.0

    print("-" * len(header))
    print(f"Overall Accuracy: {correct_count}/{total_count} ({accuracy:.2f}%)\n")

if __name__ == "__main__":
    run_clip_pair_evaluation()
