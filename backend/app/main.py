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

@app.get("/")
def root():
    return {
        "app": "Resolved, Allegedly API",
        "status": "running",
        "docs_url": "/docs"
    }
