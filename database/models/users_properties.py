from typing import Any, Dict
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, JSON, ForeignKey, UUID, func, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from database import Base


class UsersProperties(Base):
    """
    UsersProperties class represents a linking table between users and their properties' values in the database.
    """

    __tablename__ = "users_properties"
    __table_args__ = (
        PrimaryKeyConstraint("property_id", "user_id", name="pk_users_properties"),
    )
    property_id = Column("property_id", UUID(as_uuid=True), ForeignKey("properties.id"))
    user_id = Column("user_id", BigInteger, ForeignKey("users.id"))
    property_value = Column("property_value", JSON, nullable=False)
    created_at = Column("created_at", DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("Users", back_populates="users_properties")
    properties = relationship("Properties", back_populates="users_properties")

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            property_id=self.property_id,
            user_id=self.user_id,
            property_value=self.property_value,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
