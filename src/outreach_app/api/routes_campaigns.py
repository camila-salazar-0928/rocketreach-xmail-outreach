import logging
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from outreach_app.api.deps import get_db
from outreach_app.models.campaign import Campaign
from outreach_app.schemas.campaign import (
    CampaignBulkAddContactsRequest,
    CampaignBulkAddContactsResponse,
    CampaignCreate,
    CampaignRead,
    CampaignRecipientDetailRead,
    CampaignRecipientRead,
    CampaignRecipientStatus,
    CampaignSummaryResponse,
    CampaignUpdate,
)
from outreach_app.schemas.email_event import EmailEventRead
from outreach_app.services.campaign_execution_service import execute_campaign_dry_run
from outreach_app.services.campaign_service import (
    add_contact_id_to_campaign,
    add_contact_ids_to_campaign,
    create_campaign,
    get_campaign_by_id,
    update_campaign,
    build_campaign_summary,
    list_campaign_recipients,
)
from outreach_app.services.email_event_service import list_email_events_by_campaign


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/campaigns",
    tags=["campaigns"],
)


DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=CampaignRead,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign_endpoint(
    campaign_data: CampaignCreate,
    db: DbSession,
) -> Campaign:
    logger.info(
        "API create campaign requested | name=%s | dry_run=%s | max_recipients=%s",
        campaign_data.name,
        campaign_data.dry_run,
        campaign_data.max_recipients,
    )

    campaign = create_campaign(
        db=db,
        campaign_data=campaign_data,
    )

    return campaign


@router.get(
    "",
    response_model=list[CampaignRead],
)
def list_campaigns_endpoint(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Campaign]:
    logger.info(
        "API list campaigns requested | limit=%s | offset=%s",
        limit,
        offset,
    )

    result = db.execute(
        select(Campaign)
        .order_by(Campaign.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    campaigns = list(result.scalars().all())

    logger.info("API list campaigns completed | count=%s", len(campaigns))

    return campaigns


@router.get(
    "/{campaign_id}",
    response_model=CampaignRead,
)
def get_campaign_endpoint(
    campaign_id: str,
    db: DbSession,
) -> Campaign:
    logger.info("API get campaign requested | campaign_id=%s", campaign_id)

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.warning("API campaign not found | campaign_id=%s", campaign_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="campaign_not_found",
        )

    return campaign


@router.patch(
    "/{campaign_id}",
    response_model=CampaignRead,
)
def update_campaign_endpoint(
    campaign_id: str,
    campaign_data: CampaignUpdate,
    db: DbSession,
) -> Campaign:
    logger.info(
        "API update campaign requested | campaign_id=%s | fields=%s",
        campaign_id,
        list(campaign_data.model_dump(exclude_unset=True).keys()),
    )

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.warning(
            "API campaign not found for update | campaign_id=%s",
            campaign_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="campaign_not_found",
        )

    return update_campaign(
        db=db,
        campaign=campaign,
        campaign_data=campaign_data,
    )


@router.post(
    "/{campaign_id}/contacts/{contact_id}",
    response_model=CampaignRecipientRead,
    status_code=status.HTTP_201_CREATED,
)
def add_contact_to_campaign_endpoint(
    campaign_id: str,
    contact_id: str,
    db: DbSession,
):
    logger.info(
        "API add contact to campaign requested | campaign_id=%s | contact_id=%s",
        campaign_id,
        contact_id,
    )

    try:
        recipient = add_contact_id_to_campaign(
            db=db,
            campaign_id=campaign_id,
            contact_id=contact_id,
        )

    except ValueError as error:
        error_message = str(error)

        logger.warning(
            "API add contact to campaign failed | campaign_id=%s | contact_id=%s | error=%s",
            campaign_id,
            contact_id,
            error_message,
        )

        if error_message == "campaign_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="campaign_not_found",
            ) from error

        if error_message == "contact_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="contact_not_found",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        ) from error

    return recipient


@router.post(
    "/{campaign_id}/execute-dry-run",
)
def execute_campaign_dry_run_endpoint(
    campaign_id: str,
    db: DbSession,
    limit: Annotated[int | None, Query(ge=1, le=500)] = None,
) -> dict:
    logger.info(
        "API execute campaign dry run requested | campaign_id=%s | limit=%s",
        campaign_id,
        limit,
    )

    try:
        summary = execute_campaign_dry_run(
            db=db,
            campaign_id=campaign_id,
            limit=limit,
        )

    except ValueError as error:
        error_message = str(error)

        logger.warning(
            "API execute campaign dry run failed | campaign_id=%s | error=%s",
            campaign_id,
            error_message,
        )

        if error_message == "campaign_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="campaign_not_found",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        ) from error

    except NotImplementedError as error:
        logger.warning(
            "API execute campaign real sending blocked | campaign_id=%s | error=%s",
            campaign_id,
            str(error),
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    result = asdict(summary)

    logger.info(
        "API campaign dry run completed | campaign_id=%s | result=%s",
        campaign_id,
        result,
    )

    return result


@router.get(
    "/{campaign_id}/summary",
    response_model=CampaignSummaryResponse,
)
def get_campaign_summary_endpoint(
    campaign_id: str,
    db: DbSession,
) -> CampaignSummaryResponse:
    logger.info(
        "API campaign summary requested | campaign_id=%s",
        campaign_id,
    )

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.warning(
            "API campaign not found for summary | campaign_id=%s",
            campaign_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="campaign_not_found",
        )

    summary = build_campaign_summary(
        db=db,
        campaign_id=campaign_id,
    )

    return CampaignSummaryResponse(**summary)


@router.get(
    "/{campaign_id}/recipients",
    response_model=list[CampaignRecipientDetailRead],
)
def list_campaign_recipients_endpoint(
    campaign_id: str,
    db: DbSession,
) -> list[CampaignRecipientDetailRead]:
    logger.info(
        "API list campaign recipients requested | campaign_id=%s",
        campaign_id,
    )

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.warning(
            "API campaign not found for recipients | campaign_id=%s",
            campaign_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="campaign_not_found",
        )

    recipients = list_campaign_recipients(
        db=db,
        campaign_id=campaign_id,
    )

    response = []

    for recipient in recipients:
        contact = recipient.contact

        if contact is None:
            logger.warning(
                "Campaign recipient without loaded contact | recipient_id=%s",
                recipient.id,
            )
            continue

        response.append(
            CampaignRecipientDetailRead(
                id=recipient.id,
                campaign_id=recipient.campaign_id,
                contact_id=recipient.contact_id,
                email=contact.email,
                first_name=contact.first_name,
                last_name=contact.last_name,
                company=contact.company,
                job_title=contact.job_title,
                consent_status=contact.consent_status,
                is_active=contact.is_active,
                status=recipient.status,
                skip_reason=recipient.skip_reason,
                error_message=recipient.error_message,
                personalized_subject=recipient.personalized_subject,
                sent_at=recipient.sent_at,
                created_at=recipient.created_at,
                updated_at=recipient.updated_at,
            )
        )

    logger.info(
        "API campaign recipients listed | campaign_id=%s | count=%s",
        campaign_id,
        len(response),
    )

    return response


@router.get(
    "/{campaign_id}/events",
    response_model=list[EmailEventRead],
)
def list_campaign_events_endpoint(
    campaign_id: str,
    db: DbSession,
) -> list:
    logger.info(
        "API list campaign events requested | campaign_id=%s",
        campaign_id,
    )

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.warning(
            "API campaign not found for events | campaign_id=%s",
            campaign_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="campaign_not_found",
        )

    events = list_email_events_by_campaign(
        db=db,
        campaign_id=campaign_id,
    )

    logger.info(
        "API list campaign events completed | campaign_id=%s | count=%s",
        campaign_id,
        len(events),
    )

    return events


@router.post(
    "/{campaign_id}/contacts/bulk",
    response_model=CampaignBulkAddContactsResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_contacts_to_campaign_bulk_endpoint(
    campaign_id: str,
    payload: CampaignBulkAddContactsRequest,
    db: DbSession,
) -> CampaignBulkAddContactsResponse:
    logger.info(
        "API bulk add contacts to campaign requested | campaign_id=%s | contact_count=%s",
        campaign_id,
        len(payload.contact_ids),
    )

    try:
        recipients = add_contact_ids_to_campaign(
            db=db,
            campaign_id=campaign_id,
            contact_ids=payload.contact_ids,
        )

    except ValueError as error:
        error_message = str(error)

        logger.warning(
            "API bulk add contacts to campaign failed | campaign_id=%s | error=%s",
            campaign_id,
            error_message,
        )

        if error_message == "campaign_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="campaign_not_found",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        ) from error

    response = CampaignBulkAddContactsResponse(
        campaign_id=campaign_id,
        total_requested=len(payload.contact_ids),
        total_processed=len(recipients),
        pending=sum(
            recipient.status == CampaignRecipientStatus.PENDING.value
            for recipient in recipients
        ),
        skipped=sum(
            recipient.status == CampaignRecipientStatus.SKIPPED.value
            for recipient in recipients
        ),
        dry_run=sum(
            recipient.status == CampaignRecipientStatus.DRY_RUN.value
            for recipient in recipients
        ),
        sent=sum(
            recipient.status == CampaignRecipientStatus.SENT.value
            for recipient in recipients
        ),
        failed=sum(
            recipient.status == CampaignRecipientStatus.FAILED.value
            for recipient in recipients
        ),
        recipients=recipients,
    )

    logger.info(
        "API bulk add contacts to campaign completed | campaign_id=%s | pending=%s | skipped=%s",
        campaign_id,
        response.pending,
        response.skipped,
    )

    return response

