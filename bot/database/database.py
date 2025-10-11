import os
from functools import lru_cache

from sqlalchemy import create_engine, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base(metadata=MetaData(schema="expense_bot"))


class DatabaseFacade:
    @staticmethod
    @lru_cache
    def get_engine(connection_string: str = "") -> Engine:
        if connection_string:
            return create_engine(connection_string)
        return create_engine(os.environ["EXPENSE_BOT_DB_CONNECTION_STRING"])

    @staticmethod
    @lru_cache
    def get_session(connection_string: str = "") -> Session:
        session_type = sessionmaker(DatabaseFacade.get_engine(connection_string), future=True)
        return session_type()
