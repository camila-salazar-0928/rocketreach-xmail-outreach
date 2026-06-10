import logging

from outreach_app.db.base import Base
from outreach_app.db.session import engine
from outreach_app.models import Campaign, CampaignRecipient, Contact, EmailEvent  # noqa: F401


logger = logging.getLogger(__name__)


def create_database_tables() -> None:
    logger.info("Creating database tables")

    Base.metadata.create_all(bind=engine)

    logger.info(
        "Database tables created | tables=%s",
        list(Base.metadata.tables.keys()),
    )