import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from outreach_app.core.config import get_settings


logger = logging.getLogger(__name__)

settings = get_settings()


def mask_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        logger.warning("Could not mask database URL")
        return "unavailable"


def get_engine() -> Engine:
    connect_args = {}

    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    logger.info(
        "Creating database engine | database_url=%s",
        mask_database_url(settings.database_url),
    )

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = get_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        logger.debug("Database session opened")
        yield db
    except Exception:
        logger.exception("Database session failed")
        raise
    finally:
        db.close()
        logger.debug("Database session closed")