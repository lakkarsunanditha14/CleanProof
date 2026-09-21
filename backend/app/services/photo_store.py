"""Keeps photos in the database when the server has no lasting disk (free cloud hosting).

With STORE_PHOTOS_IN_DB=1, every complaint, closure and reopen photo is copied into the
`stored_photos` table in the same transaction that saves its record, and `local_path` brings a
photo back to this server's disk when it is needed. Locally (the default) photos simply stay in
data/images and nothing here does anything.
"""
import os
from pathlib import Path

from sqlalchemy import Column, LargeBinary, String, event, select

from app.config import IMAGES_DIR
from app.database import Base, SessionLocal
from app.models import Complaint, ReopenLog, Resolution

ENABLED = os.getenv("STORE_PHOTOS_IN_DB") == "1"


class StoredPhoto(Base):
    __tablename__ = "stored_photos"

    name = Column(String(255), primary_key=True)  # file name, as used in /static/images/<name>
    data = Column(LargeBinary, nullable=False)


def _keep(path_attr: str):
    def listener(mapper, connection, target):
        path = Path(getattr(target, path_attr) or "")
        if ENABLED and path.name and (IMAGES_DIR / path.name).is_file():
            table = StoredPhoto.__table__
            if connection.execute(select(table.c.name).where(table.c.name == path.name)).first() is None:
                connection.execute(table.insert().values(name=path.name, data=(IMAGES_DIR / path.name).read_bytes()))
    return listener


for model, attr in ((Complaint, "before_image_path"), (Resolution, "after_image_path"), (ReopenLog, "reopen_image_path")):
    event.listen(model, "after_insert", _keep(attr))
    event.listen(model, "after_update", _keep(attr))


def local_path(path: str) -> str:
    """Path of this photo on this server's disk, fetched from the database if it is not here yet."""
    local = IMAGES_DIR / Path(path or "").name
    if ENABLED and local.name and not local.is_file():
        with SessionLocal() as db:
            photo = db.get(StoredPhoto, local.name)
        if photo is not None:
            tmp = local.with_suffix(local.suffix + ".part")
            tmp.write_bytes(photo.data)
            tmp.replace(local)
    return str(local) if local.is_file() else path
