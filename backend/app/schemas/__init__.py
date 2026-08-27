"""Schemas de entrada y salida del API (contratos HTTP).

Separados de gym_core.models a proposito: los modelos describen como se
guardan los datos, estos schemas describen que se acepta y que se devuelve.
"""

from app.schemas.asistencia import AsistenciaCreate, AsistenciaRead, AsistenciaUpdate
from app.schemas.auth import Token
from app.schemas.miembro import MiembroCreate, MiembroRead, MiembroUpdate
from app.schemas.plan import PlanCreate, PlanRead, PlanUpdate
from app.schemas.suscripcion import SuscripcionCreate, SuscripcionRead, SuscripcionUpdate
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate

__all__ = [
    "AsistenciaCreate",
    "AsistenciaRead",
    "AsistenciaUpdate",
    "MiembroCreate",
    "MiembroRead",
    "MiembroUpdate",
    "PlanCreate",
    "PlanRead",
    "PlanUpdate",
    "SuscripcionCreate",
    "SuscripcionRead",
    "SuscripcionUpdate",
    "Token",
    "UsuarioCreate",
    "UsuarioRead",
    "UsuarioUpdate",
]
