import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from outreach_app.api.deps import get_db
from outreach_app.models.contact import Contact
from outreach_app.schemas.contact import (
    ContactCreate,
    ContactRead,
    ContactSendEligibility,
    ContactUpdate,
)
from outreach_app.services.contact_service import (
    create_contact,
    evaluate_contact_send_eligibility,
    get_contact_by_email,
    get_contact_by_id,
    mark_contact_blocked,
    mark_contact_unsubscribed,
    update_contact,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/contacts",
    tags=["contacts"],
)


DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=ContactRead,
    status_code=status.HTTP_201_CREATED,
)
def create_contact_endpoint(
    contact_data: ContactCreate,
    db: DbSession,
) -> Contact:
    logger.info(
        "API create contact requested | email=%s | source=%s",
        contact_data.email,
        contact_data.source,
    )

    contact = create_contact(
        db=db,
        contact_data=contact_data,
    )

    return contact


@router.get(
    "",
    response_model=list[ContactRead],
)
def list_contacts_endpoint(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Contact]:
    logger.info(
        "API list contacts requested | limit=%s | offset=%s",
        limit,
        offset,
    )

    result = db.execute(
        select(Contact)
        .order_by(Contact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    contacts = list(result.scalars().all())

    logger.info("API list contacts completed | count=%s", len(contacts))

    return contacts


@router.get(
    "/by-email/{email}",
    response_model=ContactRead,
)
def get_contact_by_email_endpoint(
    email: str,
    db: DbSession,
) -> Contact:
    logger.info("API get contact by email requested | email=%s", email)

    contact = get_contact_by_email(
        db=db,
        email=email,
    )

    if contact is None:
        logger.warning("API contact by email not found | email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contact_not_found",
        )

    return contact


@router.get(
    "/{contact_id}",
    response_model=ContactRead,
)
def get_contact_endpoint(
    contact_id: str,
    db: DbSession,
) -> Contact:
    logger.info("API get contact requested | contact_id=%s", contact_id)

    contact = get_contact_by_id(
        db=db,
        contact_id=contact_id,
    )

    if contact is None:
        logger.warning("API contact not found | contact_id=%s", contact_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contact_not_found",
        )

    return contact


@router.patch(
    "/{contact_id}",
    response_model=ContactRead,
)
def update_contact_endpoint(
    contact_id: str,
    contact_data: ContactUpdate,
    db: DbSession,
) -> Contact:
    logger.info(
        "API update contact requested | contact_id=%s | fields=%s",
        contact_id,
        list(contact_data.model_dump(exclude_unset=True).keys()),
    )

    contact = get_contact_by_id(
        db=db,
        contact_id=contact_id,
    )

    if contact is None:
        logger.warning("API contact not found for update | contact_id=%s", contact_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contact_not_found",
        )

    return update_contact(
        db=db,
        contact=contact,
        contact_data=contact_data,
    )


@router.get(
    "/{contact_id}/eligibility",
    response_model=ContactSendEligibility,
)
def get_contact_eligibility_endpoint(
    contact_id: str,
    db: DbSession,
) -> ContactSendEligibility:
    logger.info(
        "API contact eligibility requested | contact_id=%s",
        contact_id,
    )

    contact = get_contact_by_id(
        db=db,
        contact_id=contact_id,
    )

    if contact is None:
        logger.warning(
            "API contact not found for eligibility | contact_id=%s",
            contact_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contact_not_found",
        )

    return evaluate_contact_send_eligibility(contact)


@router.post(
    "/{contact_id}/unsubscribe",
    response_model=ContactRead,
)
def unsubscribe_contact_endpoint(
    contact_id: str,
    db: DbSession,
) -> Contact:
    logger.info(
        "API unsubscribe contact requested | contact_id=%s",
        contact_id,
    )

    contact = get_contact_by_id(
        db=db,
        contact_id=contact_id,
    )

    if contact is None:
        logger.warning(
            "API contact not found for unsubscribe | contact_id=%s",
            contact_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contact_not_found",
        )

    return mark_contact_unsubscribed(
        db=db,
        contact=contact,
    )


@router.post(
    "/{contact_id}/block",
    response_model=ContactRead,
)
def block_contact_endpoint(
    contact_id: str,
    db: DbSession,
) -> Contact:
    logger.info(
        "API block contact requested | contact_id=%s",
        contact_id,
    )

    contact = get_contact_by_id(
        db=db,
        contact_id=contact_id,
    )

    if contact is None:
        logger.warning(
            "API contact not found for block | contact_id=%s",
            contact_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contact_not_found",
        )

    return mark_contact_blocked(
        db=db,
        contact=contact,
    )