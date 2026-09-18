=== READY-TO-UPLOAD DEMO FILES FOR MUNICIPAL WORKER RESOLUTION ===

1. genuine_after_1.jpg -> Upload to Complaint #1 (Ameerpet - garbage dump)
   Expected Verdict: VERIFIED (Score >= 75)
   Details: Clean after-photo, EXIF GPS within 8m, valid IST timestamp.

2. genuine_after_2.jpg -> Upload to Complaint #2 (Kukatpally - blocked drain)
   Expected Verdict: VERIFIED (Score >= 75)
   Details: Clean after-photo, EXIF GPS within 8m, valid IST timestamp.

3. genuine_after_3.jpg -> Upload to Complaint #3 (Madhapur - construction debris)
   Expected Verdict: VERIFIED (Score >= 75)
   Details: Clean after-photo, EXIF GPS within 8m, valid IST timestamp.

4. genuine_after_4.jpg -> Upload to Complaint #4 (Secunderabad - unswept street)
   Expected Verdict: VERIFIED (Score >= 75)
   Details: Clean after-photo, EXIF GPS within 8m, valid IST timestamp.

5. genuine_after_5.jpg -> Upload to Complaint #5 (Dilsukhnagar - garbage dump)
   Expected Verdict: VERIFIED (Score >= 75)
   Details: Clean after-photo, EXIF GPS within 8m, valid IST timestamp.

6. genuine_after_6.jpg -> Upload to Complaint #6 (Mehdipatnam - garbage dump, Near Deadline)
   Expected Verdict: VERIFIED (Score >= 75)
   Details: Clean after-photo, EXIF GPS within 8m, valid IST timestamp.

7. fake_reused_dirty_2.jpg -> Upload to Complaint #2 (Kukatpally)
   Expected Verdict: LIKELY FAKE / SUSPICIOUS (Score < 40)
   Details: Re-uploaded dirty before photo (-50 pts), duplicate hash (-30 pts), timestamp earlier than complaint (-20 pts).

8. fake_wrong_place_for_1.jpg -> Upload to Complaint #1 (Ameerpet)
   Expected Verdict: SUSPICIOUS / LIKELY FAKE
   Details: Photo location in Madhapur >5 km away (location penalty -30 pts).

9. fake_ai_clean_for_6.jpg -> Upload to Complaint #6 (Mehdipatnam)
   Expected Verdict: LIKELY FAKE (Score < 40)
   Details: Missing EXIF metadata (-10 pts), missing GPS (-30 pts), missing timestamp (-20 pts).
