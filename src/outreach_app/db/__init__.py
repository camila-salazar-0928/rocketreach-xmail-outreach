import logging

from outreach_app.db.base import Base
from outreach_app.db.session import engine


logger = logging.getLogger(__name__)


def create_database_tables() -> None:
    from outreach_app.models import (  # noqa: F401
        Campaign,
        CampaignRecipient,
        Contact,
        EmailEvent,
    )

    logger.info("Creating database tables")

    Base.metadata.create_all(bind=engine)

    logger.info(
        "Database tables created | tables=%s",
        list(Base.metadata.tables.keys()),
    )
