import logging

import pandas as pd
import streamlit as st

from dashboard.api_client import (
    add_contacts_to_campaign_bulk,
    list_campaigns,
    list_contacts,
)
from dashboard.ui.components import render_section_header


logger = logging.getLogger(__name__)


def build_contact_label(contact: dict) -> str:
    email = contact.get("email", "")
    first_name = contact.get("first_name") or ""
    last_name = contact.get("last_name") or ""
    company = contact.get("company") or ""
    industry = contact.get("industry") or ""
    country = contact.get("country") or ""
    job_title = contact.get("job_title") or ""
    consent_status = contact.get("consent_status") or ""

    full_name = f"{first_name} {last_name}".strip()

    label_parts = [
        email,
        full_name,
        job_title,
        company,
        industry,
        country,
        consent_status,
    ]

    return " | ".join(
        str(part)
        for part in label_parts
        if part
    )


def render_bulk_assignment_page() -> None:
    render_section_header(
        "Asignación masiva",
        "Filtra contactos, selecciona múltiples destinatarios y agrégalos a una campaña.",
    )

    campaigns_status, campaigns_body = list_campaigns(limit=100, offset=0)
    contacts_status, contacts_body = list_contacts(limit=500, offset=0)

    if campaigns_status != 200:
        st.error("No se pudieron cargar las campañas.")
        st.json(campaigns_body)
        return

    if contacts_status != 200:
        st.error("No se pudieron cargar los contactos.")

        if isinstance(contacts_body, dict) and "detail" in contacts_body:
            st.warning("Detalle del error:")
            st.json(contacts_body["detail"])
        else:
            st.json(contacts_body)

        st.info(
            "Revisa que el endpoint /contacts permita el límite solicitado. "
            "Para asociación masiva recomendamos permitir hasta 1000 contactos por consulta."
        )
        return

    if not campaigns_body:
        st.warning("No hay campañas creadas.")
        return

    if not contacts_body:
        st.warning("No hay contactos creados.")
        return

    campaigns_df = pd.DataFrame(campaigns_body)
    contacts_df = pd.DataFrame(contacts_body)

    st.markdown("### 1. Selecciona campaña")

    campaign_options = {
        f"{row['name']} | {row['status']} | dry_run={row['dry_run']} | {row['id']}": row["id"]
        for _, row in campaigns_df.iterrows()
    }

    selected_campaign_label = st.selectbox(
        "Campaña destino",
        options=list(campaign_options.keys()),
    )

    selected_campaign_id = campaign_options[selected_campaign_label]

    selected_campaign = campaigns_df[
        campaigns_df["id"] == selected_campaign_id
    ].iloc[0].to_dict()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Estado", selected_campaign.get("status"))
    with col2:
        st.metric("Dry run", str(selected_campaign.get("dry_run")))
    with col3:
        st.metric("Max recipients", selected_campaign.get("max_recipients") or "Sin límite")
    with col4:
        st.metric("Daily limit", selected_campaign.get("daily_limit") or "Sin límite")

    st.markdown("---")
    st.markdown("### 2. Segmenta contactos")

    st.caption(
        "Filtra la base importada para crear audiencias más específicas antes de asociarlas a una campaña."
    )

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        consent_options = ["all"] + sorted(
            contacts_df["consent_status"].dropna().unique().tolist()
        )
        selected_consent = st.selectbox(
            "Consentimiento",
            options=consent_options,
            index=consent_options.index("consented") if "consented" in consent_options else 0,
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
            options=["active", "all", "inactive"],
            index=0,
        )

    segment_col1, segment_col2, segment_col3 = st.columns(3)

    with segment_col1:
        selected_countries = st.multiselect(
            "País",
            options=get_safe_unique_values(contacts_df, "country"),
        )

    with segment_col2:
        selected_industries = st.multiselect(
            "Industria",
            options=get_safe_unique_values(contacts_df, "industry"),
        )

    with segment_col3:
        selected_departments = st.multiselect(
            "Departamento",
            options=get_safe_unique_values(contacts_df, "department"),
        )

    segment_col4, segment_col5, segment_col6 = st.columns(3)

    with segment_col4:
        selected_seniorities = st.multiselect(
            "Seniority",
            options=get_safe_unique_values(contacts_df, "seniority"),
        )

    with segment_col5:
        company_search = st.text_input(
            "Empresa contiene",
            placeholder="Ej: Globant, Mercado Libre, Cuesta Blanca...",
        )

    with segment_col6:
        title_search = st.text_input(
            "Cargo contiene",
            placeholder="Ej: CEO, marketing, product, data...",
        )

    text_search = st.text_input(
        "Búsqueda general",
        placeholder="Buscar por email, nombre, empresa, industria, país, cargo...",
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

    filtered_df = apply_multiselect_filter(
        df=filtered_df,
        column="country",
        selected_values=selected_countries,
    )

    filtered_df = apply_multiselect_filter(
        df=filtered_df,
        column="industry",
        selected_values=selected_industries,
    )

    filtered_df = apply_multiselect_filter(
        df=filtered_df,
        column="department",
        selected_values=selected_departments,
    )

    filtered_df = apply_multiselect_filter(
        df=filtered_df,
        column="seniority",
        selected_values=selected_seniorities,
    )

    filtered_df = apply_text_contains_filter(
        df=filtered_df,
        column="company",
        text_value=company_search,
    )

    filtered_df = apply_text_contains_filter(
        df=filtered_df,
        column="job_title",
        text_value=title_search,
    )

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
            "job_title",
            "seniority",
            "department",
            "skills",
        ]

        mask = pd.Series(False, index=filtered_df.index)

        for col in searchable_cols:
            if col in filtered_df.columns:
                mask = mask | (
                    filtered_df[col]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(search)
                )

        filtered_df = filtered_df[mask]

    st.caption(f"Contactos filtrados: {len(filtered_df)}")

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric("Contactos filtrados", len(filtered_df))

    with metric_col2:
        contactable_count = 0

        if not filtered_df.empty:
            contactable_count = int(
                (
                    (filtered_df["consent_status"] == "consented")
                    & (filtered_df["is_active"] == True)
                ).sum()
            )

        st.metric("Contactables", contactable_count)

    with metric_col3:
        unique_companies = (
            filtered_df["company"].dropna().nunique()
            if "company" in filtered_df.columns
            else 0
        )
        st.metric("Empresas", unique_companies)

    with metric_col4:
        unique_countries = (
            filtered_df["country"].dropna().nunique()
            if "country" in filtered_df.columns
            else 0
        )
        st.metric("Países", unique_countries)
        
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
            "job_title",
            "seniority",
            "department",
            "years_of_experience",
            "source",
            "consent_status",
            "is_active",
        ]
        if col in filtered_df.columns
    ]

    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### 3. Selecciona contactos")

    contact_label_to_id = {
        build_contact_label(row.to_dict()): row["id"]
        for _, row in filtered_df.iterrows()
    }

    select_all_filtered = st.checkbox(
        "Seleccionar todos los contactos filtrados",
        value=False,
    )

    if select_all_filtered:
        selected_contact_ids = filtered_df["id"].dropna().astype(str).tolist()
        selected_contact_labels = []
    else:
        selected_contact_labels = st.multiselect(
            "Contactos a asociar",
            options=list(contact_label_to_id.keys()),
            help="Puedes seleccionar múltiples contactos filtrados.",
        )

        selected_contact_ids = [
            contact_label_to_id[label]
            for label in selected_contact_labels
        ]

    st.metric("Seleccionados", len(selected_contact_ids))

    if len(selected_contact_ids) > 100:
        st.warning(
            "Estás seleccionando más de 100 contactos. "
            "Para pruebas, te recomiendo empezar con pocos contactos y dry_run."
        )


    if selected_contact_ids:
        selected_preview = filtered_df[
            filtered_df["id"].isin(selected_contact_ids)
        ][display_cols]

        st.dataframe(
            selected_preview,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    st.markdown("### 4. Ejecutar asociación masiva")

    confirm = st.checkbox(
        "Confirmo que quiero asociar estos contactos a la campaña seleccionada",
        value=False,
    )

    if st.button("Agregar contactos seleccionados", type="primary"):
        if not selected_contact_ids:
            st.warning("Selecciona al menos un contacto.")
            return

        if not confirm:
            st.warning("Debes confirmar la asociación masiva.")
            return

        logger.info(
            "Bulk assignment requested from dashboard | campaign_id=%s | selected_contacts=%s",
            selected_campaign_id,
            len(selected_contact_ids),
        )

        status_code, body = add_contacts_to_campaign_bulk(
            campaign_id=selected_campaign_id,
            contact_ids=selected_contact_ids,
        )

        if 200 <= status_code < 300:
            st.success("Contactos asociados correctamente.")

            result_col1, result_col2, result_col3, result_col4 = st.columns(4)

            with result_col1:
                st.metric("Solicitados", body.get("total_requested"))
            with result_col2:
                st.metric("Procesados", body.get("total_processed"))
            with result_col3:
                st.metric("Pending", body.get("pending"))
            with result_col4:
                st.metric("Skipped", body.get("skipped"))

            st.json(body)

        else:
            st.error(f"Error al asociar contactos. Status: {status_code}")
            st.json(body)


def get_safe_unique_values(
    df: pd.DataFrame,
    column: str,
    max_values: int = 200,
) -> list[str]:
    if column not in df.columns:
        return []

    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    values = values[values != ""]

    return sorted(values.unique().tolist())[:max_values]


def apply_multiselect_filter(
    df: pd.DataFrame,
    column: str,
    selected_values: list[str],
) -> pd.DataFrame:
    if not selected_values or column not in df.columns:
        return df

    return df[
        df[column]
        .fillna("")
        .astype(str)
        .isin(selected_values)
    ]


def apply_text_contains_filter(
    df: pd.DataFrame,
    column: str,
    text_value: str,
) -> pd.DataFrame:
    if not text_value.strip() or column not in df.columns:
        return df

    return df[
        df[column]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(text_value.strip().lower())
    ]


