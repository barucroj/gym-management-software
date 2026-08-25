"""Suscripcion: la vigencia que un miembro compra sobre un plan."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from gym_core.enums import EstatusSuscripcion
from gym_core.estatus import calcular_estatus

if TYPE_CHECKING:
    from gym_core.models.miembro import Miembro
    from gym_core.models.plan import Plan


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class Suscripcion(SQLModel, table=True):
    __tablename__ = "suscripciones"

    id: int | None = Field(default=None, primary_key=True)
    miembro_id: int = Field(foreign_key="miembros.id", index=True)
    plan_id: int = Field(foreign_key="planes.id", index=True)

    fecha_inicio: date
    # Ultimo dia de vigencia, inclusivo. Indexado porque el notifier consulta
    # por rango sobre esta columna en cada ciclo.
    fecha_fin: date = Field(index=True)

    # Se guarda el precio del momento de la compra: si el plan sube de precio
    # despues, el historial de cobros no debe cambiar.
    precio_pagado: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    creada_en: datetime = Field(default_factory=_ahora)

    miembro: "Miembro" = Relationship(back_populates="suscripciones")
    plan: "Plan" = Relationship(back_populates="suscripciones")

    def estatus(
        self,
        hoy: date | None = None,
        dias_aviso: int | None = None,
    ) -> EstatusSuscripcion:
        """Estatus derivado de la fecha de fin. No es una columna."""
        return calcular_estatus(self.fecha_fin, hoy=hoy, dias_aviso=dias_aviso)
