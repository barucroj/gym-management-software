"""Entorno de Alembic.

La URL de la base se toma de las variables de entorno (nunca de alembic.ini)
y el metadata sale de los modelos de gym_core.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Importar los modelos puebla SQLModel.metadata. Sin esto, autogenerate
# no veria ninguna tabla y generaria migraciones vacias.
import gym_core.models  # noqa: F401
from gym_core.config import core_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", core_settings.DATABASE_URL)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse a la base."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones contra la base."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
