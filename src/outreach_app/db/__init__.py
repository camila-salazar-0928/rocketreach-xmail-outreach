import logging

from outreach_app.db.base import Base
from outreach_app.db.session import engine


logger = logging.getLogger(__name__)


def create_database_tables() -> None:
    from outreach_app.models.campaign import Campaign  # noqa: F401
    from outreach_app.models.campaign_recipient import CampaignRecipient  # noqa: F401
    from outreach_app.models.contact import Contact  # noqa: F401
    from outreach_app.models.email_event import EmailEvent  # noqa: F401

    logger.info("Creating database tables")

    Base.metadata.create_all(bind=engine)

    logger.info(
        "Database tables created | tables=%s",
        list(Base.metadata.tables.keys()),
    )
