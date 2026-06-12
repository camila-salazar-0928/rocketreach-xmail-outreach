import logging

from outreach_app.db.base import Base
from outreach_app.db.session import engine
from sqlalchemy import inspect, text


logger = logging.getLogger(__name__)


def create_database_tables() -> None:
    from outreach_app.models.campaign import Campaign  # noqa: F401
    from outreach_app.models.campaign_recipient import CampaignRecipient  # noqa: F401
    from outreach_app.models.contact import Contact  # noqa: F401
    from outreach_app.models.email_event import EmailEvent  # noqa: F401

    logger.info("Creating database tables")

    Base.metadata.create_all(bind=engine)
    ensure_contact_optional_columns()
    logger.info(
        "Database tables created | tables=%s",
        list(Base.metadata.tables.keys()),
    )


def ensure_contact_optional_columns() -> None:
    """Add optional columns to contacts table when running local SQLite development."""
    logger.info("Checking optional contact columns")

    inspector = inspect(engine)

    if "contacts" not in inspector.get_table_names():
        logger.info("Contacts table does not exist yet. Skipping optional column check.")
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("contacts")
    }

    columns_to_add = {
        "industry": "VARCHAR(200)",
        "country": "VARCHAR(120)",
        "region": "VARCHAR(120)",
        "city": "VARCHAR(120)",
        "location": "VARCHAR(250)",
        "linkedin_url": "VARCHAR(500)",
        "seniority": "VARCHAR(120)",
        "department": "VARCHAR(120)",
        "years_of_experience": "VARCHAR(50)",
        "employer_domain": "VARCHAR(250)",
        "employer_website": "VARCHAR(500)",
        "employer_linkedin": "VARCHAR(500)",
        "email_lookup_status": "VARCHAR(120)",
        "skills": "TEXT",
    }
    with engine.begin() as connection:
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                logger.info(
                    "Adding missing contact column | column=%s | type=%s",
                    column_name,
                    column_type,
                )

                connection.execute(
                    text(
                        f"ALTER TABLE contacts ADD COLUMN {column_name} {column_type}"
                    )
                )

    logger.info("Optional contact columns checked")

