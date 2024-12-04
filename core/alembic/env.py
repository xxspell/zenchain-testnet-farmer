from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from core.database.models import Base
from core.database.connect import db_path


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def load_database_url():
    return 'sqlite:///' + db_path

def run_migrations_offline() -> None:
    url = load_database_url()
    print(f"Running migrations offline with database URL: {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    url = load_database_url()
    print(f"Running migrations online with database URL: {url}")
    connectable = engine_from_config(
        {
            'sqlalchemy.url': url
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    print(f"Using database URL: {url}")

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
