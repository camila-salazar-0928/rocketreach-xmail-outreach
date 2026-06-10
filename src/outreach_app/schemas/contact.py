import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


logger = logging.getLogger(__name__)


class ConsentStatus(StrEnum):
    UNKNOWN = "unknown"
    CONSENTED = "consented"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    BLOCKED = "blocked"


class ContactBase(BaseModel):
    email: EmailStr
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default="manual", max_length=100)
    consent_status: ConsentStatus = ConsentStatus.UNKNOWN
    is_active: bool = True
    notes: str | None = None

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        normalized_email = str(value).strip().lower()

        logger.debug(
            "Email normalized | original=%s | normalized=%s",
            value,
            normalized_email,
        )

        return normalized_email

    @field_validator(
        "first_name",
        "last_name",
        "company",
        "job_title",
        "source",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        clean_value = value.strip()

        if clean_value == "":
            return None

        return clean_value


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=100)
    consent_status: ConsentStatus | None = None
    is_active: bool | None = None
    notes: str | None = None

    @field_validator(
        "first_name",
        "last_name",
        "company",
        "job_title",
        "source",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        clean_value = value.strip()

        if clean_value == "":
            return None

        return clean_value


class ContactRead(BaseModel):
    id: str
    email: EmailStr
    first_name: str | None
    last_name: str | None
    company: str | None
    job_title: str | None
    source: str | None
    consent_status: ConsentStatus
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactSendEligibility(BaseModel):
    contact_id: str
    email: EmailStr
    allowed_to_send: bool
    reason: str