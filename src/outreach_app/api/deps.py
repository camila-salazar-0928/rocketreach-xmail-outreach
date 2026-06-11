from collections.abc import Generator

from sqlalchemy.orm import Session

from outreach_app.db.session import get_db_session


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()