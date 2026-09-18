=== READY-TO-UPLOAD DEMO FILES FOR MUNICIPAL WORKER RESOLUTION & REOPEN ===

DEMO FLOW & ACTUAL DRY RUN RESULTS:

1. genuine_after_1.jpg -> Upload to Complaint #1 (Ameerpet - garbage dump)
   Action: Resolve Complaint #1
   Actual Verdict: VERIFIED (Score: 100)
   Details: Clean after-photo (CLIP problem reduced 42.8% -> 2.4%), EXIF GPS within 10.7m, valid timestamp.

2. fake_reused_dirty_2.jpg -> Upload to Complaint #2 (Kukatpally - blocked drain)
   Action: Resolve Complaint #2
   Actual Verdict: LIKELY FAKE (Score: 30)
   Details: Re-uploaded dirty before photo (CLIP problem not reduced 81.8% -> 81.8%, -50 pts), timestamp earlier than complaint creation time (-20 pts).

3. genuine_after_2.jpg -> Upload to Complaint #2 (Kukatpally - blocked drain)
   Action: Reopen Complaint #2
   Actual Status: REOPENED (Reopen Count: 1)
   Details: Citizen reopens complaint with new photo. Status changes to REOPENED and SLA clock restarts using reopened_at timestamp.

4. fake_ai_clean_for_6.jpg -> Upload to Complaint #6 (Mehdipatnam - garbage dump)
   Action: Resolve Complaint #6, then Review in Human Verification panel
   Actual Verdict: SUSPICIOUS (Score: 40) -> Flagged for Review -> Human Admin marks "Confirmed fake".
   Details: Missing camera/EXIF metadata (-10 pts), missing GPS location (-30 pts), missing timestamp (-20 pts).

5. fake_wrong_place_for_1.jpg -> Upload to Complaint #5 (Dilsukhnagar - garbage dump)
   Action: Resolve Complaint #5
   Actual Verdict: SUSPICIOUS (Score: 70)
   Details: Photo location in Madhapur >16 km away (>50m limit, -30 pts).

--- ADDITIONAL READY-TO-UPLOAD TEST FILES ---
6. genuine_after_3.jpg -> Upload to Complaint #3 (Madhapur - construction debris)
   Expected Verdict: VERIFIED (Score >= 75)
7. genuine_after_4.jpg -> Upload to Complaint #4 (Secunderabad - unswept street)
   Expected Verdict: VERIFIED (Score >= 75)
8. genuine_after_5.jpg -> Upload to Complaint #5 (Dilsukhnagar - garbage dump)
   Expected Verdict: VERIFIED (Score >= 75)
9. genuine_after_6.jpg -> Upload to Complaint #6 (Mehdipatnam - garbage dump)
   Expected Verdict: VERIFIED (Score >= 75)
