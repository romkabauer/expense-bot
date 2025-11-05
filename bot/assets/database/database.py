import os
from functools import lru_cache

from sqlalchemy import create_engine, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


SERVICE_USER = os.environ["POSTGRES_USER"]
SERVICE_USER_PASS = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
BOT_DB = os.environ["POSTGRES_DB_BOT"]
BOT_SCHEMA = os.environ["POSTGRES_SCHEMA_BOT"]
EXPENSE_BOT_DB_CONNECTION_STRING = f"postgresql://{SERVICE_USER}:{SERVICE_USER_PASS}@{POSTGRES_HOST}/{BOT_DB}"


Base = declarative_base(metadata=MetaData(schema=BOT_SCHEMA))


class DatabaseFacade:
    @staticmethod
    @lru_cache
    def get_engine(connection_string: str = "") -> Engine:
        if connection_string:
            return create_engine(connection_string)
        return create_engine(EXPENSE_BOT_DB_CONNECTION_STRING)

    @staticmethod
    @lru_cache
    def get_session(connection_string: str = "") -> Session:
        session_type = sessionmaker(DatabaseFacade.get_engine(connection_string), future=True)
        return session_type()
