"""Enumeraciones del dominio."""

from enum import Enum


class RolUsuario(str, Enum):
    """Roles del personal que opera el sistema."""

    ADMIN = "admin"
    RECEPCION = "recepcion"


class EstatusSuscripcion(str, Enum):
    """Estatus de una suscripcion.

    No se persiste: se calcula a partir de la fecha de fin. Ver
    gym_core.estatus.calcular_estatus.
    """

    ACTIVA = "activa"
    POR_VENCER = "por_vencer"
    VENCIDA = "vencida"
