import logging
from dataclasses import dataclass
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError

from outreach_app.models.campaign import Campaign
from outreach_app.models.contact import Contact


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    body: str


class EmailTemplateRenderError(Exception):
    """Raised when an email template cannot be rendered."""


def normalize_template_value(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def build_contact_template_context(contact: Contact) -> dict[str, str]:
    context = {
        "email": normalize_template_value(contact.email),
        "first_name": normalize_template_value(contact.first_name),
        "last_name": normalize_template_value(contact.last_name),
        "company": normalize_template_value(contact.company),
        "job_title": normalize_template_value(contact.job_title),
        "source": normalize_template_value(contact.source),
    }

    logger.debug(
        "Contact template context built | contact_id=%s | available_fields=%s",
        contact.id,
        list(context.keys()),
    )

    return context


def get_template_environment() -> Environment:
    return Environment(
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template_string(
    template_text: str,
    context: dict[str, str],
    template_name: str,
) -> str:
    logger.debug(
        "Rendering template | template_name=%s | context_keys=%s",
        template_name,
        list(context.keys()),
    )

    try:
        environment = get_template_environment()
        template = environment.from_string(template_text)
        rendered_text = template.render(**context).strip()

        logger.debug(
            "Template rendered successfully | template_name=%s | rendered_length=%s",
            template_name,
            len(rendered_text),
        )

        return rendered_text

    except TemplateError as error:
        logger.warning(
            "Template rendering failed | template_name=%s | error=%s",
            template_name,
            str(error),
        )

        raise EmailTemplateRenderError(
            f"Could not render template '{template_name}': {error}"
        ) from error


def render_campaign_email(
    campaign: Campaign,
    contact: Contact,
) -> RenderedEmail:
    logger.info(
        "Rendering campaign email | campaign_id=%s | contact_id=%s | email=%s",
        campaign.id,
        contact.id,
        contact.email,
    )

    context = build_contact_template_context(contact)

    subject = render_template_string(
        template_text=campaign.subject_template,
        context=context,
        template_name="subject_template",
    )

    body = render_template_string(
        template_text=campaign.body_template,
        context=context,
        template_name="body_template",
    )

    logger.info(
        "Campaign email rendered successfully | campaign_id=%s | contact_id=%s | subject_length=%s | body_length=%s",
        campaign.id,
        contact.id,
        len(subject),
        len(body),
    )

    return RenderedEmail(
        subject=subject,
        body=body,
    )