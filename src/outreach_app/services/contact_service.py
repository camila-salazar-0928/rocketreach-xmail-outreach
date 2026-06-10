import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from outreach_app.models.contact import Contact
from outreach_app.schemas.contact import (
    ConsentStatus,
    ContactCreate,
    ContactSendEligibility,
    ContactUpdate,
)


logger = logging.getLogger(__name__)


def get_contact_by_email(
    db: Session,
    email: str,
) -> Contact | None:
    normalized_email = email.strip().lower()

    logger.debug("Searching contact by email | email=%s", normalized_email)

    result = db.execute(
        select(Contact).where(Contact.email == normalized_email)
    )

    return result.scalar_one_or_none()


def get_contact_by_id(
    db: Session,
    contact_id: str,
) -> Contact | None:
    logger.debug("Searching contact by id | contact_id=%s", contact_id)

    result = db.execute(
        select(Contact).where(Contact.id == contact_id)
    )

    return result.scalar_one_or_none()


def create_contact(
    db: Session,
    contact_data: ContactCreate,
) -> Contact:
    logger.info(
        "Creating contact | email=%s | source=%s | consent_status=%s",
        contact_data.email,
        contact_data.source,
        contact_data.consent_status,
    )

    existing_contact = get_contact_by_email(
        db=db,
        email=str(contact_data.email),
    )

    if existing_contact:
        logger.info(
            "Contact already exists | contact_id=%s | email=%s",
            existing_contact.id,
            existing_contact.email,
        )
        return existing_contact

    contact = Contact(
        email=str(contact_data.email),
        first_name=contact_data.first_name,
        last_name=contact_data.last_name,
        company=contact_data.company,
        job_title=contact_data.job_title,
        source=contact_data.source,
        consent_status=contact_data.consent_status.value,
        is_active=contact_data.is_active,
        notes=contact_data.notes,
    )

    try:
        db.add(contact)
        db.commit()
        db.refresh(contact)

        logger.info(
            "Contact created successfully | contact_id=%s | email=%s",
            contact.id,
            contact.email,
        )

        return contact

    except IntegrityError:
        db.rollback()

        logger.warning(
            "Contact creation race condition detected | email=%s",
            contact_data.email,
        )

        existing_contact = get_contact_by_email(
            db=db,
            email=str(contact_data.email),
        )

        if existing_contact:
            return existing_contact

        raise

    except Exception:
        db.rollback()
        logger.exception("Unexpected error creating contact")
        raise


def update_contact(
    db: Session,
    contact: Contact,
    contact_data: ContactUpdate,
) -> Contact:
    update_data = contact_data.model_dump(exclude_unset=True)

    logger.info(
        "Updating contact | contact_id=%s | fields=%s",
        contact.id,
        list(update_data.keys()),
    )

    for field_name, value in update_data.items():
        if isinstance(value, ConsentStatus):
            value = value.value

        setattr(contact, field_name, value)

    try:
        db.add(contact)
        db.commit()
        db.refresh(contact)

        logger.info("Contact updated successfully | contact_id=%s", contact.id)

        return contact

    except Exception:
        db.rollback()
        logger.exception(
            "Unexpected error updating contact | contact_id=%s",
            contact.id,
        )
        raise


def evaluate_contact_send_eligibility(
    contact: Contact,
) -> ContactSendEligibility:
    logger.debug(
        "Evaluating contact send eligibility | contact_id=%s | email=%s",
        contact.id,
        contact.email,
    )

    if not contact.is_active:
        return ContactSendEligibility(
            contact_id=contact.id,
            email=contact.email,
            allowed_to_send=False,
            reason="contact_inactive",
        )

    if contact.consent_status == ConsentStatus.UNSUBSCRIBED.value:
        return ContactSendEligibility(
            contact_id=contact.id,
            email=contact.email,
            allowed_to_send=False,
            reason="contact_unsubscribed",
        )

    if contact.consent_status == ConsentStatus.BOUNCED.value:
        return ContactSendEligibility(
            contact_id=contact.id,
            email=contact.email,
            allowed_to_send=False,
            reason="contact_bounced",
        )

    if contact.consent_status == ConsentStatus.BLOCKED.value:
        return ContactSendEligibility(
            contact_id=contact.id,
            email=contact.email,
            allowed_to_send=False,
            reason="contact_blocked",
        )

    if contact.consent_status != ConsentStatus.CONSENTED.value:
        return ContactSendEligibility(
            contact_id=contact.id,
            email=contact.email,
            allowed_to_send=False,
            reason="contact_without_consent",
        )

    return ContactSendEligibility(
        contact_id=contact.id,
        email=contact.email,
        allowed_to_send=True,
        reason="contact_allowed",
    )


def mark_contact_unsubscribed(
    db: Session,
    contact: Contact,
) -> Contact:
    logger.info(
        "Marking contact as unsubscribed | contact_id=%s | email=%s",
        contact.id,
        contact.email,
    )

    update_data = ContactUpdate(
        consent_status=ConsentStatus.UNSUBSCRIBED,
        is_active=False,
    )

    return update_contact(
        db=db,
        contact=contact,
        contact_data=update_data,
    )


def mark_contact_bounced(
    db: Session,
    contact: Contact,
) -> Contact:
    logger.info(
        "Marking contact as bounced | contact_id=%s | email=%s",
        contact.id,
        contact.email,
    )

    update_data = ContactUpdate(
        consent_status=ConsentStatus.BOUNCED,
        is_active=False,
    )

    return update_contact(
        db=db,
        contact=contact,
        contact_data=update_data,
    )


def mark_contact_blocked(
    db: Session,
    contact: Contact,
) -> Contact:
    logger.info(
        "Marking contact as blocked | contact_id=%s | email=%s",
        contact.id,
        contact.email,
    )

    update_data = ContactUpdate(
        consent_status=ConsentStatus.BLOCKED,
        is_active=False,
    )

    return update_contact(
        db=db,
        contact=contact,
        contact_data=update_data,
    )