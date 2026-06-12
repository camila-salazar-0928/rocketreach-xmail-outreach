import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import list_campaigns, list_events
from dashboard.ui.components import render_section_header


logger = logging.getLogger(__name__)


def render_traceability_page() -> None:
    render_section_header(
        "Trazabilidad",
        "Consulta eventos de campañas, dry runs, envíos, errores y bloqueos.",
    )

    campaigns_status, campaigns = list_campaigns(limit=200, offset=0)

    campaign_filter_options = {"Todas las campañas": None}

    if campaigns_status == 200 and isinstance(campaigns, list):
        for campaign in campaigns:
            label = (
                f"{campaign.get('name')} | "
                f"{campaign.get('status')} | "
                f"{campaign.get('id')}"
            )
            campaign_filter_options[label] = campaign.get("id")

    st.markdown("### Filtros")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        selected_campaign_label = st.selectbox(
            "Campaña",
            options=list(campaign_filter_options.keys()),
        )
        selected_campaign_id = campaign_filter_options[selected_campaign_label]

    with filter_col2:
        selected_event_type = st.selectbox(
            "Tipo de evento",
            options=[
                "all",
                "rendered",
                "dry_run",
                "sent",
                "failed",
                "skipped",
                "blocked",
            ],
        )

    with filter_col3:
        selected_provider = st.selectbox(
            "Provider",
            options=[
                "all",
                "mock",
                "smtp",
                "tencent_xmail",
            ],
        )

    with filter_col4:
        limit = st.number_input(
            "Límite",
            min_value=1,
            max_value=1000,
            value=500,
        )

    contact_id_filter = st.text_input(
        "Filtrar por Contact ID opcional",
        placeholder="Pega un contact_id si quieres filtrar por contacto",
    )

    if st.button("Cargar trazabilidad", type="primary"):
        st.session_state["traceability_loaded"] = True

    if not st.session_state.get("traceability_loaded", False):
        st.info("Selecciona filtros y haz clic en **Cargar trazabilidad**.")
        return

    status_code, events = list_events(
        campaign_id=selected_campaign_id,
        contact_id=contact_id_filter.strip() or None,
        event_type=selected_event_type,
        provider=selected_provider,
        limit=limit,
        offset=0,
    )

    if status_code != 200:
        st.error("No se pudieron cargar los eventos.")
        st.json(events)
        return

    if not events:
        st.warning("No hay eventos para los filtros seleccionados.")
        return

    events_df = pd.DataFrame(events)

    st.markdown("---")
    st.markdown("### Indicadores")

    total_events = len(events_df)
    rendered_count = int((events_df["event_type"] == "rendered").sum())
    dry_run_count = int((events_df["event_type"] == "dry_run").sum())
    sent_count = int((events_df["event_type"] == "sent").sum())
    failed_count = int((events_df["event_type"] == "failed").sum())
    blocked_count = int((events_df["event_type"] == "blocked").sum())
    skipped_count = int((events_df["event_type"] == "skipped").sum())

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    with kpi1:
        st.metric("Eventos", total_events)
    with kpi2:
        st.metric("Rendered", rendered_count)
    with kpi3:
        st.metric("Dry run", dry_run_count)
    with kpi4:
        st.metric("Sent", sent_count)
    with kpi5:
        st.metric("Failed", failed_count)
    with kpi6:
        st.metric("Blocked/Skipped", blocked_count + skipped_count)

    st.markdown("---")
    st.markdown("### Distribución de eventos")

    event_counts = (
        events_df["event_type"]
        .value_counts(dropna=False)
        .reset_index()
    )
    event_counts.columns = ["event_type", "count"]

    fig_events = px.bar(
        event_counts,
        x="event_type",
        y="count",
        text="count",
        title="Eventos por tipo",
    )

    st.plotly_chart(fig_events, use_container_width=True)

    if "provider" in events_df.columns:
        provider_counts = (
            events_df["provider"]
            .fillna("unknown")
            .value_counts(dropna=False)
            .reset_index()
        )
        provider_counts.columns = ["provider", "count"]

        fig_provider = px.pie(
            provider_counts,
            names="provider",
            values="count",
            title="Eventos por provider",
        )

        st.plotly_chart(fig_provider, use_container_width=True)

    st.markdown("---")
    st.markdown("### Tabla de eventos")

    event_display_cols = [
        col for col in [
            "created_at",
            "event_type",
            "provider",
            "provider_message_id",
            "campaign_id",
            "contact_id",
            "campaign_recipient_id",
            "error_message",
            "metadata_json",
        ]
        if col in events_df.columns
    ]

    st.dataframe(
        events_df[event_display_cols],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### Errores")

    errors_df = events_df[
        events_df["error_message"].notna()
        if "error_message" in events_df.columns
        else []
    ]

    if isinstance(errors_df, pd.DataFrame) and not errors_df.empty:
        st.warning(f"Se encontraron {len(errors_df)} eventos con error.")

        error_cols = [
            col for col in [
                "created_at",
                "event_type",
                "provider",
                "campaign_id",
                "contact_id",
                "error_message",
            ]
            if col in errors_df.columns
        ]

        st.dataframe(
            errors_df[error_cols],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No se encontraron errores en los eventos cargados.")