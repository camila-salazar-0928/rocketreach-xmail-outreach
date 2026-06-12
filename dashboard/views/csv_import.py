import logging
from io import StringIO
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.api_client import (
    add_contacts_to_campaign_bulk,
    create_contact,
    list_campaigns,
)
from dashboard.ui.components import render_section_header


logger = logging.getLogger(__name__)


CONTACT_FIELDS = {
    "email": "Email",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "company": "Empresa",
    "industry": "Industria",
    "country": "País",
    "region": "Región",
    "city": "Ciudad",
    "location": "Ubicación",
    "job_title": "Cargo",
    "seniority": "Seniority",
    "department": "Departamento",
    "years_of_experience": "Años de experiencia",
    "linkedin_url": "LinkedIn",
    "employer_domain": "Dominio empresa",
    "employer_website": "Website empresa",
    "employer_linkedin": "LinkedIn empresa",
    "email_lookup_status": "Estado email",
    "skills": "Skills",
    "source": "Fuente",
    "notes": "Notas",
}


COLUMN_SUGGESTIONS = {
    "email": [
        "Recommended Email",
        "Recommended Work Email",
        "Recommended Personal Email",
        "A Emails",
        "A- Emails",
        "B Emails",
        "email",
        "Email",
        "work_email",
        "Work Email",
        "personal_email",
        "Personal Email",
        "recommended_email",
    ],
    "first_name": [
        "First Name",
        "first_name",
        "firstname",
        "name_first",
    ],
    "last_name": [
        "Last Name",
        "last_name",
        "lastname",
        "name_last",
    ],
    "company": [
        "Employer",
        "Company",
        "company",
        "current_employer",
        "Current Employer",
        "organization",
        "Organization",
    ],

    "industry": [
        "Employer Primary Industry",
        "Primary Industry",
        "Industry",
        "industry",
        "Company Industry",
        "Employer Industry",
    ],

    "country": [
        "Country",
        "country",
        "País",
        "Pais",
    ],
    "region": [
        "Region",
        "region",
        "State",
        "Provincia",
        "Departamento",
    ],
    "city": [
        "City",
        "city",
        "Ciudad",
    ],
    "location": [
        "Location",
        "location",
        "Ubicación",
        "Ubicacion",
    ],
    "linkedin_url": [
        "LinkedIn",
        "LinkedIn URL",
        "linkedin",
        "linkedin_url",
    ],
    "seniority": [
        "Seniority",
        "seniority",
    ],
    "department": [
        "Department",
        "department",
    ],
    "years_of_experience": [
        "Years of Experience",
        "years_of_experience",
        "Experience",
    ],
    "employer_domain": [
        "Employer Domain",
        "Company Domain",
        "Domain",
    ],
    "employer_website": [
        "Employer Website",
        "Company Website",
        "Website",
    ],
    "employer_linkedin": [
        "Employer LinkedIn",
        "Company LinkedIn",
    ],
    "email_lookup_status": [
        "Email Lookup Status",
        "email_lookup_status",
    ],
    "skills": [
        "Skills & Endorsements",
        "Skills",
        "skills",
    ],

    "job_title": [
        "Title",
        "Job Title",
        "job_title",
        "title",
        "current_title",
        "Current Title",
    ],
    "source": [
        "source",
        "Source",
    ],
    "notes": [
        "LinkedIn",
        "linkedin_url",
        "LinkedIn URL",
        "linkedin",
        "Linkedin",
        "Notes",
        "notes",
    ],
}


ROCKETREACH_EMAIL_PRIORITY_COLUMNS = [
    "Recommended Email",
    "Recommended Work Email",
    "Recommended Personal Email",
    "A Emails",
    "A- Emails",
    "B Emails",
]


ROCKETREACH_NOTES_COLUMNS = [
    "Profile ID",
    "Email Lookup Status",
    "Lookup Time",
    "LinkedIn",
    "Employer",
    "Employer Primary Industry",
    "Employer Domain",
    "Employer Website",
    "Employer LinkedIn",
    "Location",
    "City",
    "Postal Code",
    "Region",
    "Country",
    "Seniority",
    "Department",
    "Years of Experience",
    "Tags",
    "Notes",
    "Job1 Employer",
    "Job1 Title",
    "Job1 Start",
    "Job1 End",
    "Job2 Employer",
    "Job2 Title",
    "Job2 Start",
    "Job2 End",
]


def clean_cell_value(value: Any) -> str | None:
    if value is None:
        return None

    if pd.isna(value):
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    return cleaned


def read_csv_file(uploaded_file) -> pd.DataFrame:
    """
    Read a standard CSV or a RocketReach CSV where each row is wrapped
    as one quoted comma-separated string.
    """
    raw_text = uploaded_file.getvalue().decode("utf-8-sig", errors="replace")

    normal_df = pd.read_csv(StringIO(raw_text))

    if len(normal_df.columns) > 1 and not normal_df.empty:
        first_col = normal_df.columns[0]
        first_value = normal_df.iloc[0][first_col]

        if isinstance(first_value, str) and first_value.count(",") > 5:
            logger.info("Detected RocketReach quoted-row CSV. Normalizing rows.")

            normalized_lines = []

            for line in raw_text.splitlines():
                cleaned_line = line.strip()

                if cleaned_line.startswith('"') and cleaned_line.endswith('"'):
                    cleaned_line = cleaned_line[1:-1]
                    cleaned_line = cleaned_line.replace('""', '"')

                normalized_lines.append(cleaned_line)

            normalized_text = "\n".join(normalized_lines)

            return pd.read_csv(StringIO(normalized_text))

    return normal_df


def split_possible_emails(value: Any) -> list[str]:
    cleaned = clean_cell_value(value)

    if not cleaned:
        return []

    separators = [",", ";", "|"]

    emails = [cleaned]

    for separator in separators:
        new_emails = []

        for email in emails:
            new_emails.extend(email.split(separator))

        emails = new_emails

    return [
        email.strip()
        for email in emails
        if "@" in email.strip()
    ]


def get_best_email_from_row(
    row: pd.Series,
    mapping: dict[str, str],
) -> str | None:
    mapped_email_column = mapping.get("email")

    if mapped_email_column and mapped_email_column != "No mapear":
        mapped_email = clean_cell_value(row.get(mapped_email_column))

        if mapped_email and "@" in mapped_email:
            return mapped_email

    for column in ROCKETREACH_EMAIL_PRIORITY_COLUMNS:
        if column not in row.index:
            continue

        possible_emails = split_possible_emails(row.get(column))

        if possible_emails:
            return possible_emails[0]

    return None


def build_notes_from_row(
    row: pd.Series,
    mapping: dict[str, str],
) -> str | None:
    notes_parts = []

    mapped_notes_column = mapping.get("notes")

    if mapped_notes_column and mapped_notes_column != "No mapear":
        mapped_notes = clean_cell_value(row.get(mapped_notes_column))

        if mapped_notes:
            notes_parts.append(mapped_notes)

    for column in ROCKETREACH_NOTES_COLUMNS:
        if column not in row.index:
            continue

        value = clean_cell_value(row.get(column))

        if value:
            notes_parts.append(f"{column}: {value}")

    if not notes_parts:
        return None

    return " | ".join(notes_parts)


def guess_column(field_name: str, columns: list[str]) -> str:
    suggestions = COLUMN_SUGGESTIONS.get(field_name, [])

    for suggestion in suggestions:
        if suggestion in columns:
            return suggestion

    lower_columns = {column.lower(): column for column in columns}

    for suggestion in suggestions:
        suggestion_lower = suggestion.lower()

        if suggestion_lower in lower_columns:
            return lower_columns[suggestion_lower]

    return "No mapear"


def build_contact_payload(
    row: pd.Series,
    mapping: dict[str, str],
    default_source: str,
    default_consent_status: str,
) -> dict[str, Any] | None:
    email = get_best_email_from_row(
        row=row,
        mapping=mapping,
    )

    if not email:
        return None

    payload: dict[str, Any] = {
        "email": email,
        "first_name": None,
        "last_name": None,
        "company": None,
        "job_title": None,
        "source": default_source,
        "consent_status": default_consent_status,
        "notes": build_notes_from_row(
            row=row,
            mapping=mapping,
        ),
    }

    for contact_field in [
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
        "years_of_experience",
        "linkedin_url",
        "employer_domain",
        "employer_website",
        "employer_linkedin",
        "email_lookup_status",
        "skills",
        "source",
    ]:
        csv_column = mapping.get(contact_field)

        if not csv_column or csv_column == "No mapear":
            continue

        payload[contact_field] = clean_cell_value(row.get(csv_column))

    if not payload.get("source"):
        payload["source"] = default_source

    return payload


def render_campaign_assignment_selector() -> tuple[bool, str | None]:
    st.markdown("### Asociación automática a campaña")

    st.caption(
        "Opcional: después de importar los contactos, puedes asociarlos automáticamente "
        "a una campaña existente."
    )

    associate_to_campaign = st.checkbox(
        "Asociar contactos importados a una campaña",
        value=False,
    )

    if not associate_to_campaign:
        return False, None

    campaigns_status, campaigns_body = list_campaigns(limit=100, offset=0)

    if campaigns_status != 200:
        st.error("No se pudieron cargar las campañas.")
        st.json(campaigns_body)
        return False, None

    if not campaigns_body:
        st.warning("No hay campañas creadas todavía.")
        return False, None

    campaigns_df = pd.DataFrame(campaigns_body)

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

    return True, selected_campaign_id


def render_csv_import_page() -> None:
    render_section_header(
        "Importar CSV",
        "Carga contactos desde un archivo CSV exportado desde RocketReach u otra fuente.",
    )

    st.info(
        "Para contactos exportados desde RocketReach, lo más seguro es importarlos con "
        "`consent_status = unknown`. Si los asocias a una campaña, quedarán como skipped "
        "hasta que los marques como consented."
    )

    uploaded_file = st.file_uploader(
        "Selecciona archivo CSV",
        type=["csv"],
    )

    if uploaded_file is None:
        st.warning("Sube un archivo CSV para empezar.")
        return

    try:
        csv_df = read_csv_file(uploaded_file)
    except Exception as error:
        logger.exception("CSV could not be read")
        st.error("No se pudo leer el CSV.")
        st.exception(error)
        return
    
    if csv_df.empty:
        st.warning("El CSV está vacío.")
        return

    st.success(f"CSV cargado correctamente. Filas encontradas: {len(csv_df)}")

    st.markdown("### Preview del archivo")

    st.dataframe(
        csv_df.head(20),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### Mapeo de columnas")

    csv_columns = csv_df.columns.tolist()
    column_options = ["No mapear"] + csv_columns

    mapping: dict[str, str] = {}

    col1, col2 = st.columns(2)

    field_items = list(CONTACT_FIELDS.items())

    for index, (field_name, field_label) in enumerate(field_items):
        default_column = guess_column(field_name, csv_columns)

        default_index = (
            column_options.index(default_column)
            if default_column in column_options
            else 0
        )

        target_col = col1 if index % 2 == 0 else col2

        with target_col:
            mapping[field_name] = st.selectbox(
                f"{field_label} → columna CSV",
                options=column_options,
                index=default_index,
                key=f"csv_mapping_{field_name}",
            )

    st.markdown("---")
    st.markdown("### Configuración de importación")

    config_col1, config_col2, config_col3 = st.columns(3)

    with config_col1:
        default_source = st.selectbox(
            "Fuente por defecto",
            options=["rocketreach", "csv", "manual", "api"],
            index=0,
        )

    with config_col2:
        default_consent_status = st.selectbox(
            "Consentimiento por defecto",
            options=["unknown", "consented", "unsubscribed", "bounced", "blocked"],
            index=0,
        )

    with config_col3:
        max_rows_to_import = st.number_input(
            "Máximo de filas a importar",
            min_value=1,
            max_value=min(5000, len(csv_df)),
            value=min(100, len(csv_df)),
        )

    email_mapping = mapping.get("email")

    if not email_mapping or email_mapping == "No mapear":
        st.error("Debes mapear una columna para Email antes de importar.")
        return

    st.markdown("---")
    st.markdown("### Preview de contactos normalizados")

    preview_rows = []

    for _, row in csv_df.head(20).iterrows():
        payload = build_contact_payload(
            row=row,
            mapping=mapping,
            default_source=default_source,
            default_consent_status=default_consent_status,
        )

        if payload:
            preview_rows.append(payload)

    if preview_rows:
        preview_df = pd.DataFrame(preview_rows)

        priority_preview_cols = [
            col for col in [
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
                "years_of_experience",
                "linkedin_url",
                "employer_domain",
                "employer_website",
                "email_lookup_status",
                "source",
                "consent_status",
            ]
            if col in preview_df.columns
        ]

        st.dataframe(
            preview_df[priority_preview_cols],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No se pudieron construir contactos válidos en el preview.")

    st.markdown("---")

    associate_to_campaign, selected_campaign_id = render_campaign_assignment_selector()

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

        rows_to_import = csv_df.head(int(max_rows_to_import))

        imported = 0
        skipped = 0
        failed = 0

        errors: list[dict[str, Any]] = []
        imported_contacts: list[dict[str, Any]] = []
        imported_contact_ids: list[str] = []

        progress_bar = st.progress(0)
        status_placeholder = st.empty()

        total_rows = len(rows_to_import)

        for position, (index, row) in enumerate(rows_to_import.iterrows(), start=1):
            payload = build_contact_payload(
                row=row,
                mapping=mapping,
                default_source=default_source,
                default_consent_status=default_consent_status,
            )

            if payload is None:
                skipped += 1
                progress_bar.progress(min(position / total_rows, 1.0))
                continue

            status_code, body = create_contact(payload)

            if 200 <= status_code < 300:
                imported += 1
                imported_contacts.append(body)

                contact_id = body.get("id")

                if contact_id:
                    imported_contact_ids.append(contact_id)

            else:
                failed += 1
                errors.append(
                    {
                        "row_index": int(index),
                        "email": payload.get("email"),
                        "status_code": status_code,
                        "error": body,
                    }
                )

            progress_bar.progress(min(position / total_rows, 1.0))
            status_placeholder.caption(
                f"Procesados: {position}/{total_rows}"
            )

        st.markdown("### Resultado de importación")

        result_col1, result_col2, result_col3, result_col4 = st.columns(4)

        with result_col1:
            st.metric("Importados", imported)
        with result_col2:
            st.metric("Omitidos", skipped)
        with result_col3:
            st.metric("Fallidos", failed)
        with result_col4:
            st.metric("IDs importados", len(imported_contact_ids))

        if imported_contacts:
            st.success("Contactos importados correctamente.")
            st.dataframe(
                pd.DataFrame(imported_contacts),
                use_container_width=True,
                hide_index=True,
            )

        if errors:
            st.error("Algunos contactos no se pudieron importar.")
            st.dataframe(
                pd.DataFrame(errors),
                use_container_width=True,
                hide_index=True,
            )

        if associate_to_campaign and selected_campaign_id and imported_contact_ids:
            st.markdown("---")
            st.markdown("### Resultado de asociación a campaña")

            logger.info(
                "Associating imported contacts to campaign | campaign_id=%s | contacts=%s",
                selected_campaign_id,
                len(imported_contact_ids),
            )

            bulk_status, bulk_body = add_contacts_to_campaign_bulk(
                campaign_id=selected_campaign_id,
                contact_ids=imported_contact_ids,
            )

            if 200 <= bulk_status < 300:
                st.success("Contactos importados asociados a la campaña.")

                assign_col1, assign_col2, assign_col3, assign_col4 = st.columns(4)

                with assign_col1:
                    st.metric("Solicitados", bulk_body.get("total_requested"))
                with assign_col2:
                    st.metric("Procesados", bulk_body.get("total_processed"))
                with assign_col3:
                    st.metric("Pending", bulk_body.get("pending"))
                with assign_col4:
                    st.metric("Skipped", bulk_body.get("skipped"))

                st.json(bulk_body)

            else:
                st.error("Los contactos se importaron, pero no se pudieron asociar a la campaña.")
                st.json(bulk_body)

                