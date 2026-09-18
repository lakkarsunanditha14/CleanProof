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

# Image directory path (absolute path to data/images).
# A relative IMAGES_DIR in .env is resolved against the backend folder, never the current folder.
_images_dir = Path(os.getenv("IMAGES_DIR", PROJECT_ROOT / "data" / "images"))
if not _images_dir.is_absolute():
    _images_dir = backend_dir / _images_dir
IMAGES_DIR = _images_dir.resolve()
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

SLA_HOURS = {
    "garbage dump": 12,
    "unswept street": 24,
    "construction debris": 72,
    "blocked drain": 48
}

VALID_CATEGORIES = list(SLA_HOURS.keys())

# A worker closing a complaint after its deadline must pick one of these.
DELAY_REASONS = [
    "Vehicle or staff shortage",
    "Heavy rain or waterlogging",
    "Access blocked (traffic, parked vehicles, event)",
    "Needed special equipment (JCB, tractor, suction machine)",
    "Waste much larger than reported",
    "Other",
]
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
