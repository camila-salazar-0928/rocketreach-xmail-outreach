import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import list_campaigns, list_enriched_events
from dashboard.ui.components import render_section_header


logger = logging.getLogger(__name__)


def get_unique_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return ["all"]

    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    values = values[values != ""]

    return ["all"] + sorted(values.unique().tolist())


def render_kpis(events_df: pd.DataFrame) -> None:
    total_events = len(events_df)

    rendered_count = int((events_df["event_type"] == "rendered").sum())
    dry_run_count = int((events_df["event_type"] == "dry_run").sum())
    sent_count = int((events_df["event_type"] == "sent").sum())
    failed_count = int((events_df["event_type"] == "failed").sum())
    skipped_count = int((events_df["event_type"] == "skipped").sum())
    blocked_count = int((events_df["event_type"] == "blocked").sum())

    unique_contacts = (
        events_df["contact_id"].nunique()
        if "contact_id" in events_df.columns
        else 0
    )

    unique_companies = (
        events_df["company"].dropna().nunique()
        if "company" in events_df.columns
        else 0
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric("Eventos", total_events)
    with kpi2:
        st.metric("Contactos únicos", unique_contacts)
    with kpi3:
        st.metric("Empresas", unique_companies)
    with kpi4:
        st.metric("Sent", sent_count)

    kpi5, kpi6, kpi7, kpi8 = st.columns(4)

    with kpi5:
        st.metric("Rendered", rendered_count)
    with kpi6:
        st.metric("Dry run", dry_run_count)
    with kpi7:
        st.metric("Failed", failed_count)
    with kpi8:
        st.metric("Skipped/Blocked", skipped_count + blocked_count)


def render_time_series(events_df: pd.DataFrame) -> None:
    st.markdown("### Comportamiento temporal")

    if "created_at" not in events_df.columns:
        st.warning("Los eventos no tienen created_at.")
        return

    df = events_df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.dropna(subset=["created_at"])

    if df.empty:
        st.warning("No hay fechas válidas para graficar.")
        return

    grain = st.radio(
        "Agrupación temporal",
        options=["Diario", "Semanal", "Mensual"],
        horizontal=True,
    )

    if grain == "Diario":
        df["period"] = df["created_at"].dt.date.astype(str)
    elif grain == "Semanal":
        df["period"] = df["created_at"].dt.to_period("W").astype(str)
    else:
        df["period"] = df["created_at"].dt.to_period("M").astype(str)

    grouped = (
        df.groupby(["period", "event_type"])
        .size()
        .reset_index(name="count")
        .sort_values("period")
    )

    fig = px.line(
        grouped,
        x="period",
        y="count",
        color="event_type",
        markers=True,
        title=f"Eventos por periodo - {grain}",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_dimension_charts(events_df: pd.DataFrame) -> None:
    st.markdown("### Segmentación de eventos")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        if "industry" in events_df.columns:
            industry_counts = (
                events_df["industry"]
                .fillna("Sin industria")
                .value_counts()
                .head(15)
                .reset_index()
            )
            industry_counts.columns = ["industry", "count"]

            fig_industry = px.bar(
                industry_counts,
                x="count",
                y="industry",
                orientation="h",
                text="count",
                title="Top industrias por eventos",
            )

            st.plotly_chart(fig_industry, use_container_width=True)

    with chart_col2:
        if "country" in events_df.columns:
            country_counts = (
                events_df["country"]
                .fillna("Sin país")
                .value_counts()
                .head(15)
                .reset_index()
            )
            country_counts.columns = ["country", "count"]

            fig_country = px.bar(
                country_counts,
                x="country",
                y="count",
                text="count",
                title="Eventos por país",
            )

            st.plotly_chart(fig_country, use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        if "event_type" in events_df.columns:
            event_counts = (
                events_df["event_type"]
                .value_counts()
                .reset_index()
            )
            event_counts.columns = ["event_type", "count"]

            fig_event = px.pie(
                event_counts,
                names="event_type",
                values="count",
                title="Distribución por tipo de evento",
            )

            st.plotly_chart(fig_event, use_container_width=True)

    with chart_col4:
        if "department" in events_df.columns:
            department_counts = (
                events_df["department"]
                .fillna("Sin departamento")
                .value_counts()
                .head(15)
                .reset_index()
            )
            department_counts.columns = ["department", "count"]

            fig_department = px.bar(
                department_counts,
                x="count",
                y="department",
                orientation="h",
                text="count",
                title="Top departamentos",
            )

            st.plotly_chart(fig_department, use_container_width=True)


def render_traceability_page() -> None:
    render_section_header(
        "Trazabilidad analítica",
        "Monitorea eventos por campaña, industria, país, empresa, cargo y periodo.",
    )

    campaigns_status, campaigns = list_campaigns(limit=500, offset=0)

    campaign_options = {"Todas las campañas": None}

    if campaigns_status == 200 and isinstance(campaigns, list):
        for campaign in campaigns:
            label = f"{campaign.get('name')} | {campaign.get('status')} | {campaign.get('id')}"
            campaign_options[label] = campaign.get("id")

    st.markdown("### Filtros principales")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_campaign_label = st.selectbox(
            "Campaña",
            options=list(campaign_options.keys()),
        )
        selected_campaign_id = campaign_options[selected_campaign_label]

    with col2:
        selected_event_type = st.selectbox(
            "Tipo evento",
            options=["all", "rendered", "dry_run", "sent", "failed", "skipped", "blocked"],
        )

    with col3:
        selected_provider = st.selectbox(
            "Provider",
            options=["all", "mock", "smtp", "tencent_xmail"],
        )

    with col4:
        limit = st.number_input(
            "Límite eventos",
            min_value=1,
            max_value=5000,
            value=1000,
        )

    st.markdown("### Filtros de segmentación")

    seg1, seg2, seg3 = st.columns(3)

    with seg1:
        country_filter = st.text_input("País exacto", placeholder="Ej: Argentina, Colombia")

    with seg2:
        industry_filter = st.text_input("Industria exacta", placeholder="Ej: Retail")

    with seg3:
        source_filter = st.selectbox(
            "Fuente",
            options=["all", "rocketreach", "csv", "manual", "api"],
        )

    seg4, seg5, seg6 = st.columns(3)

    with seg4:
        company_contains = st.text_input("Empresa contiene")

    with seg5:
        job_title_contains = st.text_input("Cargo contiene")

    with seg6:
        email_lookup_status = st.text_input("Estado email exacto", placeholder="Verified emails found")

    seg7, seg8 = st.columns(2)

    with seg7:
        seniority_filter = st.text_input("Seniority exacto")

    with seg8:
        department_filter = st.text_input("Departamento exacto")

    if st.button("Cargar trazabilidad", type="primary"):
        st.session_state["traceability_analytics_loaded"] = True

    if not st.session_state.get("traceability_analytics_loaded", False):
        st.info("Selecciona filtros y haz clic en **Cargar trazabilidad**.")
        return

    status_code, events = list_enriched_events(
        campaign_id=selected_campaign_id,
        event_type=selected_event_type,
        provider=selected_provider,
        country=country_filter.strip() or None,
        industry=industry_filter.strip() or None,
        company_contains=company_contains.strip() or None,
        job_title_contains=job_title_contains.strip() or None,
        seniority=seniority_filter.strip() or None,
        department=department_filter.strip() or None,
        source=source_filter,
        email_lookup_status=email_lookup_status.strip() or None,
        limit=int(limit),
        offset=0,
    )

    if status_code != 200:
        st.error("No se pudo cargar la trazabilidad enriquecida.")
        st.json(events)
        return

    if not events:
        st.warning("No hay eventos para los filtros seleccionados.")
        return

    events_df = pd.DataFrame(events)

    st.markdown("---")
    render_kpis(events_df)

    st.markdown("---")
    render_time_series(events_df)

    st.markdown("---")
    render_dimension_charts(events_df)

    st.markdown("---")
    st.markdown("### Tabla detallada")

    display_cols = [
        col for col in [
            "created_at",
            "event_type",
            "provider",
            "campaign_name",
            "campaign_status",
            "email",
            "first_name",
            "last_name",
            "company",
            "industry",
            "country",
            "region",
            "city",
            "job_title",
            "seniority",
            "department",
            "source",
            "consent_status",
            "email_lookup_status",
            "error_message",
        ]
        if col in events_df.columns
    ]

    st.dataframe(
        events_df[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### Errores detectados")

    if "error_message" in events_df.columns:
        errors_df = events_df[
            events_df["error_message"].notna()
            & (events_df["error_message"].astype(str).str.strip() != "")
        ]

        if errors_df.empty:
            st.success("No hay errores en los eventos cargados.")
        else:
            st.warning(f"Eventos con error: {len(errors_df)}")
            st.dataframe(
                errors_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )