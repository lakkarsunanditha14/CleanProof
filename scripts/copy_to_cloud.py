"""Copy this laptop's complaints, closures, reopens and their photos into the cloud database.

Run once after setting up the cloud database (the cloud database must be empty):
    set CLOUD_DATABASE_URL=postgresql://...   (typed in the terminal, never committed)
    backend\\venv\\Scripts\\python.exe scripts\\copy_to_cloud.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cloud_url = os.environ.get("CLOUD_DATABASE_URL")
if not cloud_url:
    sys.exit("Set CLOUD_DATABASE_URL first.")

# Point the app at the cloud database, keep photos in it, read photo files from this laptop
local_db = f"sqlite:///{(ROOT / 'resolved_allegedly.db').as_posix()}"
os.environ["DATABASE_URL"] = cloud_url
os.environ["STORE_PHOTOS_IN_DB"] = "1"
os.environ["IMAGES_DIR"] = str(ROOT / "data" / "images")
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, make_transient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Complaint, ReopenLog, Resolution  # noqa: E402
from app.services import photo_store  # noqa: E402,F401  (registers the photo copying)

Base.metadata.create_all(bind=engine)
with SessionLocal() as cloud, Session(create_engine(local_db)) as local:
    if cloud.query(Complaint).count():
        sys.exit("The cloud database already has complaints; nothing copied.")
    for model in (Complaint, Resolution, ReopenLog):
        rows = local.query(model).all()
        for row in rows:
            local.expunge(row)
            make_transient(row)
            cloud.add(row)
        cloud.flush()
        print(f"{model.__tablename__}: {len(rows)} copied")
    if cloud.bind.dialect.name == "postgresql":  # continue numbering after the copied ids
        for table in ("complaints", "resolutions", "reopen_logs"):
            cloud.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                               f"COALESCE((SELECT MAX(id) FROM {table}), 1))"))
    cloud.commit()
    print(f"photos stored: {cloud.query(photo_store.StoredPhoto).count()}")
