"""Configuracion compartida, leida desde variables de entorno."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://gym:changeme@localhost:5432/gymdb"

    # Zona horaria del gimnasio. Las marcas de tiempo se guardan en UTC, que es
    # lo correcto, pero "a que hora viene la gente" solo tiene sentido en la
    # hora local: un gimnasio en UTC-6 veria su pico de las 19:00 reportado a
    # la 01:00 del dia siguiente.
    GYM_TIMEZONE: str = "UTC"

    # Dias de anticipacion con los que una suscripcion se considera "por vencer".
    # Lo usan tanto el API (al reportar estatus) como el notifier (al alertar),
    # por eso vive aqui y no en la configuracion de un solo servicio.
    NOTIFIER_DAYS_BEFORE_EXPIRATION: int = 7


core_settings = CoreSettings()
