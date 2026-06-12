import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime

from outreach_app.models.campaign import Campaign
from outreach_app.models.contact import Contact
from outreach_app.schemas.email_event import EmailEventEnrichedRead

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


@router.get(
    "/enriched",
    response_model=list[EmailEventEnrichedRead],
)
def list_enriched_events_endpoint(
    db: DbSession,
    campaign_id: str | None = None,
    event_type: str | None = None,
    provider: str | None = None,
    country: str | None = None,
    industry: str | None = None,
    company_contains: str | None = None,
    job_title_contains: str | None = None,
    seniority: str | None = None,
    department: str | None = None,
    source: str | None = None,
    email_lookup_status: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EmailEventEnrichedRead]:
    logger.info(
        "API enriched events requested | campaign_id=%s | event_type=%s | provider=%s | country=%s | industry=%s | limit=%s | offset=%s",
        campaign_id,
        event_type,
        provider,
        country,
        industry,
        limit,
        offset,
    )

    query = (
        select(EmailEvent, Contact, Campaign)
        .join(Contact, EmailEvent.contact_id == Contact.id)
        .join(Campaign, EmailEvent.campaign_id == Campaign.id)
    )

    if campaign_id:
        query = query.where(EmailEvent.campaign_id == campaign_id)

    if event_type and event_type != "all":
        query = query.where(EmailEvent.event_type == event_type)

    if provider and provider != "all":
        query = query.where(EmailEvent.provider == provider)

    if country and country != "all":
        query = query.where(Contact.country == country)

    if industry and industry != "all":
        query = query.where(Contact.industry == industry)

    if seniority and seniority != "all":
        query = query.where(Contact.seniority == seniority)

    if department and department != "all":
        query = query.where(Contact.department == department)

    if source and source != "all":
        query = query.where(Contact.source == source)

    if email_lookup_status and email_lookup_status != "all":
        query = query.where(Contact.email_lookup_status == email_lookup_status)

    if company_contains:
        query = query.where(Contact.company.ilike(f"%{company_contains}%"))

    if job_title_contains:
        query = query.where(Contact.job_title.ilike(f"%{job_title_contains}%"))

    if created_from:
        query = query.where(EmailEvent.created_at >= created_from)

    if created_to:
        query = query.where(EmailEvent.created_at <= created_to)

    query = (
        query
        .order_by(EmailEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(query).all()

    response: list[EmailEventEnrichedRead] = []

    for event, contact, campaign in rows:
        response.append(
            EmailEventEnrichedRead(
                id=event.id,
                campaign_id=event.campaign_id,
                campaign_name=campaign.name,
                campaign_status=campaign.status,
                contact_id=event.contact_id,
                email=contact.email,
                first_name=contact.first_name,
                last_name=contact.last_name,
                company=contact.company,
                industry=getattr(contact, "industry", None),
                country=getattr(contact, "country", None),
                region=getattr(contact, "region", None),
                city=getattr(contact, "city", None),
                location=getattr(contact, "location", None),
                job_title=contact.job_title,
                seniority=getattr(contact, "seniority", None),
                department=getattr(contact, "department", None),
                source=contact.source,
                consent_status=contact.consent_status,
                email_lookup_status=getattr(contact, "email_lookup_status", None),
                campaign_recipient_id=event.campaign_recipient_id,
                event_type=event.event_type,
                provider=event.provider,
                provider_message_id=event.provider_message_id,
                error_message=event.error_message,
                metadata_json=event.metadata_json,
                created_at=event.created_at,
            )
        )

    logger.info(
        "API enriched events completed | count=%s",
        len(response),
    )

    return response

