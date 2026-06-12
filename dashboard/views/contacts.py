import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import (
    block_contact,
    create_contact,
    get_contact_eligibility,
    list_contacts,
    unsubscribe_contact,
    update_contact,
)
from dashboard.ui.components import render_section_header


logger = logging.getLogger(__name__)


def render_contacts_kpis(contacts_df: pd.DataFrame) -> None:
    total_contacts = len(contacts_df)

    consented = int(
        (
            (contacts_df["consent_status"] == "consented")
            & (contacts_df["is_active"] == True)
        ).sum()
    )

    unknown = int((contacts_df["consent_status"] == "unknown").sum())
    unsubscribed = int((contacts_df["consent_status"] == "unsubscribed").sum())
    bounced = int((contacts_df["consent_status"] == "bounced").sum())
    blocked = int((contacts_df["consent_status"] == "blocked").sum())

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("Total", total_contacts)
    with col2:
        st.metric("Contactables", consented)
    with col3:
        st.metric("Unknown", unknown)
    with col4:
        st.metric("Unsubscribed", unsubscribed)
    with col5:
        st.metric("Bounced", bounced)
    with col6:
        st.metric("Blocked", blocked)


def render_create_contact_form() -> None:
    with st.expander("➕ Crear contacto", expanded=False):
        with st.form("advanced_create_contact_form"):
            col1, col2 = st.columns(2)

            with col1:
                email = st.text_input("Email")
                first_name = st.text_input("Nombre")
                last_name = st.text_input("Apellido")

            with col2:
                company = st.text_input("Empresa")
                job_title = st.text_input("Cargo")
                source = st.selectbox(
                    "Fuente",
                    options=["manual", "rocketreach", "csv", "api"],
                    index=0,
                )

            consent_status = st.selectbox(
                "Estado de consentimiento",
                options=["unknown", "consented", "unsubscribed", "bounced", "blocked"],
                index=0,
            )

            notes = st.text_area("Notas")

            submitted = st.form_submit_button("Crear contacto")

        if submitted:
            payload = {
                "email": email,
                "first_name": first_name or None,
                "last_name": last_name or None,
                "company": company or None,
                "job_title": job_title or None,
                "source": source,
                "consent_status": consent_status,
                "notes": notes or None,
            }

            status_code, body = create_contact(payload)

            if 200 <= status_code < 300:
                st.success("Contacto creado correctamente.")
                st.json(body)
                st.rerun()
            else:
                st.error("No se pudo crear el contacto.")
                st.json(body)


def render_contacts_page() -> None:
    render_section_header(
        "Contactos",
        "Consulta, filtra y gestiona contactos antes de asociarlos a campañas.",
    )

    render_create_contact_form()

    st.markdown("---")

    status_code, contacts = list_contacts(limit=1000, offset=0)

    if status_code != 200:
        st.error("No se pudieron cargar los contactos.")
        st.json(contacts)
        return

    if not contacts:
        st.warning("No hay contactos creados todavía.")
        return

    contacts_df = pd.DataFrame(contacts)

    render_contacts_kpis(contacts_df)

    st.markdown("---")

    st.markdown("### Distribución por consentimiento")

    consent_counts = (
        contacts_df["consent_status"]
        .value_counts(dropna=False)
        .reset_index()
    )
    consent_counts.columns = ["consent_status", "count"]

    fig = px.bar(
        consent_counts,
        x="consent_status",
        y="count",
        text="count",
        title="Contactos por estado de consentimiento",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.markdown("### Filtros")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        consent_options = ["all"] + sorted(
            contacts_df["consent_status"].dropna().unique().tolist()
        )
        selected_consent = st.selectbox(
            "Consentimiento",
            options=consent_options,
        )

    with filter_col2:
        source_options = ["all"] + sorted(
            contacts_df["source"].fillna("unknown").unique().tolist()
        )
        selected_source = st.selectbox(
            "Fuente",
            options=source_options,
        )

    with filter_col3:
        active_filter = st.selectbox(
            "Activo",
            options=["all", "active", "inactive"],
        )

    with filter_col4:
        text_search = st.text_input(
            "Buscar texto",
            placeholder="email, empresa, nombre, cargo...",
        )

    filtered_df = contacts_df.copy()

    if selected_consent != "all":
        filtered_df = filtered_df[
            filtered_df["consent_status"] == selected_consent
        ]

    if selected_source != "all":
        filtered_df = filtered_df[
            filtered_df["source"].fillna("unknown") == selected_source
        ]

    if active_filter == "active":
        filtered_df = filtered_df[filtered_df["is_active"] == True]

    if active_filter == "inactive":
        filtered_df = filtered_df[filtered_df["is_active"] == False]

    if text_search.strip():
        search = text_search.strip().lower()

        searchable_cols = [
            "email",
            "first_name",
            "last_name",
            "company",
            "industry",
            "country",
            "region",
            "city",
            "location",
            "seniority",
            "department",
            "skills",
            "job_title",
        ]

        mask = False

        for col in searchable_cols:
            if col in filtered_df.columns:
                mask = mask | filtered_df[col].fillna("").str.lower().str.contains(search)

        filtered_df = filtered_df[mask]

    st.caption(f"Contactos filtrados: {len(filtered_df)}")

    display_cols = [
        col for col in [
            "id",
            "email",
            "first_name",
            "last_name",
            "company",
            "industry",
            "country",
            "region",
            "city",
            "location",
            "seniority",
            "department",
            "years_of_experience",
            "linkedin_url",
            "employer_domain",
            "job_title",
            "source",
            "consent_status",
            "is_active",
            "created_at",
        ]
        if col in filtered_df.columns
    ]

    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    st.markdown("### Acciones sobre contacto")

    if filtered_df.empty:
        st.info("No hay contactos disponibles con los filtros actuales.")
        return

    contact_options = {
        f"{row['email']} | {row.get('first_name') or ''} {row.get('last_name') or ''} | {row.get('company') or ''} | {row['id']}": row["id"]
        for _, row in filtered_df.iterrows()
    }

    selected_contact_label = st.selectbox(
        "Selecciona contacto",
        options=list(contact_options.keys()),
    )

    selected_contact_id = contact_options[selected_contact_label]

    selected_contact = filtered_df[
        filtered_df["id"] == selected_contact_id
    ].iloc[0].to_dict()

    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        st.metric("Consentimiento", selected_contact.get("consent_status"))
    with col_b:
        st.metric("Activo", str(selected_contact.get("is_active")))
    with col_c:
        st.metric("Fuente", selected_contact.get("source") or "N/A")
    with col_d:
        st.metric("Empresa", selected_contact.get("company") or "N/A")

    with st.expander("Ver detalle del contacto"):
        st.json(selected_contact)

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button("Validar elegibilidad"):
            eligibility_status, eligibility_body = get_contact_eligibility(
                selected_contact_id
            )

            if eligibility_status == 200:
                if eligibility_body.get("allowed_to_send"):
                    st.success("El contacto puede recibir correos.")
                else:
                    st.warning("El contacto NO puede recibir correos.")

                st.json(eligibility_body)
            else:
                st.error("No se pudo validar elegibilidad.")
                st.json(eligibility_body)

    with action_col2:
        confirm_unsubscribe = st.checkbox(
            "Confirmar baja",
            key=f"confirm_unsubscribe_{selected_contact_id}",
        )

        if st.button("Dar de baja"):
            if not confirm_unsubscribe:
                st.warning("Debes confirmar la baja.")
            else:
                status, body = unsubscribe_contact(selected_contact_id)

                if 200 <= status < 300:
                    st.success("Contacto dado de baja.")
                    st.json(body)
                    st.rerun()
                else:
                    st.error("No se pudo dar de baja.")
                    st.json(body)

    with action_col3:
        confirm_block = st.checkbox(
            "Confirmar bloqueo",
            key=f"confirm_block_{selected_contact_id}",
        )

        if st.button("Bloquear"):
            if not confirm_block:
                st.warning("Debes confirmar el bloqueo.")
            else:
                status, body = block_contact(selected_contact_id)

                if 200 <= status < 300:
                    st.success("Contacto bloqueado.")
                    st.json(body)
                    st.rerun()
                else:
                    st.error("No se pudo bloquear.")
                    st.json(body)

    st.markdown("---")

    st.markdown("### Edición rápida")

    with st.form(f"edit_contact_form_{selected_contact_id}"):
        edit_col1, edit_col2 = st.columns(2)

        with edit_col1:
            new_first_name = st.text_input(
                "Nombre",
                value=selected_contact.get("first_name") or "",
            )
            new_last_name = st.text_input(
                "Apellido",
                value=selected_contact.get("last_name") or "",
            )
            new_company = st.text_input(
                "Empresa",
                value=selected_contact.get("company") or "",
            )

        with edit_col2:
            new_job_title = st.text_input(
                "Cargo",
                value=selected_contact.get("job_title") or "",
            )
            new_source = st.text_input(
                "Fuente",
                value=selected_contact.get("source") or "",
            )
            new_consent_status = st.selectbox(
                "Consentimiento",
                options=["unknown", "consented", "unsubscribed", "bounced", "blocked"],
                index=["unknown", "consented", "unsubscribed", "bounced", "blocked"].index(
                    selected_contact.get("consent_status", "unknown")
                ),
            )

        submitted_update = st.form_submit_button("Guardar cambios")

    if submitted_update:
        payload = {
            "first_name": new_first_name or None,
            "last_name": new_last_name or None,
            "company": new_company or None,
            "job_title": new_job_title or None,
            "source": new_source or None,
            "consent_status": new_consent_status,
        }

        status, body = update_contact(
            contact_id=selected_contact_id,
            payload=payload,
        )

        if 200 <= status < 300:
            st.success("Contacto actualizado correctamente.")
            st.json(body)
            st.rerun()
        else:
            st.error("No se pudo actualizar el contacto.")
            st.json(body)