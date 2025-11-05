import uuid
from datetime import datetime as dt

from aiogram.types import Message
from pydantic_core import ValidationError
from pydantic import validate_call

from static import SUPPORTED_BASE_CURRENCIES
from static.literals import (
    UpsertStatus,
    UserProperty
)
from utils import CurrencyRateExtractor
from utils.db import UsersPropertiesDbUtils
from database.database import (
    DatabaseFacade,
    Session
)
from database.models import Expenses
from logger import Logger


class ExpenseUncommited:
    def __init__(self, logger: Logger):
        self.logger = logger

        self.expense_id : uuid.UUID | str | None = uuid.uuid4()
        self.user_id    : int | None             = None
        self.category_id: uuid.UUID | str | None = None
        self.spent_on   : dt | str | None        = None
        self.amount     : float | None           = None
        self.currency   : str | None             = None
        self.rates      : dict | str | None      = None
        self.comment    : str | None             = None
        self.created_at : dt | str | None        = None
        self.message_id : int | None             = None

    def to_dict(self):
        return {
            "expense_id": self.expense_id,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "spent_on": self.spent_on,
            "amount": self.amount,
            "currency": self.currency,
            "rates": self.rates,
            "comment": self.comment,
            "created_at": self.created_at,
            "message_id": self.message_id
        }

    def patch(self, patch_payload: dict):
        for k, v in patch_payload.items():
            if hasattr(self, k) and k != "logger":
                try:
                    setattr(self, k, v)
                except Exception as e:
                    self.logger.log(self, "error", "", f"Error while patching Expense: {e}")
                    raise ValidationError from e

    async def upsert_to_db(self, db: Session) -> tuple[Expenses, UpsertStatus]:
        self.__is_ready_to_commit()

        existing = db.get(Expenses, self.expense_id)
        status = UpsertStatus.INSERTED

        if existing:
            for k, v in self.to_dict().items():
                if k == "expense_id":
                    continue
                setattr(existing, k, v)
            status = UpsertStatus.UPDATED
        else:
            existing = Expenses(**self.to_dict())
            db.add(existing)
        return (existing, status)


    async def delete_if_exists(self, db: DatabaseFacade):
        with db.get_session() as db_session:
            e = db_session.query(Expenses).get(self.expense_id)
            if e:
                db_session.delete(e)
                db_session.commit()

    async def sync_by_associated_msg(self, db: DatabaseFacade, msg: Message):
        try:
            with db.get_session() as db_session:
                cur_expense: Expenses = db_session.query(Expenses).filter(
                        Expenses.user_id == msg.chat.id,
                        Expenses.message_id == msg.message_id
                    ).first()
                if cur_expense:
                    self.patch(cur_expense.to_dict())
        except IndexError as e:
            self.logger.log(
                self,
                level="warn",
                user=msg.chat.id,
                extra_text=(f"Expense for user {msg.chat.id} " +
                    f"and message id {msg.message_id} was not found: {e}")
            )
        return self

    async def sync_currency_rates(self, db: DatabaseFacade):
        if not self.user_id:
            self.logger.log(
                self,
                level="warn",
                extra_text="Missing user_id field to identify user's base currency!"
            )
            return
        if not self.spent_on:
            self.logger.log(
                self,
                level="warn",
                user=self.user_id,
                extra_text="Missing spent_on field to identify rates time frame!"
            )
            return
        base_currency = self.currency
        if not base_currency:
            base_currency = (
                UsersPropertiesDbUtils(db, self.logger).get_user_property(
                    self.user_id,
                    UserProperty.BASE_CURRENCY
                )
            )
        rates = CurrencyRateExtractor().extract_currency_rates(
            base_currency,
            self.spent_on.date().isoformat()
        )
        self.rates = rates

    def __is_ready_to_commit(self):
        required_fields = [
            "expense_id",
            "user_id",
            "category_id",
            "spent_on",
            "amount",
            "currency",
            "rates",
            "comment",
            "created_at"
        ]

        for field in required_fields:
            value = getattr(self, field, None)
            if value is None:
                return False

        return True

    # ---------- PROPERTIES ----------

    # ---------- message_id ----------
    @property
    def message_id(self) -> int | None:
        return self._message_id

    @message_id.setter
    @validate_call
    def message_id(self, v: int | None):
        if v is not None and v < 0:
            raise ValueError("message_id must be a positive integer")
        self._message_id = v

    # ---------- user_id ----------
    @property
    def user_id(self) -> int | None:
        return self._user_id

    @user_id.setter
    @validate_call
    def user_id(self, v: int | None):
        if v is not None and v < 0:
            raise ValueError("user_id must be a positive integer")
        self._user_id = v

    # ---------- amount ----------
    @property
    def amount(self) -> float | None:
        return self._amount

    @amount.setter
    @validate_call
    def amount(self, v: float | int | None):
        self._amount = float(v) if v is not None else None

    # ---------- currency ----------
    @property
    def currency(self) -> str | None:
        return self._currency

    @currency.setter
    @validate_call
    def currency(self, v: str | None):
        self._currency = v if v in SUPPORTED_BASE_CURRENCIES else "USD"

    # ---------- created_at ----------
    @property
    def created_at(self) -> dt | str | None:
        return self._created_at

    @created_at.setter
    @validate_call
    def created_at(self, v: dt | str | None):
        if isinstance(v, str):
            try:
                v = dt.fromisoformat(v)
            except ValueError as e:
                raise ValueError("created_at string must be in ISO 8601 format") from e
        self._created_at = v

    # ---------- spent_on ----------
    @property
    def spent_on(self) -> dt | str | None:
        return self._spent_on

    @spent_on.setter
    @validate_call
    def spent_on(self, v: dt | str | None):
        if isinstance(v, str):
            try:
                v = dt.fromisoformat(v)
            except ValueError as e:
                raise ValueError("spent_on string must be in ISO 8601 format") from e
        self._spent_on = v
