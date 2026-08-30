"""datos para estadisticas

Revision ID: e5c93a17b6f0
Revises: d4b8c1e07a52
Create Date: 2026-08-30 14:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e5c93a17b6f0'
down_revision: str | None = 'd4b8c1e07a52'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Casi toda estadistica de gimnasio se deriva de lo que ya hay guardado: las
# horas pico salen de asistencias.registrada_en y los ingresos de
# suscripciones.precio_pagado. Persistir esos numeros seria repetir el error
# que el proyecto ya decidio no cometer con el estatus de suscripcion.
#
# Lo que esta migracion agrega es lo contrario: hechos que hoy NO quedan
# registrados en ninguna parte y que, si no se guardan cuando ocurren, no hay
# consulta que los reconstruya despues.


def upgrade() -> None:
    # Quien registro cada check-in. Nullable porque las asistencias que ya
    # existen se registraron cuando el dato no se pedia, y porque el registro
    # historico vale mas que forzar un valor inventado.
    op.add_column("asistencias", sa.Column("usuario_id", sa.Integer(), nullable=True))
    op.create_index("ix_asistencias_usuario_id", "asistencias", ["usuario_id"])
    op.create_foreign_key(
        "fk_asistencias_usuario_id", "asistencias", "usuarios", ["usuario_id"], ["id"]
    )

    # Distingue una renovacion de una venta nueva. Sin este enlace las dos se
    # ven identicas en la tabla y no hay forma de calcular tasa de renovacion
    # ni antiguedad real del socio.
    op.add_column("suscripciones", sa.Column("renovada_de_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_suscripciones_renovada_de_id",
        "suscripciones",
        "suscripciones",
        ["renovada_de_id"],
        ["id"],
    )
    # Unico: una suscripcion se renueva una sola vez. Dos filas apuntando a la
    # misma anterior serian una bifurcacion del historial, es decir, un error
    # de carga que conviene que la base rechace en el momento.
    op.create_unique_constraint(
        "uq_suscripciones_renovada_de_id", "suscripciones", ["renovada_de_id"]
    )

    # activo dice que el socio se fue, pero no cuando ni por que. Sin la fecha
    # no hay churn mensual: solo se sabe cuantos hay de baja hoy.
    op.add_column("miembros", sa.Column("fecha_baja", sa.Date(), nullable=True))
    op.add_column("miembros", sa.Column("motivo_baja", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("miembros", "motivo_baja")
    op.drop_column("miembros", "fecha_baja")

    op.drop_constraint("uq_suscripciones_renovada_de_id", "suscripciones", type_="unique")
    op.drop_constraint("fk_suscripciones_renovada_de_id", "suscripciones", type_="foreignkey")
    op.drop_column("suscripciones", "renovada_de_id")

    op.drop_constraint("fk_asistencias_usuario_id", "asistencias", type_="foreignkey")
    op.drop_index("ix_asistencias_usuario_id", table_name="asistencias")
    op.drop_column("asistencias", "usuario_id")
