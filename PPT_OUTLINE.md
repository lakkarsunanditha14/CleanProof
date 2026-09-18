# CleanProof: Pitch Presentation Outline

**Slide 1: Title Slide**
*   **Title:** CleanProof: Every 'resolved' complaint, verified.
*   **Tagline:** Safeguarding civic integrity and SLA adherence.
*   **Event:** PS-D04 "Resolved, Allegedly" (24h Hackathon).

**Slide 2: The Problem**
*   **Current State:** Citizens report civic issues (garbage, blocked drains, debris), but workers sometimes close these complaints prematurely or fraudulently.
*   **The Loophole:** Re-using old photos, uploading web images, or submitting pictures from entirely different locations to falsely meet Service Level Agreements (SLAs).
*   **Impact:** Broken trust between citizens and municipalities, wasted resources, and unresolved civic hazards.

**Slide 3: Our Solution (CleanProof)**
*   **Concept:** An automated verification engine that validates "after" photos submitted by municipal workers.
*   **Mechanism:** Uses a localized scoring system (0-100) combining AI vision and forensic metadata checks.
*   **Outcome:** Automatically flags suspicious (40-74) and likely fake (<40) closures for human review, while automatically verifying genuine resolutions (>=75).

**Slide 4: How it Works (The Workflow)**
*   **Step 1 (Report):** Citizen logs a complaint with a geo-tagged "before" photo.
*   **Step 2 (Resolve):** Worker completes the job and captures an "after" photo.
*   **Step 3 (Verify):** CleanProof runs automated checks to score the submission.
*   **Step 4 (Review):** Human supervisors audit flagged closures through a dedicated dashboard. (Confirmed fakes reopen the complaint).

**Slide 5: The 5 Forensic Checks**
*   **1. AI Vision (-50 pts):** Local CLIP model compares the before/after photos to ensure the issue is actually reduced.
*   **2. Location (-30 pts):** GPS check ensures the resolution photo is within 50 meters of the original complaint.
*   **3. Time (-30 pts):** Ensures the photo timestamp is *after* the complaint was created or reopened.
*   **4. Duplicate Photo (-30 pts):** Perceptual hashing prevents re-uploading older closure photos.
*   **5. Camera Data (-10 pts):** Rejects photos missing original camera EXIF metadata (often web downloads or screenshots).

**Slide 6: Live Camera and Photo Evidence**
*   **Secure Capture:** In-app custom live camera enforces real-time capture (no gallery uploads).
*   **Evidence Stamping:** Burns server time, ward, and distance directly into the image. Street name is only included if GPS accuracy is <= 30m.
*   **Quality Gates:** Automatically rejects blurry or pitch-dark photos with immediate retake prompts.
*   **Evidence Panel:** A dedicated UI for supervisors to view extracted metadata, cropped comparisons, and check failures.

**Slide 7: Tech Stack**
*   **Frontend:** React + Vite, Tailwind CSS, Recharts, React-Leaflet (Fully responsive, mobile-first).
*   **Backend:** FastAPI, SQLite (SQLAlchemy) single-file database.
*   **AI/Forensics:** Local HuggingFace CLIP (`openai/clip-vit-base-patch32`), perceptual hashing, EXIF parsing.
*   **Architecture:** 100% offline-capable (except map tiles), zero external API keys required.

**Slide 8: Test Results & Accuracy**
*   **Demo Sequence:** 12/13 correct classifications on structured demo pairs.
*   **Robustness Testing:** 95% accuracy on a hard dataset of challenging edge cases.
*   **Real-World Data (TACO Dataset):** 100% success rate in catching re-used dirty photos posing as clean resolutions.

**Slide 9: Responsible Design**
*   **Human-in-the-Loop:** The AI never automatically penalizes a worker or reopens a complaint. It only flags for human review.
*   **Fact-Based Only:** No hallucinated data or guessed place names. We only display measured, verifiable facts.
*   **Privacy & Scope:** Purely synthetic data used for the demo. No impersonation of official bodies (Swachhata/GHMC).

**Slide 10: Future Scope**
*   **Expansion:** Add support for more complex civic categories (e.g., pothole repairs, broken streetlights).
*   **Edge Deployment:** Move the lightweight CLIP model directly to the worker's mobile device for offline, instant verification.
*   **Analytics:** Deeper predictive insights into ward-level fraud trends and SLA bottlenecks.
