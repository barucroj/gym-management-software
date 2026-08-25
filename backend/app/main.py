"""Punto de entrada de la API de Gym Management Software."""

from fastapi import FastAPI, Response, status
from sqlalchemy import text

from app.core.config import settings
from gym_core.db import engine

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Healthcheck superficial: el proceso responde."""
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/health/db", tags=["health"])
def health_db(response: Response) -> dict[str, str]:
    """Healthcheck real: verifica que la base de datos responde."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depende del entorno
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "unreachable", "detail": str(exc)}
    return {"status": "ok", "database": "reachable"}
