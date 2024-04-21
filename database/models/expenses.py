from typing import Any, Dict
from datetime import datetime
import uuid

from sqlalchemy import BigInteger, Float, Column, DateTime, Date, String, ForeignKey, UUID, JSON, func
from sqlalchemy.orm import relationship

from database import Base


class Expenses(Base):
    """
    Expenses class represents a expense object in the database.
    """

    __tablename__ = "expenses"
    expense_id = Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column("user_id", BigInteger, ForeignKey("users.id"), nullable=False)
    category_id = Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    spent_on = Column("spent_on", Date, nullable=False, default=func.current_date)
    amount = Column("amount", Float, nullable=False)
    currency = Column("currency", String, nullable=False, default="USD")
    rates = Column("rates", JSON, nullable=False)
    comment = Column("comment", String)
    created_at = Column("created_at", DateTime, nullable=False, default=datetime.utcnow)
    # updated_at = Column("updated_at", DateTime, nullable=False, default=datetime.utcnow(), onupdate=func.now())

    users = relationship("Users", back_populates="expenses")
    categories = relationship("Categories", back_populates="expenses")

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            expense_id=self.expense_id,
            user_id=self.user_id,
            category_id=self.category_id,
            spent_on=self.spent_on,
            amount=self.amount,
            currency=self.currency,
            rates=self.rates,
            comment=self.comment,
            created_at=self.created_at,
            # updated_at=self.updated_at,
        )
