import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import get_health, list_campaigns, list_contacts
from dashboard.ui.components import render_metric_card, render_section_header


def render_overview_page() -> None:
    render_section_header(
        "Overview",
        "Resumen general de contactos y campañas.",
    )

    health_status, health_body = get_health()
    contacts_status, contacts_body = list_contacts(limit=200, offset=0)
    campaigns_status, campaigns_body = list_campaigns(limit=200, offset=0)

    api_ok = health_status == 200
    total_contacts = len(contacts_body) if isinstance(contacts_body, list) else 0
    total_campaigns = len(campaigns_body) if isinstance(campaigns_body, list) else 0

    contactable_contacts = 0
    unsubscribed_contacts = 0
    blocked_contacts = 0
    bounced_contacts = 0

    if isinstance(contacts_body, list):
        for contact in contacts_body:
            consent_status = contact.get("consent_status")
            is_active = contact.get("is_active")

            if consent_status == "consented" and is_active:
                contactable_contacts += 1
            elif consent_status == "unsubscribed":
                unsubscribed_contacts += 1
            elif consent_status == "blocked":
                blocked_contacts += 1
            elif consent_status == "bounced":
                bounced_contacts += 1

    draft_campaigns = 0
    dry_run_campaigns = 0

    if isinstance(campaigns_body, list):
        for campaign in campaigns_body:
            if campaign.get("status") == "draft":
                draft_campaigns += 1
            if campaign.get("dry_run") is True:
                dry_run_campaigns += 1

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("API", "Online" if api_ok else "Offline")
    with col2:
        render_metric_card("Contactos", total_contacts)
    with col3:
        render_metric_card("Contactables", contactable_contacts)
    with col4:
        render_metric_card("Campañas", total_campaigns)

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        render_metric_card("Draft", draft_campaigns)
    with col6:
        render_metric_card("Dry run", dry_run_campaigns)
    with col7:
        render_metric_card("Unsubscribed", unsubscribed_contacts)
    with col8:
        render_metric_card("Blocked/Bounced", blocked_contacts + bounced_contacts)

    st.markdown("---")

    if isinstance(contacts_body, list) and contacts_body:
        render_section_header("Distribución de contactos por consentimiento")

        contacts_df = pd.DataFrame(contacts_body)
        consent_counts = (
            contacts_df["consent_status"]
            .value_counts(dropna=False)
            .reset_index()
        )
        consent_counts.columns = ["consent_status", "count"]

        fig = px.pie(
            consent_counts,
            names="consent_status",
            values="count",
            title="Contactos por estado de consentimiento",
        )

        st.plotly_chart(fig, use_container_width=True)

    if isinstance(campaigns_body, list) and campaigns_body:
        render_section_header("Últimas campañas")

        campaigns_df = pd.DataFrame(campaigns_body)
        display_cols = [
            col for col in [
                "id",
                "name",
                "status",
                "dry_run",
                "max_recipients",
                "daily_limit",
                "created_at",
            ] if col in campaigns_df.columns
        ]

        st.dataframe(
            campaigns_df[display_cols],
            use_container_width=True,
            hide_index=True,
        )