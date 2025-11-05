from typing import Any, Dict
import uuid

from sqlalchemy import UUID, Column, String
from sqlalchemy.orm import relationship

from database import Base


class Categories(Base):
    """
    Categories class represents a category object in the database.
    """

    __tablename__ = "categories"
    category_id = Column("id", UUID, primary_key=True, default=uuid.uuid4)
    category_name = Column("name", String, nullable=False)

    expenses = relationship("Expenses", back_populates="categories")

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            category_id=self.category_id,
            category_name=self.category_name,
        )
