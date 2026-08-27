"""Punto de entrada de la API de Gym Management Software."""

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from gym_core.db import engine

# Importar los routers de la carpeta app/routers/
from app.routers import (
    usuarios,
    miembros,
    planes,
    suscripciones,
    asistencias,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


# --- CONFIGURACIÓN DE CORS ---
# Permite que el frontend se comunique con la API sin bloqueos del navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REGISTRO DE ROUTERS ---
# Esto registra cada módulo en Swagger UI con su prefijo y etiqueta correspondientes.
app.include_router(usuarios.router, prefix="/api/v1/usuarios", tags=["Usuarios"])
app.include_router(miembros.router, prefix="/api/v1/miembros", tags=["Miembros"])
app.include_router(planes.router, prefix="/api/v1/planes", tags=["Planes"])
app.include_router(suscripciones.router, prefix="/api/v1/suscripciones", tags=["Suscripciones"])
app.include_router(asistencias.router, prefix="/api/v1/asistencias", tags=["Asistencias"])


# --- HEALTHCHECKS ---
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