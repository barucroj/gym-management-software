"""Modelos del dominio.

Importarlos todos aqui garantiza que SQLModel.metadata quede completo,
que es de lo que depende Alembic para autogenerar migraciones.
"""

from gym_core.models.asistencia import Asistencia
from gym_core.models.miembro import Miembro
from gym_core.models.plan import Plan
from gym_core.models.suscripcion import Suscripcion
from gym_core.models.usuario import Usuario

__all__ = ["Asistencia", "Miembro", "Plan", "Suscripcion", "Usuario"]
