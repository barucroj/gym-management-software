from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.schemas.asistencia import (
    AsistenciaCreate,
    AsistenciaRead,
    AsistenciaUpdate,
    PaseDiaCreate,
    PaseDiaRead,
)
from app.services.tiempo import hoy_local
from gym_core.db import get_session
from gym_core.models.asistencia import Asistencia
from gym_core.models.miembro import Miembro
from gym_core.models.plan import Plan
from gym_core.models.suscripcion import Suscripcion
from gym_core.models.usuario import Usuario

router = APIRouter()



def _verificar_referencias(
    session: Session, miembro_id: int | None, suscripcion_id: int | None
) -> None:
    if miembro_id is not None and session.get(Miembro, miembro_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No existe el miembro {miembro_id}",
        )
    if suscripcion_id is not None and session.get(Suscripcion, suscripcion_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No existe la suscripcion {suscripcion_id}",
        )


@router.get("/", response_model=list[AsistenciaRead])
def listar_asistencias(session: Session = Depends(get_session)):
    return session.exec(select(Asistencia)).all()


@router.get("/{asistencia_id}", response_model=AsistenciaRead)
def obtener_asistencia(asistencia_id: int, session: Session = Depends(get_session)):
    asistencia = session.get(Asistencia, asistencia_id)
    if not asistencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asistencia no encontrada"
        )
    return asistencia


@router.post("/", response_model=AsistenciaRead, status_code=status.HTTP_201_CREATED)
def registrar_asistencia(
    datos: AsistenciaCreate,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(get_current_user),
):
    _verificar_referencias(session, datos.miembro_id, datos.suscripcion_id)

    # Ni registrada_en ni usuario_id se toman del cliente: la hora la pone el
    # modelo con la del servidor y el autor sale del token que ya viajaba en la
    # peticion. Es lo unico que hace del registro una prueba de algo.
    asistencia = Asistencia(**datos.model_dump(), usuario_id=usuario.id)
    session.add(asistencia)
    session.commit()
    session.refresh(asistencia)
    return asistencia


@router.post("/pase-dia", response_model=PaseDiaRead, status_code=status.HTTP_201_CREATED)
def registrar_pase_dia(
    datos: PaseDiaCreate,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(get_current_user),
):
    hoy = hoy_local()
    monto_dec = Decimal(str(datos.monto))
    nombre_limpio = (datos.nombre or "Visitante").strip()

    # Buscar o crear plan de Pase del Dia
    plan = session.exec(select(Plan).where(Plan.nombre == "Pase del Día")).first()
    if not plan:
        plan = session.exec(select(Plan).where(Plan.duracion_dias == 1)).first()
    if not plan:
        plan = Plan(
            nombre="Pase del Día",
            descripcion="Acceso por un día para visitantes",
            duracion_dias=1,
            precio=monto_dec,
            activo=True,
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)

    # Crear miembro de visita
    miembro = Miembro(
        nombre=nombre_limpio,
        apellidos="Visitante",
        fecha_registro=hoy,
        activo=True,
        notas=datos.notas or "Pase del Día / Visita rápida",
    )
    session.add(miembro)
    session.commit()
    session.refresh(miembro)

    # Crear suscripcion de 1 dia con el precio pagado
    suscripcion = Suscripcion(
        miembro_id=miembro.id,
        plan_id=plan.id,
        fecha_inicio=hoy,
        fecha_fin=hoy,
        precio_pagado=monto_dec,
    )
    session.add(suscripcion)
    session.commit()
    session.refresh(suscripcion)

    # Registrar asistencia
    asistencia = Asistencia(
        miembro_id=miembro.id,
        suscripcion_id=suscripcion.id,
        usuario_id=usuario.id,
    )
    session.add(asistencia)
    session.commit()
    session.refresh(asistencia)

    return PaseDiaRead(
        asistencia_id=asistencia.id,
        miembro_id=miembro.id,
        suscripcion_id=suscripcion.id,
        nombre_visitante=f"{miembro.nombre} {miembro.apellidos}",
        monto_pagado=float(monto_dec),
        registrada_en=asistencia.registrada_en,
    )



@router.put("/{asistencia_id}", response_model=AsistenciaRead)
def actualizar_asistencia(
    asistencia_id: int, datos: AsistenciaUpdate, session: Session = Depends(get_session)
):
    asistencia = session.get(Asistencia, asistencia_id)
    if not asistencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asistencia no encontrada"
        )

    cambios = datos.model_dump(exclude_unset=True)
    _verificar_referencias(session, cambios.get("miembro_id"), cambios.get("suscripcion_id"))

    for campo, valor in cambios.items():
        setattr(asistencia, campo, valor)

    session.add(asistencia)
    session.commit()
    session.refresh(asistencia)
    return asistencia


@router.delete("/{asistencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asistencia(asistencia_id: int, session: Session = Depends(get_session)):
    asistencia = session.get(Asistencia, asistencia_id)
    if not asistencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asistencia no encontrada"
        )

    session.delete(asistencia)
    session.commit()
    return None
