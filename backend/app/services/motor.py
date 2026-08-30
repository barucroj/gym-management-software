"""Comprobacion del motor de base de datos.

Algunas consultas del sistema no son portables: la busqueda usa pg_trgm y las
estadisticas usan AT TIME ZONE. Se apoyan en PostgreSQL a proposito, porque es
lo que se despliega, pero conviene que quien las corra en otro motor reciba un
mensaje que diga eso y no un error de sintaxis del driver.
"""

from sqlmodel import Session


def exigir_postgresql(session: Session, para: str) -> None:
    dialecto = session.get_bind().dialect.name
    if dialecto != "postgresql":
        raise RuntimeError(f"{para} necesita PostgreSQL; el motor es {dialecto!r}.")
