from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_kwargs: dict = {"future": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = connect_args
    if ":memory:" in settings.database_url:
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
