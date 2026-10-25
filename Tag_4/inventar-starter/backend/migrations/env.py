import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Gleiche Verbindungsdaten wie die App (aus .env), sonst Default aus alembic.ini
if os.getenv("POSTGRES_USER"):
    config.set_main_option(
        "sqlalchemy.url",
        "postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}".format(
            user=os.getenv("POSTGRES_USER"),
            pw=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST", "db"),
            port=os.getenv("POSTGRES_CONTAINER_PORT", "5432"),
            db=os.getenv("POSTGRES_DB"),
        ),
    )

# Kein ORM: Migrationen werden von Hand geschrieben, daher keine target_metadata
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
