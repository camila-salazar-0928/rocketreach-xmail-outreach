import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def request_api(
    method: str,
    path: str,
    json_payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    url = f"{API_BASE_URL}{path}"

    try:
        with httpx.Client(timeout=30) as client:
            response = client.request(
                method=method,
                url=url,
                json=json_payload,
                params=params,
            )

        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, response.text

    except httpx.ConnectError:
        logger.exception("Could not connect to API")
        return 0, {
            "detail": "No se pudo conectar a la API. Verifica que FastAPI esté corriendo."
        }

    except Exception as error:
        logger.exception("Unexpected API client error")
        return 0, {"detail": str(error)}


def get_health() -> tuple[int, Any]:
    return request_api("GET", "/health")


def list_contacts(limit: int = 500, offset: int = 0) -> tuple[int, Any]:
    return request_api(
        "GET",
        "/contacts",
        params={"limit": limit, "offset": offset},
    )


def list_campaigns(limit: int = 100, offset: int = 0) -> tuple[int, Any]:
    return request_api(
        "GET",
        "/campaigns",
        params={"limit": limit, "offset": offset},
    )


def get_campaign_events(campaign_id: str) -> tuple[int, Any]:
    return request_api(
        "GET",
        f"/campaigns/{campaign_id}/events",
    )


def add_contacts_to_campaign_bulk(
    campaign_id: str,
    contact_ids: list[str],
) -> tuple[int, Any]:
    return request_api(
        "POST",
        f"/campaigns/{campaign_id}/contacts/bulk",
        json_payload={
            "contact_ids": contact_ids,
        },
    )


def execute_campaign_dry_run(
    campaign_id: str,
    limit: int | None = None,
) -> tuple[int, Any]:
    params = None

    if limit is not None:
        params = {"limit": limit}

    return request_api(
        "POST",
        f"/campaigns/{campaign_id}/execute-dry-run",
        params=params,
    )


def get_campaign_summary(campaign_id: str) -> tuple[int, Any]:
    return request_api(
        "GET",
        f"/campaigns/{campaign_id}/summary",
    )


def get_campaign_recipients(campaign_id: str) -> tuple[int, Any]:
    return request_api(
        "GET",
        f"/campaigns/{campaign_id}/recipients",
    )


def list_events(
    campaign_id: str | None = None,
    contact_id: str | None = None,
    event_type: str | None = None,
    provider: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> tuple[int, Any]:
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }

    if campaign_id:
        params["campaign_id"] = campaign_id

    if contact_id:
        params["contact_id"] = contact_id

    if event_type and event_type != "all":
        params["event_type"] = event_type

    if provider and provider != "all":
        params["provider"] = provider

    return request_api(
        "GET",
        "/events",
        params=params,
    )


def create_contact(payload: dict[str, Any]) -> tuple[int, Any]:
    return request_api(
        "POST",
        "/contacts",
        json_payload=payload,
    )


def update_contact(contact_id: str, payload: dict[str, Any]) -> tuple[int, Any]:
    return request_api(
        "PATCH",
        f"/contacts/{contact_id}",
        json_payload=payload,
    )


def get_contact_eligibility(contact_id: str) -> tuple[int, Any]:
    return request_api(
        "GET",
        f"/contacts/{contact_id}/eligibility",
    )


def unsubscribe_contact(contact_id: str) -> tuple[int, Any]:
    return request_api(
        "POST",
        f"/contacts/{contact_id}/unsubscribe",
    )


def block_contact(contact_id: str) -> tuple[int, Any]:
    return request_api(
        "POST",
        f"/contacts/{contact_id}/block",
    )


def create_campaign(payload: dict[str, Any]) -> tuple[int, Any]:
    return request_api(
        "POST",
        "/campaigns",
        json_payload=payload,
    )


def update_campaign(campaign_id: str, payload: dict[str, Any]) -> tuple[int, Any]:
    return request_api(
        "PATCH",
        f"/campaigns/{campaign_id}",
        json_payload=payload,
    )


def list_enriched_events(
    campaign_id: str | None = None,
    event_type: str | None = None,
    provider: str | None = None,
    country: str | None = None,
    industry: str | None = None,
    company_contains: str | None = None,
    job_title_contains: str | None = None,
    seniority: str | None = None,
    department: str | None = None,
    source: str | None = None,
    email_lookup_status: str | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> tuple[int, Any]:
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }

    optional_params = {
        "campaign_id": campaign_id,
        "event_type": event_type,
        "provider": provider,
        "country": country,
        "industry": industry,
        "company_contains": company_contains,
        "job_title_contains": job_title_contains,
        "seniority": seniority,
        "department": department,
        "source": source,
        "email_lookup_status": email_lookup_status,
    }

    for key, value in optional_params.items():
        if value and value != "all":
            params[key] = value

    return request_api(
        "GET",
        "/events/enriched",
        params=params,
    )

