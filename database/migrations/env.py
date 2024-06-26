from logging.config import fileConfig

from sqlalchemy import create_engine
import os

from alembic import context

from database import Base
from database.models import (
    Users,
    UsersProperties,
    Properties,
    Categories,
    Expenses
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your models's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

connection_url = os.getenv("EXPENSE_BOT_DB_CONNECTION_STRING")
config.set_main_option("sqlalchemy.url", f"{connection_url}")


def include_name(name, type_, _):
    if type_ == "table":
        return name in target_metadata.tables
    else:
        return True


def include_object(object, name, type_, reflected, _):
    if type_ == "column" and not reflected and object.info.get("skip_autogenerate", False):
        return False
    else:
        return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connection_url = os.getenv("EXPENSE_BOT_DB_CONNECTION_STRING")
    engine = create_engine(connection_url)

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_object=include_object,
            version_table_schema=target_metadata.schema,
            include_schemas=True
        )

        with context.begin_transaction():
            context.execute(f'create schema if not exists {target_metadata.schema};')
            context.execute(f'set search_path to {target_metadata.schema}')
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
