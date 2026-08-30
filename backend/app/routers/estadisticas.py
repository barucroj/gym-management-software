"""Endpoints de estadisticas.

Ningun numero de aqui esta guardado: todos se derivan al momento de las tablas
existentes. Ver app.services.estadisticas.
"""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.schemas.estadisticas import ConteoDiarioRead, FranjaHorariaRead, ResumenRead
from app.services import estadisticas
from gym_core.db import get_session

router = APIRouter()


@router.get("/resumen", response_model=ResumenRead)
def resumen(session: Session = Depends(get_session)):
    """Los KPIs del panel, contados en la base y no en el navegador."""
    return estadisticas.resumen(session)


@router.get("/horas-pico", response_model=list[FranjaHorariaRead])
def horas_pico(
    dias: int = Query(default=estadisticas.DIAS_HORAS_PICO, ge=1, le=365),
    session: Session = Depends(get_session),
):
    """A que hora viene la gente. Siempre devuelve las 24 franjas."""
    return estadisticas.horas_pico(session, dias=dias)


@router.get("/asistencias-por-dia", response_model=list[ConteoDiarioRead])
def asistencias_por_dia(
    dias: int = Query(default=estadisticas.DIAS_GRAFICO, ge=1, le=365),
    session: Session = Depends(get_session),
):
    """Serie diaria de asistencias, con los dias vacios incluidos."""
    return estadisticas.asistencias_por_dia(session, dias=dias)
