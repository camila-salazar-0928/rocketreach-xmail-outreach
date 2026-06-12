import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from outreach_app.api.deps import get_db
from outreach_app.models.email_event import EmailEvent
from outreach_app.schemas.email_event import EmailEventRead


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/events",
    tags=["events"],
)


DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=list[EmailEventRead],
)
def list_events_endpoint(
    db: DbSession,
    campaign_id: str | None = None,
    contact_id: str | None = None,
    event_type: str | None = None,
    provider: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EmailEvent]:
    logger.info(
        "API list events requested | campaign_id=%s | contact_id=%s | event_type=%s | provider=%s | limit=%s | offset=%s",
        campaign_id,
        contact_id,
        event_type,
        provider,
        limit,
        offset,
    )

    query = select(EmailEvent)

    if campaign_id:
        query = query.where(EmailEvent.campaign_id == campaign_id)

    if contact_id:
        query = query.where(EmailEvent.contact_id == contact_id)

    if event_type:
        query = query.where(EmailEvent.event_type == event_type)

    if provider:
        query = query.where(EmailEvent.provider == provider)

    query = (
        query
        .order_by(EmailEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = db.execute(query)

    events = list(result.scalars().all())

    logger.info(
        "API list events completed | count=%s",
        len(events),
    )

    return events
