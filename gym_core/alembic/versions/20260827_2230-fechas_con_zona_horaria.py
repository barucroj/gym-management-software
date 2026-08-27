"""fechas con zona horaria

Revision ID: a3f9c1d20b47
Revises: fb01695637ae
Create Date: 2026-08-27 22:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f9c1d20b47'
down_revision: str | None = 'fb01695637ae'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Las tres marcas de tiempo siempre se escribieron con datetime.now(timezone.utc),
# pero la columna era "timestamp without time zone", asi que el desplazamiento se
# perdia al guardar y el JSON salia sin zona: cualquier cliente lo interpretaba
# como hora local.
#
# Los valores ya almacenados SON UTC. "AT TIME ZONE 'UTC'" se lo declara a
# Postgres; sin esa clausula, la conversion los reinterpretaria como hora local
# del servidor y desplazaria todos los registros existentes.
_COLUMNAS = [
    ("usuarios", "creado_en"),
    ("suscripciones", "creada_en"),
    ("asistencias", "registrada_en"),
]


def upgrade() -> None:
    for tabla, columna in _COLUMNAS:
        op.alter_column(
            tabla,
            columna,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
            postgresql_using=f"{columna} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for tabla, columna in _COLUMNAS:
        op.alter_column(
            tabla,
            columna,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=False,
            postgresql_using=f"{columna} AT TIME ZONE 'UTC'",
        )
