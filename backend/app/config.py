import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory if present
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

CLIP_THRESHOLD = float(os.getenv("CLIP_THRESHOLD", "0.5"))
CLIP_RATIO = float(os.getenv("CLIP_RATIO", "0.75"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./resolved_allegedly.db")

# Image directory path (absolute path to data/images)
PROJECT_ROOT = backend_dir.parent
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", PROJECT_ROOT / "data" / "images")).resolve()
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

SLA_HOURS = {
    "garbage dump": 12,
    "unswept street": 24,
    "construction debris": 72,
    "blocked drain": 48
}

VALID_CATEGORIES = list(SLA_HOURS.keys())
VALID_WARDS = ["Ward 1", "Ward 2", "Ward 3", "Ward 4", "Ward 5"]
