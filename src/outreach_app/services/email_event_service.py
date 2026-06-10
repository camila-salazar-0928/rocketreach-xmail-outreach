import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from outreach_app.models.email_event import EmailEvent
from outreach_app.schemas.email_event import EmailEventCreate


logger = logging.getLogger(__name__)


SENSITIVE_METADATA_KEYS = {
    "password",
    "token",
    "api_key",
    "secret",
    "smtp_password",
    "body",
    "email_body",
}


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None

    sanitized: dict[str, Any] = {}

    for key, value in metadata.items():
        normalized_key = key.lower()

        if normalized_key in SENSITIVE_METADATA_KEYS:
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value

    return sanitized


def create_email_event(
    db: Session,
    event_data: EmailEventCreate,
) -> EmailEvent:
    logger.info(
        "Creating email event | campaign_id=%s | contact_id=%s | recipient_id=%s | event_type=%s | provider=%s",
        event_data.campaign_id,
        event_data.contact_id,
        event_data.campaign_recipient_id,
        event_data.event_type,
        event_data.provider,
    )

    sanitized_metadata = sanitize_metadata(event_data.metadata)

    metadata_json = None

    if sanitized_metadata is not None:
        metadata_json = json.dumps(
            sanitized_metadata,
            ensure_ascii=False,
            default=str,
        )

    event = EmailEvent(
        campaign_id=event_data.campaign_id,
        contact_id=event_data.contact_id,
        campaign_recipient_id=event_data.campaign_recipient_id,
        event_type=event_data.event_type.value,
        provider=event_data.provider.value if event_data.provider else None,
        provider_message_id=event_data.provider_message_id,
        error_message=event_data.error_message,
        metadata_json=metadata_json,
    )

    try:
        db.add(event)
        db.commit()
        db.refresh(event)

        logger.info(
            "Email event created successfully | event_id=%s | event_type=%s",
            event.id,
            event.event_type,
        )

        return event

    except Exception:
        db.rollback()
        logger.exception(
            "Unexpected error creating email event | campaign_id=%s | contact_id=%s | event_type=%s",
            event_data.campaign_id,
            event_data.contact_id,
            event_data.event_type,
        )
        raise


def list_email_events_by_campaign(
    db: Session,
    campaign_id: str,
) -> list[EmailEvent]:
    logger.debug(
        "Listing email events by campaign | campaign_id=%s",
        campaign_id,
    )

    result = db.execute(
        select(EmailEvent)
        .where(EmailEvent.campaign_id == campaign_id)
        .order_by(EmailEvent.created_at.desc())
    )

    return list(result.scalars().all())


def list_email_events_by_contact(
    db: Session,
    contact_id: str,
) -> list[EmailEvent]:
    logger.debug(
        "Listing email events by contact | contact_id=%s",
        contact_id,
    )

    result = db.execute(
        select(EmailEvent)
        .where(EmailEvent.contact_id == contact_id)
        .order_by(EmailEvent.created_at.desc())
    )

    return list(result.scalars().all())