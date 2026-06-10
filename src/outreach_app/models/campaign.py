import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from outreach_app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    subject_template: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    body_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        comment="draft, ready, running, paused, completed, cancelled",
    )

    dry_run: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="If true, the campaign simulates sending without real emails",
    )

    max_recipients: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum number of recipients allowed for this campaign",
    )

    daily_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum number of emails to send per day for this campaign",
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

    recipients = relationship(
        "CampaignRecipient",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

