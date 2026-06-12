import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import (
    create_campaign,
    execute_campaign_dry_run,
    get_campaign_events,
    get_campaign_recipients,
    get_campaign_summary,
    list_campaigns,
    update_campaign,
)
from dashboard.ui.components import render_section_header


logger = logging.getLogger(__name__)


def render_create_campaign_form() -> None:
    with st.expander("➕ Crear nueva campaña", expanded=False):
        st.caption(
            "Crea campañas en modo dry_run para validar personalización, destinatarios y trazabilidad antes de cualquier envío real."
        )

        with st.form("create_campaign_form"):
            name = st.text_input(
                "Nombre de la campaña",
                placeholder="Ej: RocketReach - Retail Argentina",
            )

            description = st.text_area(
                "Descripción",
                placeholder="Describe el objetivo o segmento de esta campaña.",
            )

            subject_template = st.text_input(
                "Subject template",
                value="{{ first_name }}, una idea para {{ company }}",
            )

            body_template = st.text_area(
                "Body template",
                value=(
                    "Hola {{ first_name }},\n\n"
                    "Vi que trabajas como {{ job_title }} en {{ company }}, "
                    "una empresa de la industria {{ industry }} en {{ country }}.\n\n"
                    "Creo que podría ser relevante conversar sobre una oportunidad "
                    "relacionada con tu área de {{ department }}.\n\n"
                    "¿Te parecería bien si te comparto más contexto?\n\n"
                    "Saludos,\n"
                    "Maria Camila"
                ),
                height=260,
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                status_value = st.selectbox(
                    "Estado",
                    options=["draft", "ready", "paused"],
                    index=0,
                )

            with col2:
                dry_run = st.checkbox(
                    "Dry run",
                    value=True,
                    help="Debe estar activo para simular antes de enviar correos reales.",
                )

            with col3:
                max_recipients = st.number_input(
                    "Máximo recipients",
                    min_value=1,
                    max_value=10000,
                    value=100,
                )

            daily_limit = st.number_input(
                "Límite diario",
                min_value=1,
                max_value=1000,
                value=25,
            )

            submitted = st.form_submit_button("Crear campaña")

        if submitted:
            if not name.strip():
                st.warning("El nombre de la campaña es obligatorio.")
                return

            if not subject_template.strip():
                st.warning("El subject template es obligatorio.")
                return

            if not body_template.strip():
                st.warning("El body template es obligatorio.")
                return

            payload = {
                "name": name.strip(),
                "description": description.strip() or None,
                "subject_template": subject_template.strip(),
                "body_template": body_template.strip(),
                "status": status_value,
                "dry_run": dry_run,
                "max_recipients": int(max_recipients),
                "daily_limit": int(daily_limit),
            }

            status_code, body = create_campaign(payload)

            if 200 <= status_code < 300:
                st.success("Campaña creada correctamente.")
                st.json(body)
                st.rerun()
            else:
                st.error("No se pudo crear la campaña.")
                st.json(body)


def render_campaigns_page() -> None:
    render_section_header(
        "Campañas",
        "Gestiona campañas, revisa destinatarios y ejecuta dry runs.",
    )

    render_create_campaign_form()

    st.markdown("---")

    status_code, campaigns = list_campaigns(limit=100, offset=0)

    if status_code != 200:
        st.error("No se pudieron cargar las campañas.")
        st.json(campaigns)
        return

    if not campaigns:
        st.warning("No hay campañas creadas todavía.")
        return

    campaigns_df = pd.DataFrame(campaigns)

    campaign_options = {
        f"{row['name']} | {row['status']} | dry_run={row['dry_run']} | {row['id']}": row["id"]
        for _, row in campaigns_df.iterrows()
    }

    selected_label = st.selectbox(
        "Selecciona una campaña",
        options=list(campaign_options.keys()),
    )

    campaign_id = campaign_options[selected_label]

    selected_campaign = campaigns_df[
        campaigns_df["id"] == campaign_id
    ].iloc[0].to_dict()

    st.markdown("### Detalle de campaña")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Estado", selected_campaign.get("status"))
    with col2:
        st.metric("Dry run", str(selected_campaign.get("dry_run")))
    with col3:
        st.metric("Max recipients", selected_campaign.get("max_recipients") or "Sin límite")
    with col4:
        st.metric("Daily limit", selected_campaign.get("daily_limit") or "Sin límite")

        st.markdown("### Acciones de campaña")

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            confirm_cancel_campaign = st.checkbox(
                "Confirmo que quiero cancelar esta campaña",
                value=False,
                key=f"confirm_cancel_campaign_{campaign_id}",
            )

            if st.button(
                "Cancelar campaña",
                type="secondary",
                key=f"cancel_campaign_{campaign_id}",
            ):
                if not confirm_cancel_campaign:
                    st.warning("Debes confirmar la cancelación de la campaña.")
                else:
                    status_code, body = update_campaign(
                        campaign_id=campaign_id,
                        payload={
                            "status": "cancelled",
                        },
                    )

                    if 200 <= status_code < 300:
                        st.success("Campaña cancelada correctamente.")
                        st.json(body)
                        st.rerun()
                    else:
                        st.error("No se pudo cancelar la campaña.")
                        st.json(body)

        with action_col2:
            st.info(
                "Cancelar una campaña conserva sus recipients y eventos. "
                "Esto es mejor que borrarla porque mantiene la trazabilidad."
            )

    st.caption(f"Campaign ID: `{campaign_id}`")

    with st.expander("Variables disponibles para personalización"):
        st.markdown(
        """
        Puedes usar estas variables en el asunto y cuerpo del correo:

        ```jinja2
        {{ first_name }}
        {{ last_name }}
        {{ full_name }}
        {{ email }}

        {{ company }}
        {{ industry }}
        {{ job_title }}
        {{ seniority }}
        {{ department }}
        {{ years_of_experience }}

        {{ country }}
        {{ region }}
        {{ city }}
        {{ location }}

        {{ linkedin_url }}
        {{ employer_domain }}
        {{ employer_website }}
        {{ employer_linkedin }}

        {{ email_lookup_status }}
        {{ skills }}
        {{ source }}
        """)

    with st.expander("Ver templates"):
        st.markdown("**Subject template**")
        st.code(selected_campaign.get("subject_template") or "")

        st.markdown("**Body template**")
        st.code(selected_campaign.get("body_template") or "")

    st.markdown("---")

    summary_status, summary = get_campaign_summary(campaign_id)

    if summary_status != 200:
        st.error("No se pudo cargar el resumen de campaña.")
        st.json(summary)
        return

    st.markdown("### Indicadores de destinatarios")

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    with kpi1:
        st.metric("Total", summary.get("total_recipients", 0))
    with kpi2:
        st.metric("Pending", summary.get("pending", 0))
    with kpi3:
        st.metric("Dry run", summary.get("dry_run", 0))
    with kpi4:
        st.metric("Sent", summary.get("sent", 0))
    with kpi5:
        st.metric("Skipped", summary.get("skipped", 0))
    with kpi6:
        st.metric("Failed", summary.get("failed", 0))

    summary_df = pd.DataFrame(
        [
            {"status": "pending", "count": summary.get("pending", 0)},
            {"status": "dry_run", "count": summary.get("dry_run", 0)},
            {"status": "sent", "count": summary.get("sent", 0)},
            {"status": "skipped", "count": summary.get("skipped", 0)},
            {"status": "failed", "count": summary.get("failed", 0)},
            {"status": "cancelled", "count": summary.get("cancelled", 0)},
        ]
    )

    fig = px.bar(
        summary_df,
        x="status",
        y="count",
        title="Destinatarios por estado",
        text="count",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.markdown("### Ejecutar campaña")

    pending_count = summary.get("pending", 0)

    st.info(
        f"Esta acción procesa destinatarios en estado pending. "
        f"Pendientes actuales: {pending_count}"
    )

    limit_enabled = st.checkbox(
        "Procesar con límite",
        value=False,
        key=f"limit_enabled_{campaign_id}",
    )

    limit = None

    if limit_enabled:
        limit = st.number_input(
            "Límite de recipients a procesar",
            min_value=1,
            max_value=500,
            value=10,
            key=f"dry_run_limit_{campaign_id}",
        )

    confirm_execution = st.checkbox(
        "Confirmo ejecutar dry run para esta campaña",
        value=False,
        key=f"confirm_dry_run_{campaign_id}",
    )

    if st.button(
        "Ejecutar dry run",
        type="primary",
        key=f"execute_dry_run_{campaign_id}",
    ):
        if not confirm_execution:
            st.warning("Debes confirmar la ejecución.")
        else:
            logger.info(
                "Dashboard dry run requested | campaign_id=%s | limit=%s",
                campaign_id,
                limit,
            )

            dry_run_status, dry_run_body = execute_campaign_dry_run(
                campaign_id=campaign_id,
                limit=limit,
            )

            if dry_run_status == 200:
                st.success("Dry run ejecutado correctamente.")
                st.json(dry_run_body)
                st.rerun()
            else:
                st.error("No se pudo ejecutar el dry run.")
                st.json(dry_run_body)

    st.markdown("---")

    st.markdown("### Destinatarios de la campaña")

    recipients_status, recipients = get_campaign_recipients(campaign_id)

    if recipients_status != 200:
        st.error("No se pudieron cargar los destinatarios.")
        st.json(recipients)
    elif not recipients:
        st.warning("Esta campaña todavía no tiene destinatarios asociados.")
    else:
        recipients_df = pd.DataFrame(recipients)

        status_filter_options = ["all"] + sorted(
            recipients_df["status"].dropna().unique().tolist()
        )

        selected_status = st.selectbox(
            "Filtrar por estado",
            options=status_filter_options,
            key=f"recipient_status_filter_{campaign_id}",
        )

        filtered_recipients_df = recipients_df.copy()

        if selected_status != "all":
            filtered_recipients_df = filtered_recipients_df[
                filtered_recipients_df["status"] == selected_status
            ]

        display_cols = [
            col for col in [
                "email",
                "first_name",
                "last_name",
                "company",
                "job_title",
                "consent_status",
                "is_active",
                "status",
                "skip_reason",
                "error_message",
                "personalized_subject",
                "created_at",
            ]
            if col in filtered_recipients_df.columns
        ]

        st.dataframe(
            filtered_recipients_df[display_cols],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Preview de correo personalizado")

    preview_options = {
        f"{row['email']} | {row.get('status')}": row.to_dict()
        for _, row in filtered_recipients_df.iterrows()
    }

    if preview_options:
        selected_preview_label = st.selectbox(
            "Selecciona un destinatario para ver el correo",
            options=list(preview_options.keys()),
            key=f"email_preview_{campaign_id}",
        )

        selected_preview = preview_options[selected_preview_label]

        personalized_subject = selected_preview.get("personalized_subject")
        personalized_body = selected_preview.get("personalized_body")

        if personalized_subject or personalized_body:
            st.markdown("**Subject**")
            st.code(personalized_subject or "")

            st.markdown("**Body**")
            st.code(personalized_body or "")
        else:
            st.info(
                "Este destinatario todavía no tiene correo personalizado generado. "
                "Ejecuta el dry_run para generar el preview."
            )

    st.markdown("---")

    st.markdown("### Trazabilidad reciente")

    events_status, events = get_campaign_events(campaign_id)

    if events_status != 200:
        st.error("No se pudieron cargar los eventos.")
        st.json(events)
        return

    if not events:
        st.warning("Esta campaña todavía no tiene eventos.")
        return

    events_df = pd.DataFrame(events)

    event_counts = (
        events_df["event_type"]
        .value_counts(dropna=False)
        .reset_index()
    )
    event_counts.columns = ["event_type", "count"]

    fig_events = px.pie(
        event_counts,
        names="event_type",
        values="count",
        title="Eventos por tipo",
    )

    st.plotly_chart(fig_events, use_container_width=True)

    event_display_cols = [
        col for col in [
            "event_type",
            "provider",
            "provider_message_id",
            "error_message",
            "campaign_recipient_id",
            "created_at",
            "metadata_json",
        ]
        if col in events_df.columns
    ]

    st.dataframe(
        events_df[event_display_cols],
        use_container_width=True,
        hide_index=True,
    )
    