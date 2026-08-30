"""Endpoints de los miembros del gimnasio."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.schemas.miembro import (
    MiembroBusquedaRead,
    MiembroCreate,
    MiembroRead,
    MiembroUpdate,
)
from app.services.busqueda import LIMITE_POR_DEFECTO, buscar_miembros
from gym_core.db import get_session
from gym_core.models.miembro import Miembro

router = APIRouter()


@router.get("/", response_model=list[MiembroRead])
def listar_miembros(session: Session = Depends(get_session)):
    return session.exec(select(Miembro)).all()


# Va declarado ANTES de /{miembro_id}: FastAPI resuelve las rutas en el orden
# en que se registran, y si /{miembro_id} fuera primero intentaria leer
# "buscar" como un entero y responderia 422 en vez de buscar nada.
@router.get("/buscar", response_model=list[MiembroBusquedaRead])
def buscar_socios(
    # min_length=1 y no LONGITUD_MINIMA: un id de un solo digito es una
    # consulta legitima. El minimo para los nombres lo aplica el servicio.
    q: str = Query(
        min_length=1,
        max_length=120,
        description="Nombre, apellido o id del socio. Tolera erratas y acentos.",
    ),
    limite: int = Query(default=LIMITE_POR_DEFECTO, ge=1, le=50),
    solo_activos: bool = Query(default=False, description="Excluye a los dados de baja"),
    session: Session = Depends(get_session),
):
    """Busca socios por parecido, no por subcadena. Ver app.services.busqueda."""
    resultados = buscar_miembros(session, q, limite=limite, solo_activos=solo_activos)
    return [MiembroBusquedaRead.desde(r.miembro, r.puntaje) for r in resultados]


@router.get("/{miembro_id}", response_model=MiembroRead)
def obtener_miembro(miembro_id: int, session: Session = Depends(get_session)):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
    return miembro


@router.post("/", response_model=MiembroRead, status_code=status.HTTP_201_CREATED)
def crear_miembro(datos: MiembroCreate, session: Session = Depends(get_session)):
    miembro = Miembro(**datos.model_dump())
    session.add(miembro)
    session.commit()
    session.refresh(miembro)
    return miembro


@router.put("/{miembro_id}", response_model=MiembroRead)
def actualizar_miembro(
    miembro_id: int, datos: MiembroUpdate, session: Session = Depends(get_session)
):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(miembro, campo, valor)

    session.add(miembro)
    session.commit()
    session.refresh(miembro)
    return miembro


@router.delete("/{miembro_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_miembro(miembro_id: int, session: Session = Depends(get_session)):
    miembro = session.get(Miembro, miembro_id)
    if not miembro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")

    # El modelo preve baja logica. Borrar de verdad a alguien con historial
    # violaria las claves foraneas de suscripciones y asistencias, y ademas
    # perderia datos que el gimnasio necesita conservar.
    if miembro.suscripciones or miembro.asistencias:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El miembro tiene historial: darlo de baja con activo=false",
        )

    session.delete(miembro)
    session.commit()
    return None
