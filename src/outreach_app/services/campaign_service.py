import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from outreach_app.models.campaign import Campaign
from outreach_app.models.campaign_recipient import CampaignRecipient
from outreach_app.models.contact import Contact
from outreach_app.schemas.campaign import (
    CampaignCreate,
    CampaignRecipientStatus,
    CampaignUpdate,
)
from outreach_app.services.contact_service import (
    evaluate_contact_send_eligibility,
    get_contact_by_id,
)


logger = logging.getLogger(__name__)


def get_campaign_by_id(
    db: Session,
    campaign_id: str,
) -> Campaign | None:
    logger.debug("Searching campaign by id | campaign_id=%s", campaign_id)

    result = db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )

    return result.scalar_one_or_none()


def create_campaign(
    db: Session,
    campaign_data: CampaignCreate,
) -> Campaign:
    logger.info(
        "Creating campaign | name=%s | status=%s | dry_run=%s | max_recipients=%s | daily_limit=%s",
        campaign_data.name,
        campaign_data.status,
        campaign_data.dry_run,
        campaign_data.max_recipients,
        campaign_data.daily_limit,
    )

    campaign = Campaign(
        name=campaign_data.name,
        description=campaign_data.description,
        subject_template=campaign_data.subject_template,
        body_template=campaign_data.body_template,
        status=campaign_data.status.value,
        dry_run=campaign_data.dry_run,
        max_recipients=campaign_data.max_recipients,
        daily_limit=campaign_data.daily_limit,
    )

    try:
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        logger.info(
            "Campaign created successfully | campaign_id=%s | name=%s",
            campaign.id,
            campaign.name,
        )

        return campaign

    except Exception:
        db.rollback()
        logger.exception("Unexpected error creating campaign")
        raise


def update_campaign(
    db: Session,
    campaign: Campaign,
    campaign_data: CampaignUpdate,
) -> Campaign:
    update_data = campaign_data.model_dump(exclude_unset=True)

    logger.info(
        "Updating campaign | campaign_id=%s | fields=%s",
        campaign.id,
        list(update_data.keys()),
    )

    for field_name, value in update_data.items():
        if hasattr(value, "value"):
            value = value.value

        setattr(campaign, field_name, value)

    try:
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        logger.info(
            "Campaign updated successfully | campaign_id=%s",
            campaign.id,
        )

        return campaign

    except Exception:
        db.rollback()
        logger.exception(
            "Unexpected error updating campaign | campaign_id=%s",
            campaign.id,
        )
        raise


def get_campaign_recipient(
    db: Session,
    campaign_id: str,
    contact_id: str,
) -> CampaignRecipient | None:
    logger.debug(
        "Searching campaign recipient | campaign_id=%s | contact_id=%s",
        campaign_id,
        contact_id,
    )

    result = db.execute(
        select(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.contact_id == contact_id,
        )
    )

    return result.scalar_one_or_none()


def count_campaign_recipients(
    db: Session,
    campaign_id: str,
    statuses: list[CampaignRecipientStatus] | None = None,
) -> int:
    query = select(func.count()).select_from(CampaignRecipient).where(
        CampaignRecipient.campaign_id == campaign_id
    )

    if statuses:
        query = query.where(
            CampaignRecipient.status.in_([status.value for status in statuses])
        )

    count = db.execute(query).scalar_one()

    logger.debug(
        "Campaign recipients counted | campaign_id=%s | statuses=%s | count=%s",
        campaign_id,
        statuses,
        count,
    )

    return count


def campaign_has_capacity(
    db: Session,
    campaign: Campaign,
) -> bool:
    if campaign.max_recipients is None:
        return True

    active_recipient_count = count_campaign_recipients(
        db=db,
        campaign_id=campaign.id,
        statuses=[
            CampaignRecipientStatus.PENDING,
            CampaignRecipientStatus.DRY_RUN,
            CampaignRecipientStatus.SENT,
            CampaignRecipientStatus.FAILED,
        ],
    )

    has_capacity = active_recipient_count < campaign.max_recipients

    logger.debug(
        "Campaign capacity evaluated | campaign_id=%s | max_recipients=%s | active_recipients=%s | has_capacity=%s",
        campaign.id,
        campaign.max_recipients,
        active_recipient_count,
        has_capacity,
    )

    return has_capacity


def build_skipped_recipient(
    campaign_id: str,
    contact_id: str,
    skip_reason: str,
) -> CampaignRecipient:
    return CampaignRecipient(
        campaign_id=campaign_id,
        contact_id=contact_id,
        status=CampaignRecipientStatus.SKIPPED.value,
        skip_reason=skip_reason,
    )


def add_contact_to_campaign(
    db: Session,
    campaign: Campaign,
    contact: Contact,
) -> CampaignRecipient:
    logger.info(
        "Adding contact to campaign | campaign_id=%s | contact_id=%s | email=%s",
        campaign.id,
        contact.id,
        contact.email,
    )

    existing_recipient = get_campaign_recipient(
        db=db,
        campaign_id=campaign.id,
        contact_id=contact.id,
    )

    if existing_recipient:
        logger.info(
            "Campaign recipient already exists | recipient_id=%s | campaign_id=%s | contact_id=%s | status=%s",
            existing_recipient.id,
            campaign.id,
            contact.id,
            existing_recipient.status,
        )
        return existing_recipient

    eligibility = evaluate_contact_send_eligibility(contact)

    if not eligibility.allowed_to_send:
        logger.warning(
            "Contact skipped for campaign | campaign_id=%s | contact_id=%s | reason=%s",
            campaign.id,
            contact.id,
            eligibility.reason,
        )

        recipient = build_skipped_recipient(
            campaign_id=campaign.id,
            contact_id=contact.id,
            skip_reason=eligibility.reason,
        )

    elif not campaign_has_capacity(db=db, campaign=campaign):
        logger.warning(
            "Contact skipped because campaign reached max recipients | campaign_id=%s | contact_id=%s",
            campaign.id,
            contact.id,
        )

        recipient = build_skipped_recipient(
            campaign_id=campaign.id,
            contact_id=contact.id,
            skip_reason="campaign_max_recipients_reached",
        )

    else:
        recipient = CampaignRecipient(
            campaign_id=campaign.id,
            contact_id=contact.id,
            status=CampaignRecipientStatus.PENDING.value,
        )

    try:
        db.add(recipient)
        db.commit()
        db.refresh(recipient)

        logger.info(
            "Campaign recipient created | recipient_id=%s | campaign_id=%s | contact_id=%s | status=%s | skip_reason=%s",
            recipient.id,
            campaign.id,
            contact.id,
            recipient.status,
            recipient.skip_reason,
        )

        return recipient

    except IntegrityError:
        db.rollback()

        logger.warning(
            "Campaign recipient creation race condition detected | campaign_id=%s | contact_id=%s",
            campaign.id,
            contact.id,
        )

        existing_recipient = get_campaign_recipient(
            db=db,
            campaign_id=campaign.id,
            contact_id=contact.id,
        )

        if existing_recipient:
            return existing_recipient

        raise

    except Exception:
        db.rollback()
        logger.exception(
            "Unexpected error adding contact to campaign | campaign_id=%s | contact_id=%s",
            campaign.id,
            contact.id,
        )
        raise


def add_contact_id_to_campaign(
    db: Session,
    campaign_id: str,
    contact_id: str,
) -> CampaignRecipient:
    logger.info(
        "Adding contact id to campaign | campaign_id=%s | contact_id=%s",
        campaign_id,
        contact_id,
    )

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.error("Campaign not found | campaign_id=%s", campaign_id)
        raise ValueError("campaign_not_found")

    contact = get_contact_by_id(
        db=db,
        contact_id=contact_id,
    )

    if contact is None:
        logger.error("Contact not found | contact_id=%s", contact_id)
        raise ValueError("contact_not_found")

    return add_contact_to_campaign(
        db=db,
        campaign=campaign,
        contact=contact,
    )


def add_contacts_to_campaign(
    db: Session,
    campaign: Campaign,
    contacts: list[Contact],
) -> list[CampaignRecipient]:
    logger.info(
        "Adding multiple contacts to campaign | campaign_id=%s | contacts_count=%s",
        campaign.id,
        len(contacts),
    )

    recipients: list[CampaignRecipient] = []

    for contact in contacts:
        recipient = add_contact_to_campaign(
            db=db,
            campaign=campaign,
            contact=contact,
        )

        recipients.append(recipient)

    summary = {
        "total": len(recipients),
        "pending": sum(
            recipient.status == CampaignRecipientStatus.PENDING.value
            for recipient in recipients
        ),
        "skipped": sum(
            recipient.status == CampaignRecipientStatus.SKIPPED.value
            for recipient in recipients
        ),
    }

    logger.info(
        "Multiple contacts added to campaign | campaign_id=%s | summary=%s",
        campaign.id,
        summary,
    )

    return recipients


def add_contact_ids_to_campaign(
    db: Session,
    campaign_id: str,
    contact_ids: list[str],
) -> list[CampaignRecipient]:
    logger.info(
        "Adding contact ids to campaign in bulk | campaign_id=%s | requested_count=%s",
        campaign_id,
        len(contact_ids),
    )

    campaign = get_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )

    if campaign is None:
        logger.error("Campaign not found for bulk assignment | campaign_id=%s", campaign_id)
        raise ValueError("campaign_not_found")

    unique_contact_ids = list(dict.fromkeys(contact_ids))

    if len(unique_contact_ids) != len(contact_ids):
        logger.info(
            "Duplicate contact ids removed from bulk assignment | campaign_id=%s | original_count=%s | unique_count=%s",
            campaign_id,
            len(contact_ids),
            len(unique_contact_ids),
        )

    recipients: list[CampaignRecipient] = []

    for contact_id in unique_contact_ids:
        contact = get_contact_by_id(
            db=db,
            contact_id=contact_id,
        )

        if contact is None:
            logger.warning(
                "Contact not found during bulk assignment | campaign_id=%s | contact_id=%s",
                campaign_id,
                contact_id,
            )
            continue

        recipient = add_contact_to_campaign(
            db=db,
            campaign=campaign,
            contact=contact,
        )

        recipients.append(recipient)

    summary = {
        "total_requested": len(contact_ids),
        "unique_contact_ids": len(unique_contact_ids),
        "total_processed": len(recipients),
        "pending": sum(
            recipient.status == CampaignRecipientStatus.PENDING.value
            for recipient in recipients
        ),
        "skipped": sum(
            recipient.status == CampaignRecipientStatus.SKIPPED.value
            for recipient in recipients
        ),
    }

    logger.info(
        "Bulk contact assignment completed | campaign_id=%s | summary=%s",
        campaign_id,
        summary,
    )

    return recipients


def list_campaign_recipients(
    db: Session,
    campaign_id: str,
) -> list[CampaignRecipient]:
    logger.info(
        "Listing campaign recipients | campaign_id=%s",
        campaign_id,
    )

    result = db.execute(
        select(CampaignRecipient)
        .where(CampaignRecipient.campaign_id == campaign_id)
        .order_by(CampaignRecipient.created_at.desc())
    )

    recipients = list(result.scalars().all())

    logger.info(
        "Campaign recipients listed | campaign_id=%s | count=%s",
        campaign_id,
        len(recipients),
    )

    return recipients


def build_campaign_summary(
    db: Session,
    campaign_id: str,
) -> dict:
    logger.info(
        "Building campaign summary | campaign_id=%s",
        campaign_id,
    )

    recipients = list_campaign_recipients(
        db=db,
        campaign_id=campaign_id,
    )

    summary = {
        "campaign_id": campaign_id,
        "total_recipients": len(recipients),
        "pending": sum(
            recipient.status == CampaignRecipientStatus.PENDING.value
            for recipient in recipients
        ),
        "skipped": sum(
            recipient.status == CampaignRecipientStatus.SKIPPED.value
            for recipient in recipients
        ),
        "dry_run": sum(
            recipient.status == CampaignRecipientStatus.DRY_RUN.value
            for recipient in recipients
        ),
        "sent": sum(
            recipient.status == CampaignRecipientStatus.SENT.value
            for recipient in recipients
        ),
        "failed": sum(
            recipient.status == CampaignRecipientStatus.FAILED.value
            for recipient in recipients
        ),
        "cancelled": sum(
            recipient.status == CampaignRecipientStatus.CANCELLED.value
            for recipient in recipients
        ),
    }

    logger.info(
        "Campaign summary built | campaign_id=%s | summary=%s",
        campaign_id,
        summary,
    )

    return summary

