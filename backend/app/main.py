"""Punto de entrada de la API de Gym Management Software."""

from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Healthcheck usado por Docker y por el proxy."""
    return {"status": "ok", "service": settings.APP_NAME}
