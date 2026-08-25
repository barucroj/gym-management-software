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


settings = Settings()
