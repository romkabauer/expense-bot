from database.database import DatabaseFacade
from database.models import (
    Categories
)
from logger import Logger


class CategoriesDbUtils:
    def __init__(self, db: DatabaseFacade, logger: Logger):
        self.db = db
        self.logger = logger
        self.db_session = self.db.get_session()

    async def get_all_categories(self, mode: str = "NAMES"):
        """
        Available modes:
        - NAMES (default) - returns list of all categories names
        - MAP - Returns map { "category_name": "category_id" }
        """
        with self.db_session as db_session:
            categories = db_session.query(Categories).all()
            if mode == "MAP":
                res_map = {}
                for c in categories:
                    res_map[c.category_name] = c.category_id
                return res_map
            return [c.category_name for c in categories]

    async def get_category_by_id(self, category_id: str) -> Categories:
        with self.db_session as db_session:
            return db_session.get(Categories, category_id)

    async def get_category_by_name(self, category_name: str) -> Categories | None:
        with self.db_session as db_session:
            cat = (db_session
                    .query(Categories)
                    .filter(Categories.category_name == category_name)
                    .first())
            if not cat:
                return (db_session
                    .query(Categories)
                    .filter(Categories.category_name == "Other")
                    .first())
            return cat
