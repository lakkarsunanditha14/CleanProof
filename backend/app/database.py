from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

url = make_url(DATABASE_URL)
if url.drivername == "postgresql":
    # Cloud Postgres (Neon) through pg8000, a small pure-Python driver; SSL is always on
    url = url.set(drivername="postgresql+pg8000", query={})
    connect_args = {"ssl_context": True}
else:
    connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    url,
    connect_args=connect_args,
    pool_pre_ping=True,  # cloud databases close idle connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
