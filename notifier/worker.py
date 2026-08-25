"""Worker de notificaciones.

Proceso independiente del API. Revisa periodicamente las suscripciones
proximas a vencer para generar alertas.

Usa los modelos y la regla de estatus de gym_core, los mismos que el API,
para que ambos no puedan divergir.

NOTA: por ahora solo consulta y reporta al log. El envio real de
notificaciones se implementa en feature/notifier-vencimientos.
"""

import logging
import time
from datetime import date, timedelta

from sqlmodel import Session, select

from gym_core.config import core_settings
from gym_core.db import engine
from gym_core.models import Miembro, Suscripcion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [notifier] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

INTERVAL_MINUTES = 60
DIAS_AVISO = core_settings.NOTIFIER_DAYS_BEFORE_EXPIRATION


def buscar_por_vencer(session: Session, hoy: date | None = None) -> list[tuple[Suscripcion, Miembro]]:
    """Suscripciones vigentes que vencen dentro del umbral de aviso."""
    hoy = hoy or date.today()
    limite = hoy + timedelta(days=DIAS_AVISO)

    sentencia = (
        select(Suscripcion, Miembro)
        .join(Miembro, Miembro.id == Suscripcion.miembro_id)  # type: ignore[arg-type]
        .where(Suscripcion.fecha_fin >= hoy)
        .where(Suscripcion.fecha_fin <= limite)
        .order_by(Suscripcion.fecha_fin)
    )
    return list(session.exec(sentencia).all())


def revisar_vencimientos() -> None:
    """Un ciclo de revision."""
    try:
        with Session(engine) as session:
            por_vencer = buscar_por_vencer(session)
    except Exception:
        logger.exception("Fallo la consulta de suscripciones; se reintenta en el proximo ciclo")
        return

    if not por_vencer:
        logger.info("Sin suscripciones por vencer en los proximos %s dias.", DIAS_AVISO)
        return

    logger.info("%s suscripcion(es) por vencer:", len(por_vencer))
    for suscripcion, miembro in por_vencer:
        logger.info(
            "  - %s (suscripcion %s) vence el %s",
            miembro.nombre_completo,
            suscripcion.id,
            suscripcion.fecha_fin,
        )


def main() -> None:
    logger.info(
        "Notifier iniciado. Intervalo: %s min. Umbral de aviso: %s dias.",
        INTERVAL_MINUTES,
        DIAS_AVISO,
    )
    while True:
        revisar_vencimientos()
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
