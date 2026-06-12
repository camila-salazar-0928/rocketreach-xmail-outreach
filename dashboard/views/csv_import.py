import logging
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.api_client import create_contact
from dashboard.ui.components import render_section_header


logger = logging.getLogger(__name__)


def clean_cell_value(value: Any) -> str | None:
    if value is None:
        return None

    if pd.isna(value):
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    return cleaned


def render_csv_import_page() -> None:
    render_section_header(
        "Importar CSV",
        "Carga contactos desde un archivo CSV exportado desde RocketReach u otra fuente.",
    )

    uploaded_file = st.file_uploader(
        "Selecciona archivo CSV",
        type=["csv"],
    )

    if uploaded_file is None:
        st.info("Sube un archivo CSV para empezar.")
        return

    try:
        csv_df = pd.read_csv(uploaded_file)
    except Exception as error:
        logger.exception("CSV could not be read")
        st.error("No se pudo leer el CSV.")
        st.exception(error)
        return

    if csv_df.empty:
        st.warning("El CSV está vacío.")
        return

    st.success(f"CSV cargado correctamente. Filas encontradas: {len(csv_df)}")

    st.markdown("### Preview del CSV")

    st.dataframe(
        csv_df.head(20),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### Mapeo básico de columnas")

    csv_columns = csv_df.columns.tolist()
    column_options = ["No mapear"] + csv_columns

    email_col = st.selectbox(
        "Columna de email",
        options=column_options,
    )

    first_name_col = st.selectbox(
        "Columna de nombre",
        options=column_options,
    )

    last_name_col = st.selectbox(
        "Columna de apellido",
        options=column_options,
    )

    company_col = st.selectbox(
        "Columna de empresa",
        options=column_options,
    )

    job_title_col = st.selectbox(
        "Columna de cargo",
        options=column_options,
    )

    default_source = st.selectbox(
        "Fuente",
        options=["rocketreach", "csv", "manual", "api"],
        index=0,
    )

    default_consent_status = st.selectbox(
        "Consentimiento por defecto",
        options=["unknown", "consented", "unsubscribed", "bounced", "blocked"],
        index=0,
    )

    max_rows_to_import = st.number_input(
        "Máximo de filas a importar",
        min_value=1,
        max_value=min(5000, len(csv_df)),
        value=min(100, len(csv_df)),
    )

    if email_col == "No mapear":
        st.error("Debes seleccionar una columna de email.")
        return

    st.markdown("---")
    st.markdown("### Preview normalizado")

    preview_payloads = []

    for _, row in csv_df.head(20).iterrows():
        payload = {
            "email": clean_cell_value(row.get(email_col)),
            "first_name": clean_cell_value(row.get(first_name_col)) if first_name_col != "No mapear" else None,
            "last_name": clean_cell_value(row.get(last_name_col)) if last_name_col != "No mapear" else None,
            "company": clean_cell_value(row.get(company_col)) if company_col != "No mapear" else None,
            "job_title": clean_cell_value(row.get(job_title_col)) if job_title_col != "No mapear" else None,
            "source": default_source,
            "consent_status": default_consent_status,
        }

        if payload["email"]:
            preview_payloads.append(payload)

    if preview_payloads:
        st.dataframe(
            pd.DataFrame(preview_payloads),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No se detectaron emails válidos en el preview.")

    st.markdown("---")
    st.markdown("### Ejecutar importación")

    confirm_import = st.checkbox(
        "Confirmo que quiero importar estos contactos",
        value=False,
    )

    if st.button("Importar contactos", type="primary"):
        if not confirm_import:
            st.warning("Debes confirmar la importación.")
            return

        imported = 0
        skipped = 0
        failed = 0
        errors = []

        rows_to_import = csv_df.head(int(max_rows_to_import))

        progress_bar = st.progress(0)

        for index, row in rows_to_import.iterrows():
            payload = {
                "email": clean_cell_value(row.get(email_col)),
                "first_name": clean_cell_value(row.get(first_name_col)) if first_name_col != "No mapear" else None,
                "last_name": clean_cell_value(row.get(last_name_col)) if last_name_col != "No mapear" else None,
                "company": clean_cell_value(row.get(company_col)) if company_col != "No mapear" else None,
                "job_title": clean_cell_value(row.get(job_title_col)) if job_title_col != "No mapear" else None,
                "source": default_source,
                "consent_status": default_consent_status,
            }

            if not payload["email"]:
                skipped += 1
                continue

            status_code, body = create_contact(payload)

            if 200 <= status_code < 300:
                imported += 1
            else:
                failed += 1
                errors.append(
                    {
                        "row_index": int(index),
                        "email": payload["email"],
                        "status_code": status_code,
                        "error": body,
                    }
                )

            processed = imported + skipped + failed
            progress_bar.progress(min(processed / len(rows_to_import), 1.0))

        st.markdown("### Resultado")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Importados", imported)

        with col2:
            st.metric("Omitidos", skipped)

        with col3:
            st.metric("Fallidos", failed)

        if errors:
            st.error("Algunos contactos no se pudieron importar.")
            st.dataframe(
                pd.DataFrame(errors),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("Importación finalizada sin errores.")