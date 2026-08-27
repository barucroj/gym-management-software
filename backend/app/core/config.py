"""Configuracion propia del API.

Lo relativo a base de datos y reglas de dominio vive en gym_core.config,
porque lo comparte con el notifier.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Gym Management Software API"
    APP_VERSION: str = "0.1.0"

    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Origenes autorizados a llamar al API desde un navegador, separados por
    # coma. Vacio por defecto: sirviendo el frontend desde el mismo Nginx no
    # se cruza de origen y CORS no interviene.
    #
    # Es un string y no una list[str] a proposito: pydantic-settings espera
    # que una lista venga en JSON dentro de la variable de entorno, lo que
    # obligaria a escribir CORS_ORIGINS=["http://..."] en el .env.
    CORS_ORIGINS: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origen.strip() for origen in self.CORS_ORIGINS.split(",") if origen.strip()]


settings = Settings()
