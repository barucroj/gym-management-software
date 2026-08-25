"""Worker de notificaciones.

Proceso independiente del API. Su responsabilidad es revisar periódicamente
las suscripciones próximas a vencer y generar las notificaciones/alertas
correspondientes.

NOTA: por ahora solo es el esqueleto del scheduler. La lógica de negocio
(consulta de suscripciones, reglas de vencimiento, envío de notificaciones)
se implementa en una iteración posterior.
"""

import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [notifier] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

INTERVAL_MINUTES = int(os.getenv("NOTIFIER_INTERVAL_MINUTES", "60"))
DAYS_BEFORE_EXPIRATION = int(os.getenv("NOTIFIER_DAYS_BEFORE_EXPIRATION", "7"))


def check_expiring_subscriptions() -> None:
    """Revisa suscripciones próximas a vencer. Pendiente de implementar."""
    logger.info(
        "Ciclo ejecutado (umbral: %s días). Lógica pendiente de implementar.",
        DAYS_BEFORE_EXPIRATION,
    )


def main() -> None:
    logger.info("Notifier iniciado. Intervalo: %s minutos.", INTERVAL_MINUTES)
    while True:
        check_expiring_subscriptions()
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
