from typing import Any, Dict
import uuid

from sqlalchemy import UUID, Column, String, Boolean
from sqlalchemy.orm import relationship

from database import Base


class Properties(Base):
    """
    Properties class represents a property object in the database.
    """

    __tablename__ = "properties"
    property_id = Column("id", UUID, primary_key=True, default=uuid.uuid4)
    property_name = Column("name", String, nullable=False)
    is_required = Column("is_required", Boolean, nullable=False, default=False)

    users_properties = relationship("UsersProperties", back_populates="properties")

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            property_id=self.property_id,
            property_name=self.property_name,
            is_required=self.is_required,
        )
