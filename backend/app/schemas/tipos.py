"""Tipos compartidos por los schemas del API."""

import re
from typing import Annotated

from pydantic import AfterValidator, Field

# Comprobacion deliberadamente simple: algo, arroba, dominio con al menos un
# punto. Alcanza para atajar el error real (un correo mal tipeado) sin
# pretender implementar el RFC 5322, que es mucho mas permisivo de lo que
# cualquiera espera.
#
# No se usa pydantic EmailStr ni email-validator: esa libreria rechaza los
# dominios de uso especial, y "local" es uno de ellos. Este sistema se
# despliega en la red interna de un solo gimnasio, donde una direccion como
# recepcion@gimnasio.local es legitima. Validar de mas seria rechazar datos
# correctos del cliente, que es un error peor que aceptar uno raro.
_PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validar_email(valor: str) -> str:
    valor = valor.strip()
    if not _PATRON_EMAIL.match(valor):
        raise ValueError("no parece una direccion de correo valida")
    # Se normaliza a minusculas: el email es unique en la tabla de usuarios y
    # sin esto Ada@gym.local y ada@gym.local serian dos cuentas distintas.
    return valor.lower()


Email = Annotated[str, AfterValidator(_validar_email), Field(max_length=255)]
