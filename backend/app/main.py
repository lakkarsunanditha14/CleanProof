import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.config import IMAGES_DIR
from app.routers import complaints, dashboard, verification

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resolved, Allegedly API",
    description="Backend service for Civic Complaint Verification, SLA Tracking, and Fraud Detection",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure images directory exists
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files directory to serve uploaded before/after photos
app.mount("/static/images", StaticFiles(directory=str(IMAGES_DIR)), name="static_images")
app.mount("/data/images", StaticFiles(directory=str(IMAGES_DIR)), name="data_images")

# Register routers
app.include_router(complaints.router)
app.include_router(dashboard.router)
app.include_router(verification.router)

# Cloud mode (e.g. Hugging Face Spaces): FRONTEND_DIST points to the built frontend, and this one
# server serves the whole app at a single address. Locally it is unset and Vite serves the frontend.
FRONTEND_DIST = os.getenv("FRONTEND_DIST")

if FRONTEND_DIST and (Path(FRONTEND_DIST) / "index.html").exists():
    from fastapi.responses import FileResponse

    dist = Path(FRONTEND_DIST).resolve()
    app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="frontend_assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        # Real files (favicon etc.) as-is; every page route (/track, /worker, ...) gets the app shell
        file = (dist / path).resolve()
        if path and file.is_file() and dist in file.parents:
            return FileResponse(file)
        return FileResponse(dist / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "app": "Resolved, Allegedly API",
            "status": "running",
            "docs_url": "/docs"
        }
