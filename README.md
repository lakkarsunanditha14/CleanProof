---
title: CleanProof
emoji: 🧹
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Verifies that 'resolved' civic complaints were really fixed
---

# CleanProof

**Every 'resolved' complaint, verified.** Hackathon prototype for PS-D04 "Resolved, Allegedly"
(Digital Public Services track).

Citizens report civic issues (garbage, blocked drains, debris, unswept streets) with a photo.
When a worker closes a complaint, CleanProof checks the after photo before accepting it:

1. **AI vision (CLIP, runs locally):** is the problem visibly reduced compared with the citizen's photo?
2. **Location:** was the photo taken within 50 m of the complaint?
3. **Time:** was it taken after the complaint (or reopen)?
4. **Duplicate:** has this photo been used for another closure?
5. **Camera data:** does it carry real camera metadata?

Workers take the after photo with a **live in-app camera** (no gallery), so old photos cannot be
submitted. Suspicious closures go to a **human reviewer**, citizens can **reopen**, late closures
need a **delay reason**, and a **dashboard** shows deadline performance and suspected fake closures
by ward.

All data is synthetic. This is a prototype, not an official government service.

## Run locally

Double-click `START_DEMO.bat`, or:

```bash
cd backend; .\venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```
```bash
cd frontend; npm run dev
```

Reset demo data: `backend\venv\Scripts\python.exe scripts\reset_demo.py`
(add `--with-history` for 194 synthetic past complaints).

**Stack:** React + Vite + Tailwind + Leaflet + Recharts, FastAPI + SQLite, CLIP
(`openai/clip-vit-base-patch32`) via PyTorch, Pillow, imagehash, piexif.
