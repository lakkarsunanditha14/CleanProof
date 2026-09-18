# Project: Resolved, Allegedly (Hackathon PS-D04, 24 hours)

## Problem
Civic complaints (garbage, drains, debris) get marked "resolved" without real
verification. We build a system that tracks complaints, verifies resolution
photos with AI, detects fraud, and shows SLA adherence + hotspots on a dashboard.

## Features (build ONLY these)
1. Complaint submission: photo upload, category, GPS (lat/lng), timestamp, ward
2. SLA clock per category: garbage dump 12h, unswept street 24h, construction debris 72h,
   blocked drain 48h. Status: On time / Near deadline / Breached
3. Resolution + verification: when "after" photo is uploaded, run checks:
   - AI vision: local CLIP model zero-shot check (is the issue still present? yes/no + confidence)
   - Same location: GPS distance between before/after < 50m (-30 pts if > 50m or missing GPS)
   - Timestamp: after-photo time must be later than complaint time (-20 pts)
   - Duplicate: perceptual hash (imagehash) vs all previous after-photos (-30 pts)
   - Metadata: missing EXIF = suspicious (-10 pts)
   Output: score 0-100 + verdict: VERIFIED / SUSPICIOUS / LIKELY FAKE + reasons list
4. Citizen reopen: upload new photo to reopen a closed complaint
5. Dashboard: Leaflet map with markers + heatmap, SLA adherence % by ward and category,
   false-closure count per ward, list of flagged complaints

## Tech stack (do NOT change)
- Frontend: React + Vite + Tailwind CSS + Leaflet (react-leaflet) + Recharts
- Backend: Python FastAPI + SQLite (SQLAlchemy)
- AI: Local CLIP Vision Model (openai/clip-vit-base-patch32, no API key required)
- Image libs: Pillow, imagehash, piexif, transformers, torch
- Folders: /backend, /frontend, /data (images), /scripts

## Rules
- Human review only: never auto-penalise, only flag
- All data is synthetic, created by the team. No scraping of real govt systems
- Do not impersonate the official Swachhata app; use our own name and branding
- Clean, modern, professional UI (not childish). Mobile-friendly complaint form
- Keep code simple and readable. Do not add features not listed here
- Never hardcode API keys or credentials
