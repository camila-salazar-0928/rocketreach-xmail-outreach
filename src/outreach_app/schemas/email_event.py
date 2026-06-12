import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


logger = logging.getLogger(__name__)


class EmailEventType(StrEnum):
    RENDERED = "rendered"
    DRY_RUN = "dry_run"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class EmailProvider(StrEnum):
    MOCK = "mock"
    SMTP = "smtp"
    TENCENT_XMAIL = "tencent_xmail"


class EmailEventCreate(BaseModel):
    campaign_id: str
    contact_id: str
    campaign_recipient_id: str | None = None
    event_type: EmailEventType
    provider: EmailProvider | None = None
    provider_message_id: str | None = Field(default=None, max_length=300)
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("provider_message_id", "error_message", mode="before")
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


class EmailEventRead(BaseModel):
    id: str
    campaign_id: str
    contact_id: str
    campaign_recipient_id: str | None
    event_type: EmailEventType
    provider: EmailProvider | None
    provider_message_id: str | None
    error_message: str | None
    metadata_json: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailEventEnrichedRead(BaseModel):
    id: str

    campaign_id: str
    campaign_name: str | None
    campaign_status: str | None

    contact_id: str
    email: str | None
    first_name: str | None
    last_name: str | None
    company: str | None
    industry: str | None
    country: str | None
    region: str | None
    city: str | None
    location: str | None
    job_title: str | None
    seniority: str | None
    department: str | None
    source: str | None
    consent_status: str | None
    email_lookup_status: str | None

    campaign_recipient_id: str | None
    event_type: str
    provider: str | None
    provider_message_id: str | None
    error_message: str | None
    metadata_json: str | None
    created_at: datetime


