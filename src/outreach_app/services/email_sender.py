import logging
import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage

from pydantic import EmailStr

from outreach_app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSendRequest:
    to_email: EmailStr
    subject: str
    body: str
    dry_run: bool = True


@dataclass(frozen=True)
class EmailSendResult:
    status: str
    provider: str
    provider_message_id: str | None = None
    error_message: str | None = None


class EmailSenderConfigError(Exception):
    """Raised when SMTP configuration is incomplete."""


class EmailSenderError(Exception):
    """Raised when SMTP sending fails."""


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"

    local_part, domain = email.split("@", maxsplit=1)

    if len(local_part) <= 2:
        masked_local = "***"
    else:
        masked_local = f"{local_part[:2]}***"

    return f"{masked_local}@{domain}"


def validate_smtp_settings(settings: Settings) -> None:
    missing_fields: list[str] = []

    if not settings.smtp_host:
        missing_fields.append("SMTP_HOST")

    if not settings.smtp_username:
        missing_fields.append("SMTP_USERNAME")

    if not settings.smtp_password:
        missing_fields.append("SMTP_PASSWORD")

    if not settings.smtp_from_email:
        missing_fields.append("SMTP_FROM_EMAIL")

    if missing_fields:
        logger.error(
            "SMTP configuration is incomplete | missing_fields=%s",
            missing_fields,
        )
        raise EmailSenderConfigError(
            f"Incomplete SMTP configuration: {', '.join(missing_fields)}"
        )

    logger.info(
        "SMTP configuration validated | host=%s | port=%s | use_ssl=%s | use_tls=%s | from_email=%s",
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_use_ssl,
        settings.smtp_use_tls,
        mask_email(str(settings.smtp_from_email)),
    )


def build_email_message(
    request: EmailSendRequest,
    settings: Settings,
) -> EmailMessage:
    if not settings.smtp_from_email:
        raise EmailSenderConfigError("SMTP_FROM_EMAIL is required to build the message")

    message = EmailMessage()

    message["Subject"] = request.subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = str(request.to_email)

    message.set_content(request.body)

    logger.info(
        "Email message built | to=%s | subject_length=%s | body_length=%s | dry_run=%s",
        mask_email(str(request.to_email)),
        len(request.subject),
        len(request.body),
        request.dry_run,
    )

    return message


def send_email_via_smtp(
    request: EmailSendRequest,
    settings: Settings | None = None,
) -> EmailSendResult:
    settings = settings or get_settings()

    logger.info(
        "SMTP send requested | to=%s | dry_run=%s | real_sending_enabled=%s",
        mask_email(str(request.to_email)),
        request.dry_run,
        settings.enable_real_email_sending,
    )

    if request.dry_run:
        logger.info(
            "SMTP send skipped because dry_run=True | to=%s",
            mask_email(str(request.to_email)),
        )

        return EmailSendResult(
            status="dry_run",
            provider="mock",
            provider_message_id=f"dry-run-{uuid.uuid4()}",
            error_message=None,
        )

    if not settings.enable_real_email_sending:
        logger.warning(
            "SMTP real sending blocked by safety switch | to=%s",
            mask_email(str(request.to_email)),
        )

        return EmailSendResult(
            status="blocked",
            provider="smtp",
            provider_message_id=None,
            error_message="real_email_sending_disabled",
        )

    validate_smtp_settings(settings)

    message = build_email_message(
        request=request,
        settings=settings,
    )

    try:
        if settings.smtp_use_ssl:
            logger.info(
                "Opening SMTP SSL connection | host=%s | port=%s",
                settings.smtp_host,
                settings.smtp_port,
            )

            with smtplib.SMTP_SSL(
                host=settings.smtp_host,
                port=settings.smtp_port,
                timeout=30,
            ) as smtp:
                smtp.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
                smtp.send_message(message)

        else:
            logger.info(
                "Opening SMTP connection | host=%s | port=%s | use_tls=%s",
                settings.smtp_host,
                settings.smtp_port,
                settings.smtp_use_tls,
            )

            with smtplib.SMTP(
                host=settings.smtp_host,
                port=settings.smtp_port,
                timeout=30,
            ) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()

                smtp.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
                smtp.send_message(message)

        provider_message_id = f"smtp-{uuid.uuid4()}"

        logger.info(
            "SMTP email sent successfully | to=%s | provider_message_id=%s",
            mask_email(str(request.to_email)),
            provider_message_id,
        )

        return EmailSendResult(
            status="sent",
            provider="smtp",
            provider_message_id=provider_message_id,
            error_message=None,
        )

    except Exception as error:
        logger.exception(
            "SMTP email sending failed | to=%s",
            mask_email(str(request.to_email)),
        )

        return EmailSendResult(
            status="failed",
            provider="smtp",
            provider_message_id=None,
            error_message=str(error),
        )