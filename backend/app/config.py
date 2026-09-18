import os
from pathlib import Path
from dotenv import load_dotenv

# Compute project directories relative to this file
backend_dir = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]

env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

CLIP_THRESHOLD = float(os.getenv("CLIP_THRESHOLD", "0.5"))
CLIP_RATIO = float(os.getenv("CLIP_RATIO", "0.75"))

# Absolute path to single SQLite database file at project root
DEFAULT_DB_FILE = (PROJECT_ROOT / "resolved_allegedly.db").resolve()
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"

env_db_url = os.getenv("DATABASE_URL")
if not env_db_url or env_db_url.startswith("sqlite:///./"):
    DATABASE_URL = DEFAULT_DATABASE_URL
else:
    DATABASE_URL = env_db_url

# Image directory path (absolute path to data/images)
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", PROJECT_ROOT / "data" / "images")).resolve()
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

SLA_HOURS = {
    "garbage dump": 12,
    "unswept street": 24,
    "construction debris": 72,
    "blocked drain": 48
}

VALID_CATEGORIES = list(SLA_HOURS.keys())
VALID_WARDS = [
    "Ameerpet",
    "Kukatpally",
    "Madhapur",
    "Secunderabad",
    "Dilsukhnagar",
    "Mehdipatnam",
    "Begumpet",
    "LB Nagar"
]
