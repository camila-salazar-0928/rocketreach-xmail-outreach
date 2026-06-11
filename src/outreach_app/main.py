import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from outreach_app.core.config import get_settings
from outreach_app.core.logger import configure_logging
from outreach_app.api.routes_contacts import router as contacts_router
from outreach_app.db.__init__ import create_database_tables

settings = get_settings()

configure_logging(settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Application startup | app_name=%s | environment=%s",
        settings.app_name,
        settings.environment,
    )
    create_database_tables()

    yield

    logger.info("Application shutdown | app_name=%s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(contacts_router)

@app.get("/health")
def health_check():
    logger.debug("Health check requested")
    return {"status": "ok", "environment": settings.environment}