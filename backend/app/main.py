"""Punto de entrada de la API de Gym Management Software."""

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import get_current_user, require_admin
from gym_core.db import engine

# Importar los routers de la carpeta app/routers/
from app.routers import (
    auth,
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
# Solo se activa si se declaran origenes en CORS_ORIGINS. En el despliegue
# normal queda apagado: Nginx sirve el frontend y el API por el mismo origen,
# asi que el navegador nunca hace una peticion entre origenes.
#
# Nunca "*" junto con allow_credentials: el estandar prohibe esa combinacion
# para peticiones con credenciales, y el navegador las rechaza.
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# --- REGISTRO DE ROUTERS ---
# Esto registra cada módulo en Swagger UI con su prefijo y etiqueta correspondientes.
# La proteccion se declara aqui, al montar cada router, y no dentro de cada
# endpoint: asi lo protegido es el default y abrir algo exige quitarlo de esta
# lista, que es un cambio visible en el diff.
protegido = [Depends(get_current_user)]
solo_admin = [Depends(require_admin)]

# auth queda abierto por definicion: es donde se consigue el token.
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

# Administrar al personal del sistema es tarea de un administrador.
app.include_router(
    usuarios.router, prefix="/api/v1/usuarios", tags=["Usuarios"], dependencies=solo_admin
)

# El resto lo opera cualquier usuario autenticado, incluida recepcion.
app.include_router(
    miembros.router, prefix="/api/v1/miembros", tags=["Miembros"], dependencies=protegido
)
app.include_router(
    planes.router, prefix="/api/v1/planes", tags=["Planes"], dependencies=protegido
)
app.include_router(
    suscripciones.router,
    prefix="/api/v1/suscripciones",
    tags=["Suscripciones"],
    dependencies=protegido,
)
app.include_router(
    asistencias.router,
    prefix="/api/v1/asistencias",
    tags=["Asistencias"],
    dependencies=protegido,
)


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