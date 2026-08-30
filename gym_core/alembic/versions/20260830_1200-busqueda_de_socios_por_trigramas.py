"""busqueda de socios por trigramas

Revision ID: d4b8c1e07a52
Revises: a3f9c1d20b47
Create Date: 2026-08-30 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = 'd4b8c1e07a52'
down_revision: str | None = 'a3f9c1d20b47'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Recepcion escribe el nombre como lo escucha. Una busqueda por subcadena no
# encuentra a "Rodriguez" si tecleron "Rodrigez", ni a "Nunez" si escribieron
# "Nuñez". pg_trgm compara por trigramas y tolera las dos cosas.
#
# unaccent va aparte porque los trigramas de "rodriguez" y "rodríguez" no son
# los mismos: sin normalizar el acento, la tilde baja el puntaje de una
# coincidencia que para quien busca es exacta.
_INDICE = "ix_miembros_nombre_trgm"

# El indice tiene que construirse sobre EXACTAMENTE la misma expresion que use
# la consulta. Si difieren aunque sea en un espacio, PostgreSQL no lo usa y la
# busqueda pasa a recorrer la tabla entera sin avisar.
_EXPRESION = "gym_normalizar(nombre || ' ' || apellidos)"

# unaccent() es STABLE, no IMMUTABLE, porque su diccionario podria recargarse:
# PostgreSQL se niega a indexar una expresion que la use directamente. La forma
# de dos argumentos nombra el diccionario en vez de resolverlo por search_path,
# que es lo que hace legitimo envolverla en una funcion IMMUTABLE. Es el patron
# que documenta el propio manual de PostgreSQL para este caso.
_FUNCION = """
CREATE OR REPLACE FUNCTION gym_normalizar(texto text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT lower(public.unaccent('public.unaccent', texto)) $$
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(_FUNCION)
    op.execute(f"CREATE INDEX {_INDICE} ON miembros USING gin ({_EXPRESION} gin_trgm_ops)")


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDICE}")
    op.execute("DROP FUNCTION IF EXISTS gym_normalizar(text)")
    # Las extensiones no se quitan a proposito: son de la base, no de esta
    # migracion, y borrarlas rompería a cualquier otro objeto que las use.
