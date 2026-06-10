import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from outreach_app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "contact_id",
            name="uq_campaign_recipient_campaign_contact",
        ),
    )

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

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        comment="pending, skipped, dry_run, sent, failed, cancelled",
    )

    personalized_subject: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    personalized_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    skip_reason: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    campaign = relationship(
        "Campaign",
        back_populates="recipients",
    )

    contact = relationship("Contact")