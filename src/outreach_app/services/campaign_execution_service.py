import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from outreach_app.models.campaign import Campaign
from outreach_app.models.campaign_recipient import CampaignRecipient
from outreach_app.schemas.campaign import CampaignRecipientStatus
from outreach_app.schemas.email_event import (
    EmailEventCreate,
    EmailEventType,
    EmailProvider,
)
from outreach_app.services.campaign_service import get_campaign_by_id
from outreach_app.services.contact_service import evaluate_contact_send_eligibility
from outreach_app.services.email_event_service import create_email_event
from outreach_app.services.email_template import (
    EmailTemplateRenderError,
    render_campaign_email,
)
from outreach_app.services.email_sender import (
    EmailSendRequest,
    send_email_via_smtp,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CampaignExecutionSummary:
    campaign_id: str
    total_pending: int
    rendered: int
    dry_run: int
    skipped: int
    failed: int


def list_pending_campaign_recipients(
    db: Session,
    campaign_id: str,
    limit: int | None = None,
) -> list[CampaignRecipient]:
    logger.info(
        "Listing pending campaign recipients | campaign_id=%s | limit=%s",
        campaign_id,
        limit,
    )

    query = (
        select(CampaignRecipient)
        .options(selectinload(CampaignRecipient.contact))
        .where(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == CampaignRecipientStatus.PENDING.value,
        )
        .order_by(CampaignRecipient.created_at.asc())
    )

    if limit is not None:
        query = query.limit(limit)

    result = db.execute(query)
    recipients = list(result.scalars().all())

    logger.info(
        "Pending campaign recipients listed | campaign_id=%s | count=%s",
        campaign_id,
        len(recipients),
    )

    return recipients


def mark_recipient_skipped(
    db: Session,
    campaign: Campaign,
    recipient: CampaignRecipient,
    reason: str,
) -> None:
    logger.warning(
        "Marking campaign recipient as skipped | campaign_id=%s | recipient_id=%s | contact_id=%s | reason=%s",
        campaign.id,
        recipient.id,
        recipient.contact_id,
        reason,
    )

    recipient.status = CampaignRecipientStatus.SKIPPED.value
    recipient.skip_reason = reason

    db.add(recipient)

    create_email_event(
        db=db,
        event_data=EmailEventCreate(
            campaign_id=campaign.id,
            contact_id=recipient.contact_id,
            campaign_recipient_id=recipient.id,
            event_type=EmailEventType.SKIPPED,
            provider=EmailProvider.MOCK,
            metadata={
                "reason": reason,
            },
        ),
    )


def mark_recipient_failed(
    db: Session,
    campaign: Campaign,
    recipient: CampaignRecipient,
    error_message: str,
) -> None:
    logger.warning(
        "Marking campaign recipient as failed | campaign_id=%s | recipient_id=%s | contact_id=%s | error=%s",
        campaign.id,
        recipient.id,
        recipient.contact_id,
        error_message,
    )

    recipient.status = CampaignRecipientStatus.FAILED.value
    recipient.error_message = error_message

    db.add(recipient)

    create_email_event(
        db=db,
        event_data=EmailEventCreate(
            campaign_id=campaign.id,
            contact_id=recipient.contact_id,
            campaign_recipient_id=recipient.id,
            event_type=EmailEventType.FAILED,
            provider=EmailProvider.MOCK,
            error_message=error_message,
            metadata={
                "stage": "template_rendering",
            },
        ),
    )


def process_campaign_recipient(
    db: Session,
    campaign: Campaign,
    recipient: CampaignRecipient,
) -> None:
    contact = recipient.contact

    if contact is None:
        mark_recipient_failed(
            db=db,
            campaign=campaign,
            recipient=recipient,
            error_message="contact_not_loaded",
        )
        return

    logger.info(
        "Processing campaign recipient | campaign_id=%s | recipient_id=%s | contact_id=%s | dry_run=%s",
        campaign.id,
        recipient.id,
        contact.id,
        campaign.dry_run,
    )

    eligibility = evaluate_contact_send_eligibility(contact)

    if not eligibility.allowed_to_send:
        mark_recipient_skipped(
            db=db,
            campaign=campaign,
            recipient=recipient,
            reason=eligibility.reason,
        )
        return

    try:
        rendered_email = render_campaign_email(
            campaign=campaign,
            contact=contact,
        )

    except EmailTemplateRenderError as error:
        mark_recipient_failed(
            db=db,
            campaign=campaign,
            recipient=recipient,
            error_message=str(error),
        )
        return

    recipient.personalized_subject = rendered_email.subject
    recipient.personalized_body = rendered_email.body

    db.add(recipient)

    create_email_event(
        db=db,
        event_data=EmailEventCreate(
            campaign_id=campaign.id,
            contact_id=contact.id,
            campaign_recipient_id=recipient.id,
            event_type=EmailEventType.RENDERED,
            provider=EmailProvider.MOCK,
            metadata={
                "subject_length": len(rendered_email.subject),
                "body_length": len(rendered_email.body),
            },
        ),
    )

    send_result = send_email_via_smtp(
        EmailSendRequest(
            to_email=contact.email,
            subject=rendered_email.subject,
            body=rendered_email.body,
            dry_run=campaign.dry_run,
        )
    )

    logger.info(
        "Email sender result received | campaign_id=%s | recipient_id=%s | contact_id=%s | status=%s | provider=%s",
        campaign.id,
        recipient.id,
        contact.id,
        send_result.status,
        send_result.provider,
    )

    if send_result.status == "dry_run":
        recipient.status = CampaignRecipientStatus.DRY_RUN.value

        db.add(recipient)

        create_email_event(
            db=db,
            event_data=EmailEventCreate(
                campaign_id=campaign.id,
                contact_id=contact.id,
                campaign_recipient_id=recipient.id,
                event_type=EmailEventType.DRY_RUN,
                provider=map_email_provider(send_result.provider),
                provider_message_id=send_result.provider_message_id,
                metadata={
                    "reason": "campaign_dry_run_enabled",
                },
            ),
        )

        logger.info(
            "Campaign recipient marked as dry_run | campaign_id=%s | recipient_id=%s",
            campaign.id,
            recipient.id,
        )

        return

    if send_result.status == "sent":
        recipient.status = CampaignRecipientStatus.SENT.value

        db.add(recipient)

        create_email_event(
            db=db,
            event_data=EmailEventCreate(
                campaign_id=campaign.id,
                contact_id=contact.id,
                campaign_recipient_id=recipient.id,
                event_type=EmailEventType.SENT,
                provider=map_email_provider(send_result.provider),
                provider_message_id=send_result.provider_message_id,
            ),
        )

        logger.info(
            "Campaign recipient marked as sent | campaign_id=%s | recipient_id=%s",
            campaign.id,
            recipient.id,
        )

        return

    if send_result.status == "blocked":
        recipient.status = CampaignRecipientStatus.SKIPPED.value
        recipient.skip_reason = send_result.error_message or "email_sending_blocked"

        db.add(recipient)

        create_email_event(
            db=db,
            event_data=EmailEventCreate(
                campaign_id=campaign.id,
                contact_id=contact.id,
                campaign_recipient_id=recipient.id,
                event_type=EmailEventType.BLOCKED,
                provider=map_email_provider(send_result.provider),
                error_message=send_result.error_message,
                metadata={
                    "reason": send_result.error_message,
                },
            ),
        )

        logger.warning(
            "Campaign recipient blocked by email sender | campaign_id=%s | recipient_id=%s | reason=%s",
            campaign.id,
            recipient.id,
            send_result.error_message,
        )

        return

    recipient.status = CampaignRecipientStatus.FAILED.value
    recipient.error_message = send_result.error_message or "email_sending_failed"

    db.add(recipient)

    create_email_event(
        db=db,
        event_data=EmailEventCreate(
            campaign_id=campaign.id,
            contact_id=contact.id,
            campaign_recipient_id=recipient.id,
            event_type=EmailEventType.FAILED,
            provider=map_email_provider(send_result.provider),
            error_message=send_result.error_message,
        ),
    )

    logger.warning(
        "Campaign recipient failed during email sending | campaign_id=%s | recipient_id=%s | error=%s",
        campaign.id,
        recipient.id,
        send_result.error_message,
    )


def render_and_mark_recipient_dry_run(
    db: Session,
    campaign: Campaign,
    recipient: CampaignRecipient,
) -> None:
    logger.warning(
        "render_and_mark_recipient_dry_run is deprecated; use process_campaign_recipient instead"
    )

    process_campaign_recipient(
        db=db,
        campaign=campaign,
        recipient=recipient,
    )


def execute_campaign_dry_run(
    db: Session,
    campaign_id: str,
    limit: int | None = None,
) -> CampaignExecutionSummary:
    logger.info(
        "Starting campaign dry run execution | campaign_id=%s | limit=%s",
        campaign_id,
        limit,
    )

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.error("Campaign not found for execution | campaign_id=%s", campaign_id)
        raise ValueError("campaign_not_found")

    if campaign.status in {"completed", "cancelled"}:
        logger.error(
            "Campaign cannot be executed due to status | campaign_id=%s | status=%s",
            campaign.id,
            campaign.status,
        )
        raise ValueError("campaign_status_not_executable")

    if not campaign.dry_run:
        logger.error(
            "Real sending not implemented yet | campaign_id=%s | dry_run=%s",
            campaign.id,
            campaign.dry_run,
        )
        raise NotImplementedError(
            "Real email sending is not implemented yet. Set dry_run=True."
        )

    pending_recipients = list_pending_campaign_recipients(
        db=db,
        campaign_id=campaign.id,
        limit=limit,
    )

    total_pending = len(pending_recipients)

    for recipient in pending_recipients:
        process_campaign_recipient(
            db=db,
            campaign=campaign,
            recipient=recipient,
        )

    refreshed_recipients = list(
        db.execute(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == campaign.id
            )
        )
        .scalars()
        .all()
    )

    summary = CampaignExecutionSummary(
        campaign_id=campaign.id,
        total_pending=total_pending,
        rendered=sum(
            recipient.personalized_subject is not None
            and recipient.personalized_body is not None
            for recipient in refreshed_recipients
        ),
        dry_run=sum(
            recipient.status == CampaignRecipientStatus.DRY_RUN.value
            for recipient in refreshed_recipients
        ),
        skipped=sum(
            recipient.status == CampaignRecipientStatus.SKIPPED.value
            for recipient in refreshed_recipients
        ),
        failed=sum(
            recipient.status == CampaignRecipientStatus.FAILED.value
            for recipient in refreshed_recipients
        ),
    )

    logger.info(
        "Campaign dry run execution completed | summary=%s",
        summary,
    )

    return summary


def map_email_provider(provider: str) -> EmailProvider:
    if provider == "mock":
        return EmailProvider.MOCK

    if provider == "smtp":
        return EmailProvider.SMTP

    if provider == "tencent_xmail":
        return EmailProvider.TENCENT_XMAIL

    logger.warning("Unknown email provider received | provider=%s", provider)

    return EmailProvider.MOCK

