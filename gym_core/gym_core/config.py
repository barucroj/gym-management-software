"""Configuracion compartida, leida desde variables de entorno."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://gym:changeme@localhost:5432/gymdb"

    # Dias de anticipacion con los que una suscripcion se considera "por vencer".
    # Lo usan tanto el API (al reportar estatus) como el notifier (al alertar),
    # por eso vive aqui y no en la configuracion de un solo servicio.
    NOTIFIER_DAYS_BEFORE_EXPIRATION: int = 7


core_settings = CoreSettings()
