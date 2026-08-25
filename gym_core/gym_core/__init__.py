"""Nucleo compartido: modelos, acceso a datos y reglas de dominio.

Este paquete se instala tanto en la imagen del API como en la del notifier,
para que ambos procesos usen exactamente los mismos modelos y las mismas
reglas de negocio sin duplicar codigo.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
