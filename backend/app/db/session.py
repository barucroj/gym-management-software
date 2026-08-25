"""Motor y sesión de base de datos (SQLModel / SQLAlchemy)."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesión por request."""
    with Session(engine) as session:
        yield session
