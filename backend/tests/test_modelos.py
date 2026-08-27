"""Tests de los modelos contra una base SQLite en memoria.

No tocan PostgreSQL a proposito: verifican relaciones y restricciones del
modelo, que son independientes del motor.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from gym_core.enums import EstatusSuscripcion, RolUsuario
from gym_core.models import Asistencia, Miembro, Plan, Suscripcion, Usuario


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_alta_de_miembro_y_nombre_completo(session: Session) -> None:
    miembro = Miembro(nombre="Ana", apellidos="Torres")
    session.add(miembro)
    session.commit()
    session.refresh(miembro)

    assert miembro.id is not None
    assert miembro.activo is True
    assert miembro.fecha_registro == date.today()
    assert miembro.nombre_completo == "Ana Torres"


def test_suscripcion_enlaza_miembro_y_plan(session: Session) -> None:
    miembro = Miembro(nombre="Luis", apellidos="Ramos")
    plan = Plan(nombre="Mensual", duracion_dias=30, precio=Decimal("450.00"))
    session.add_all([miembro, plan])
    session.commit()

    inicio = date(2026, 6, 1)
    suscripcion = Suscripcion(
        miembro_id=miembro.id,
        plan_id=plan.id,
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(days=plan.duracion_dias),
        precio_pagado=plan.precio,
    )
    session.add(suscripcion)
    session.commit()
    session.refresh(miembro)

    assert len(miembro.suscripciones) == 1
    assert miembro.suscripciones[0].plan.nombre == "Mensual"


def test_estatus_se_calcula_no_se_guarda(session: Session) -> None:
    """El estatus es un metodo, no una columna de la tabla."""
    assert "estatus" not in Suscripcion.model_fields

    suscripcion = Suscripcion(
        miembro_id=1,
        plan_id=1,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 1, 31),
        precio_pagado=Decimal("0"),
    )
    assert suscripcion.estatus(hoy=date(2026, 1, 10), dias_aviso=7) is EstatusSuscripcion.ACTIVA
    assert suscripcion.estatus(hoy=date(2026, 1, 28), dias_aviso=7) is EstatusSuscripcion.POR_VENCER
    assert suscripcion.estatus(hoy=date(2026, 2, 5), dias_aviso=7) is EstatusSuscripcion.VENCIDA


def test_asistencia_sin_suscripcion_es_valida(session: Session) -> None:
    """Se registra la entrada aunque no haya suscripcion vigente."""
    miembro = Miembro(nombre="Sara", apellidos="Lopez")
    session.add(miembro)
    session.commit()

    session.add(Asistencia(miembro_id=miembro.id))
    session.commit()

    asistencias = session.exec(select(Asistencia)).all()
    assert len(asistencias) == 1
    assert asistencias[0].suscripcion_id is None


def test_email_de_usuario_es_unico(session: Session) -> None:
    session.add(Usuario(nombre="Admin", email="admin@gym.local", hashed_password="x"))
    session.commit()

    session.add(Usuario(nombre="Otro", email="admin@gym.local", hashed_password="y"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_rol_por_defecto_es_recepcion(session: Session) -> None:
    usuario = Usuario(nombre="Recep", email="recep@gym.local", hashed_password="x")
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    assert usuario.rol is RolUsuario.RECEPCION


def test_nombre_de_plan_es_unico(session: Session) -> None:
    session.add(Plan(nombre="Anual", duracion_dias=365, precio=Decimal("4500")))
    session.commit()

    session.add(Plan(nombre="Anual", duracion_dias=365, precio=Decimal("4800")))
    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("modelo", "columna"),
    [(Usuario, "creado_en"), (Suscripcion, "creada_en"), (Asistencia, "registrada_en")],
)
def test_las_marcas_de_tiempo_llevan_zona_horaria(modelo, columna: str) -> None:
    """Sin timezone=True la columna guarda la hora sin contexto, el JSON sale
    sin desplazamiento y cualquier cliente la interpreta como hora local."""
    assert modelo.__table__.c[columna].type.timezone is True
