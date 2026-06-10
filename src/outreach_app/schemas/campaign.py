import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


logger = logging.getLogger(__name__)


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignRecipientStatus(StrEnum):
    PENDING = "pending"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: str | None = None
    subject_template: str = Field(..., min_length=3, max_length=300)
    body_template: str = Field(..., min_length=10)
    status: CampaignStatus = CampaignStatus.DRAFT
    dry_run: bool = True
    max_recipients: int | None = Field(default=None, ge=1)
    daily_limit: int | None = Field(default=None, ge=1)

    @field_validator(
        "name",
        "description",
        "subject_template",
        "body_template",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: Any) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        clean_value = value.strip()

        if clean_value == "":
            return None

        return clean_value

    @field_validator("name", "subject_template", "body_template")
    @classmethod
    def required_text_cannot_be_empty(cls, value: str | None) -> str:
        if value is None or value.strip() == "":
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("body_template")
    @classmethod
    def body_template_should_include_unsubscribe_text(cls, value: str) -> str:
        unsubscribe_keywords = [
            "unsubscribe",
            "darse de baja",
            "no recibir",
            "dejar de recibir",
        ]

        normalized_body = value.lower()

        has_unsubscribe_text = any(
            keyword in normalized_body for keyword in unsubscribe_keywords
        )

        if not has_unsubscribe_text:
            logger.warning(
                "Campaign body template does not include unsubscribe wording"
            )

        return value

    @field_validator("daily_limit")
    @classmethod
    def daily_limit_cannot_exceed_max_recipients(
        cls,
        value: int | None,
        info,
    ) -> int | None:
        if value is None:
            return value

        max_recipients = info.data.get("max_recipients")

        if max_recipients is not None and value > max_recipients:
            raise ValueError("daily_limit cannot exceed max_recipients")

        return value


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    subject_template: str | None = Field(default=None, min_length=3, max_length=300)
    body_template: str | None = Field(default=None, min_length=10)
    status: CampaignStatus | None = None
    dry_run: bool | None = None
    max_recipients: int | None = Field(default=None, ge=1)
    daily_limit: int | None = Field(default=None, ge=1)

    @field_validator(
        "name",
        "description",
        "subject_template",
        "body_template",
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


class CampaignRead(BaseModel):
    id: str
    name: str
    description: str | None
    subject_template: str
    body_template: str
    status: CampaignStatus
    dry_run: bool
    max_recipients: int | None
    daily_limit: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignRecipientCreate(BaseModel):
    campaign_id: str
    contact_id: str
    status: CampaignRecipientStatus = CampaignRecipientStatus.PENDING


class CampaignRecipientRead(BaseModel):
    id: str
    campaign_id: str
    contact_id: str
    status: CampaignRecipientStatus
    personalized_subject: str | None
    personalized_body: str | None
    skip_reason: str | None
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)