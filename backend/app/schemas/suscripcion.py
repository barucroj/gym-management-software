"""Contratos de entrada y salida del recurso suscripciones."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gym_core.enums import EstatusSuscripcion
from gym_core.models.suscripcion import Suscripcion


class SuscripcionCreate(BaseModel):
    """Alta de suscripcion.

    No declara creada_en: es el sello de cuando el sistema registro la venta,
    y dejar que lo mande el cliente permitiria antedatar operaciones.
    """

    miembro_id: int
    plan_id: int
    fecha_inicio: date
    fecha_fin: date
    precio_pagado: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    # Suscripcion que esta renueva, si lo es. Sin este enlace una renovacion y
    # una venta nueva se ven identicas y no hay forma de saber cuantos socios
    # se quedan. El router verifica que sea del mismo miembro.
    renovada_de_id: int | None = None

    @model_validator(mode="after")
    def _fin_no_puede_preceder_al_inicio(self) -> "SuscripcionCreate":
        # Una vigencia invertida haria que la regla de estatus devolviera
        # "vencida" desde el primer dia, sin que nadie entienda por que.
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class SuscripcionUpdate(BaseModel):
    miembro_id: int | None = None
    plan_id: int | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    precio_pagado: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def _fin_no_puede_preceder_al_inicio(self) -> "SuscripcionUpdate":
        # Solo comparable si llegan las dos: si viene una sola, la coherencia
        # contra la que ya esta guardada se verifica en el router.
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class SuscripcionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    miembro_id: int
    plan_id: int
    fecha_inicio: date
    fecha_fin: date
    precio_pagado: Decimal
    creada_en: datetime
    renovada_de_id: int | None
    # Derivado de fecha_fin, nunca persistido. Ver gym_core.estatus.
    estatus: EstatusSuscripcion

    @classmethod
    def desde(cls, suscripcion: Suscripcion) -> "SuscripcionRead":
        """estatus es un metodo del modelo, no una columna.

        from_attributes solo lee atributos, no llama metodos, asi que se
        calcula aqui y se arma el schema con el resultado.
        """
        datos = suscripcion.model_dump()
        datos["estatus"] = suscripcion.estatus()
        return cls.model_validate(datos)
