"""Configuración de la aplicación, leída desde variables de entorno."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Gym Management Software API"
    APP_VERSION: str = "0.1.0"

    # Base de datos
    DATABASE_URL: str = "postgresql+psycopg://gym:changeme@localhost:5432/gymdb"

    # Seguridad / JWT
    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


settings = Settings()
