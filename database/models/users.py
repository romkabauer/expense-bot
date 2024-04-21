from typing import Any, Dict
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String, func
from sqlalchemy.orm import relationship

from database import Base


class Users(Base):
    """
    Users class represents a user object in the database.
    """

    __tablename__ = "users"
    user_id = Column("id", BigInteger, primary_key=True)
    user_role = Column("role", String, nullable=False, default="viewer")
    created_at = Column("created_at", DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=func.now)

    expenses = relationship("Expenses", back_populates="users")
    users_properties = relationship("UsersProperties", back_populates="users")

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            user_id=self.user_id,
            user_role=self.user_role,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
