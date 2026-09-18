=== CLEANPROOF LIVE DEMO: WHAT TO UPLOAD, IN THIS ORDER ===
Run scripts/reset_demo.py right before the demo. It regenerates these photos
with fresh timestamps, so they only match the complaints from that reset.
Upload on the Worker page (Resolve button on the complaint card).

STEP 1  Genuine clean-up
  Upload genuine_after_1.jpg to complaint #1 (Ameerpet)
  Expected: 100/100 VERIFIED (all 5 checks pass)

STEP 2  Dirty photo re-uploaded as "proof"
  Upload fake_reused_dirty_2.jpg to complaint #2 (Kukatpally)
  Expected: 20/100 LIKELY FAKE
  (CLIP: problem not reduced -50, photo older than the complaint -30)

STEP 3  Citizen reopens
  Track page, complaint #2: Reopen with any photo
  Expected: status REOPENED, deadline restarts

STEP 4  AI-generated "clean" photo (no camera data)
  Upload fake_ai_clean_for_6.jpg to complaint #6 (Mehdipatnam)
  Expected: 30/100 LIKELY FAKE (no GPS -30, no timestamp -30, no EXIF -10)
  Then on the Review page click "Confirmed fake"

STEP 5  Real clean photo from a different place
  Upload fake_wrong_place_for_1.jpg to complaint #5 (Dilsukhnagar)
  Expected: 70/100 SUSPICIOUS (photo taken km away from the complaint -30)

STEP 6  Dashboard
  Show the hotspots: Dilsukhnagar (fake closures) and Kukatpally (missed deadlines)

Other files: genuine_after_2..6.jpg are genuine clean-ups for complaints #2..#6.
Note: fake_wrong_place_for_1.jpg is the same photo as genuine_after_3.jpg,
so whichever of the two is uploaded second is also flagged as a duplicate (-30).
