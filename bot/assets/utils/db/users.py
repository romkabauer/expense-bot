from .users_properties import UsersPropertiesDbUtils
from database.database import DatabaseFacade
from database.models import (
    Users
)
from logger import Logger


class UsersDbUtils:
    def __init__(self, db: DatabaseFacade, logger: Logger):
        self.db = db
        self.logger = logger
        self.db_session = self.db.get_session()

    async def create_user_if_not_exist(self, user_id: int):
        with self.db_session as db_session:
            user = db_session.get(Users, user_id)
            if not user:
                db_session.add(Users(
                    user_id=user_id,
                    user_role="viewer"
                ))
                db_session.commit()
                up_utils = UsersPropertiesDbUtils(self.db, self.logger)
                await up_utils.set_default_property_value_bulk(
                    user_id,
                    await up_utils.get_required_properties_names()
                )
                db_session.commit()

    async def reset_user_properties(self, user_id: int):
        await self.create_user_if_not_exist(user_id)
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)
        await up_utils.set_default_property_value_bulk(
            user_id,
            await up_utils.get_required_properties_names(),
            True
        )
