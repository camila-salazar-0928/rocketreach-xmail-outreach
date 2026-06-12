import sys
from pathlib import Path
import logging
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.views.campaigns import render_campaigns_page
from dashboard.views.contacts import render_contacts_page
from dashboard.views.overview import render_overview_page
from dashboard.views.traceability import render_traceability_page
from dashboard.views.bulk_assignment import render_bulk_assignment_page
from dashboard.views.csv_import import render_csv_import_page

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)

logger = logging.getLogger(__name__)


def main() -> None:
    st.set_page_config(
        page_title="RocketReach Xmail Outreach",
        page_icon="📧",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("RocketReach Outreach")
    st.sidebar.caption("Gestión visual de contactos y campañas")

    page = st.sidebar.radio(
        "Navegación",
        options=[
            "Overview",
            "Contactos",
            "Campañas",
            "Asignación masiva",
            "Importar CSV",
            "Trazabilidad",
        ],
    )

    st.title("RocketReach Xmail Outreach Dashboard")

    if page == "Overview":
        render_overview_page()
    elif page == "Contactos":
        render_contacts_page()
    elif page == "Campañas":
        render_campaigns_page()
    elif page == "Trazabilidad":
        render_traceability_page()
    elif page == "Asignación masiva":
        render_bulk_assignment_page()
    elif page == "Importar CSV":
        render_csv_import_page()

if __name__ == "__main__":
    main()