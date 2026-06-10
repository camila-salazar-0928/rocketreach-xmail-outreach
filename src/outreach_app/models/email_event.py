import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from outreach_app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("campaigns.id"),
        nullable=False,
        index=True,
    )

    contact_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("contacts.id"),
        nullable=False,
        index=True,
    )

    campaign_recipient_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("campaign_recipients.id"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="rendered, dry_run, sent, failed, skipped, blocked",
    )

    provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="smtp, tencent_xmail, mock",
    )

    provider_message_id: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON string with non-sensitive metadata",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    campaign = relationship("Campaign")
    contact = relationship("Contact")
    campaign_recipient = relationship("CampaignRecipient")