from logger import Logger
from database.database import (
    DatabaseFacade
)
from database.models import (
    Properties,
    UsersProperties
)
from static.literals import (
    UserProperty
)
from .categories import CategoriesDbUtils


class UsersPropertiesDbUtils:
    def __init__(self, db: DatabaseFacade, logger: Logger):
        self.db = db
        self.logger = logger
        self.db_session = self.db.get_session()

    async def get_all_properties_names(self):
        with self.db_session as db_session:
            return [p[0] for p in db_session.query(Properties.property_name).all()]

    async def get_required_properties_names(self, user_id: int = None, filter_existing: bool = False) -> list[str]:
        with self.db_session as db_session:
            filters = [Properties.is_required == True]
            if user_id and filter_existing:
                existing_props = db_session.query(UsersProperties.property_id) \
                    .filter(UsersProperties.user_id == user_id).all()
                if existing_props:
                    existing_props = [x[0] for x in existing_props]
                    filters.append(Properties.property_id.notin_(existing_props))
            props = db_session.query(Properties.property_name).filter(*filters).all()
            return [x[0] for x in props]

    async def get_user_property(
        self,
        user_id: int,
        property_name: UserProperty,
        category_id: str = None
    ):
        """There are user properties with nested data. 
        For example `UserProperty.AMOUNTS`: `{"default": [1,2,3], "Eat Out": [10, 20]}`. 
        You can access nested values by providing corresponding `category_id`. 
        Example: `class_instance.get_user_property(
        user_id, UserProperty.AMOUNTS, "eat_out_categoty_guid"`
        ) -> `[10, 20]`"""
        property_value = self.db_session.query(UsersProperties.property_value).filter(
            UsersProperties.properties.has(Properties.property_name == property_name.value),
            UsersProperties.user_id == user_id
        ).first()

        if not property_value:
            return None

        if property_name == UserProperty.BASE_CURRENCY:
            return property_value[0].get("base_currency", "USD")

        if category_id:
            if category_id == "default":
                return property_value[0][category_id]
            cat = await CategoriesDbUtils(self.db, self.logger) \
                .get_category_by_id(category_id)
            category_name = cat.category_name if cat else "default"
            return property_value[0].get(category_name, property_value[0]["default"])

        return property_value[0]

    async def get_user_categories_map(self, user_id: int) -> dict[str, str]:
        """Returns map { "category_name": "category_id" }
        with categories user marked as visible for itself."""
        cat_map = {}

        for c in await self.get_user_property(user_id, UserProperty.CATEGORIES):
            temp = await CategoriesDbUtils(self.db, self.logger).get_category_by_name(c)
            cat_map[temp.category_name] = str(temp.category_id)
        return cat_map

    async def set_default_property_value_bulk(
        self,
        user_id: int,
        properties_to_set: list[str],
        is_update: bool = False
    ):
        for prop in properties_to_set:
            match prop:
                case UserProperty.CATEGORIES.value:
                    await self.set_property_value(user_id, prop, [
                        "Fun", "Clothes", "Transportation", "Eat Out",
                        "Food", "Facilities", "Medicine", "Home", "Other", "Rent"
                    ], is_update=is_update)
                case UserProperty.BASE_CURRENCY.value:
                    await self.set_property_value(user_id, prop, {
                        prop: "USD"
                    }, is_update=is_update)
                case UserProperty.AMOUNTS.value:
                    await self.set_property_value(user_id, prop, {
                        "default": [1, 3, 5, 7, 10, 15, 25, 30],
                        "Transportation": [5, 15, 20, 30, 50],
                        "Eat outside": [10, 15, 20, 25, 30, 40, 50, 60]
                    }, is_update=is_update)
                case UserProperty.COMMENTS.value:
                    await self.set_property_value(user_id, prop, {
                        "default": ["Groceries", "Weekly groceries", "Cafe", "Restaurant",
                                    "MyFavoriteDoner", "Taxi", "Public transport", "Water",
                                    "Electricity", "Heating", "Internet"]
                    }, is_update=is_update)
                case _:
                    pass

    async def set_property_value(
        self,
        user_id: int,
        property_name: str,
        property_value: dict | list | None,
        category: str | None = None,
        is_update: bool = False
    ):
        with self.db_session as db_session:
            categories_prop = db_session.query(Properties) \
                .filter(Properties.property_name == property_name).first()
            if is_update:
                if category:
                    filters = [
                        UsersProperties.properties.has(Properties.property_name == property_name),
                        UsersProperties.user_id == user_id
                    ]
                    current_prop_value = db_session.query(UsersProperties.property_value) \
                        .filter(*filters).first()[0]
                    current_prop_value[category] = property_value
                    property_value = current_prop_value
                db_session.bulk_update_mappings(UsersProperties, [{
                    "user_id": user_id,
                    "property_id": categories_prop.property_id,
                    "property_value": property_value
                }])
            else:
                db_session.add(UsersProperties(
                    property_id=categories_prop.property_id,
                    user_id=user_id,
                    property_value=property_value
                ))
            db_session.commit()
