import json
import os
from pathlib import Path
from datetime import datetime as dt

from aiogram import (
    types,
    Router,
    F,
    Bot
)

from static.literals import UserProperty
from static.interface_messages import AI_PROGRESS_MSG
from utils.db import (
    UsersDbUtils,
    UsersPropertiesDbUtils,
    CategoriesDbUtils,
    ExpenseUncommited
)
from utils.ai.providers import (
    GeminiAIProvider,
    AIModel
)
from utils.ai.prompt_templates import PromptTemplateExpenseFromFreeInput
from routers.abstract_router_builder import AbstractRouterBuilder
from logger import Logger

class AIRouterBuilder(AbstractRouterBuilder):
    def __init__(self, logger: Logger):
        super().__init__(logger)
        self.router = Router(name=self.__class__.__name__)
        path = Path("/tmp/bot_audio_storage")
        path.mkdir(parents=True, exist_ok=True)
        self.audio_storage_path = str(path)

    def build_default_router(self):
        self.router.message.register(self.handler_voice_expense_with_ai,
                                     F.content_type == types.ContentType.VOICE)
        self.router.message.register(self.handler_text_expense_with_ai,
                                     F.content_type == types.ContentType.TEXT)
        return self.router

    async def handler_voice_expense_with_ai(self, message: types.Message, bot: Bot):
        user_id = message.from_user.id
        await UsersDbUtils(self.db, self.logger).create_user_if_not_exist(user_id)
        progress_msg = await message.reply(AI_PROGRESS_MSG, disable_notification=True)

        voice = message.voice
        file_info = await bot.get_file(voice.file_id)
        file_path = file_info.file_path
        destination = Path(self.audio_storage_path, f"{voice.file_unique_id}.ogg")
        await bot.download_file(file_path, destination)

        try:
            users_comments = await UsersPropertiesDbUtils(self.db, self.logger) \
                .get_user_property(user_id, UserProperty.COMMENTS)

            ai_response = await GeminiAIProvider(AIModel.GEMINI_2_FLASH).ask_about_file(
                destination,
                PromptTemplateExpenseFromFreeInput({
                    "${today}": dt.now().date().isoformat(),
                    "${user_comments}": str(users_comments)
                }).render()
            )
            ai_expense_payload = json.loads(ai_response)
            expense_draft = await self.__refine_ai_response(ai_expense_payload, user_id)
            await self.report_expense_details(bot, expense_draft)
        except Exception as e:
            self.logger.log(self, user=user_id, extra_text=f"Exception occured during AI request handling: {e}")
        finally:
            if destination.exists():
                os.remove(destination)
            await progress_msg.delete()
            await message.delete()

    async def handler_text_expense_with_ai(self, message: types.Message, bot: Bot):
        user_id = message.from_user.id
        await UsersDbUtils(self.db, self.logger).create_user_if_not_exist(user_id)
        progress_msg = await message.reply(AI_PROGRESS_MSG, disable_notification=True)

        users_comments = await UsersPropertiesDbUtils(self.db, self.logger) \
                .get_user_property(user_id, UserProperty.COMMENTS)

        ai_response = await GeminiAIProvider(AIModel.GEMINI_2_FLASH).ask(
            PromptTemplateExpenseFromFreeInput({
                "${today}": dt.now().date().isoformat(),
                "${user_comments}": str(users_comments),
                "${user_input}": message.text
            }).render()
        )
        ai_expense_payload = json.loads(ai_response)
        expense_draft = await self.__refine_ai_response(ai_expense_payload, user_id)
        await self.report_expense_details(bot, expense_draft)
        await progress_msg.delete()
        await message.delete()

    async def __refine_ai_response(
        self,
        ai_expense_payload: dict,
        user_id: int
    ) -> ExpenseUncommited:
        if "currency" not in ai_expense_payload:
            ai_expense_payload["currency"] = await UsersPropertiesDbUtils(self.db, self.logger) \
                .get_user_property(user_id, UserProperty.BASE_CURRENCY)
        if "category" in ai_expense_payload:
            category_name = ai_expense_payload.pop("category")
            category = await CategoriesDbUtils(self.db, self.logger) \
                .get_category_by_name(category_name)
            ai_expense_payload["category_id"] = category.category_id

        expense_draft = ExpenseUncommited(self.logger)
        expense_draft.user_id = user_id
        expense_draft.patch(ai_expense_payload)
        await expense_draft.sync_currency_rates(self.db)
        return expense_draft
