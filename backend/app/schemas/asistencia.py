"""Contratos de entrada y salida del recurso asistencias."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AsistenciaCreate(BaseModel):
    """Check-in de un miembro.

    No declara registrada_en a proposito: la hora de entrada la pone el
    servidor. Si la mandara el cliente, el registro dejaria de ser prueba de
    nada, porque cualquiera podria declarar la hora que quisiera.
    """

    miembro_id: int
    # Opcional: se registra la entrada aunque no haya suscripcion vigente,
    # para no perder el dato.
    suscripcion_id: int | None = None

    # usuario_id tampoco se declara, por el mismo motivo que registrada_en: lo
    # pone el API con el usuario del token. Si viniera del cliente, cualquiera
    # podria anotar entradas a nombre de otro y la auditoria no valdria nada.


class AsistenciaUpdate(BaseModel):
    """Correccion de un registro ya hecho.

    Aqui si se admite registrada_en: corregir a mano una entrada mal cargada
    es una operacion legitima, distinta de registrarla.
    """

    miembro_id: int | None = None
    suscripcion_id: int | None = None
    registrada_en: datetime | None = None


class AsistenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    miembro_id: int
    registrada_en: datetime
    suscripcion_id: int | None
    # Quien lo registro. None en las asistencias anteriores a esta columna.
    usuario_id: int | None
