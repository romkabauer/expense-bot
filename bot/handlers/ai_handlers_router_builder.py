import json
import os
from pathlib import Path
import asyncio
from datetime import datetime as dt

from aiogram import (
    types,
    Router,
    F,
    Bot
)

from resources.ai.providers.gemini_provider import GeminiAIProvider
from resources.ai.providers import AIModel
from resources.ai.prompt_templates import (
    PromptTemplateExpenseFromFreeInput
)
from database.models import (
    UsersProperties,
    Properties
)
from handlers.abstract_router_builder import AbstractRouterBuilder
from logger import Logger

class AIHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self, logger: Logger):
        super().__init__(logger)
        self.router = Router(name=self.__class__.__name__)
        path = Path("/app/audio_storage")
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
        progress_msg = await message.reply(
            "🤖 Your voice message is being handeled by AI, it may take 5-10 seconds...",
            disable_notification=True
        )

        voice = message.voice
        file_info = await bot.get_file(voice.file_id)
        file_path = file_info.file_path
        destination = Path(self.audio_storage_path, f"{voice.file_unique_id}.ogg")
        await bot.download_file(file_path, destination)

        try:
            with self.db.get_session() as db:
                users_comments = db.query(UsersProperties.property_value).filter(
                    UsersProperties.properties.has(Properties.property_name == "comments"),
                    UsersProperties.user_id == user_id
                ).first()[0]

            ai_response = await GeminiAIProvider(AIModel.GEMINI_2_FLASH).ask_about_file(
                destination,
                PromptTemplateExpenseFromFreeInput({
                    "${today}": dt.now().date().isoformat(),
                    "${user_comments}": str(users_comments)
                }).render()
            )
            expense_payload = json.loads(ai_response)
            expense_payload = await self.__refine_ai_response(expense_payload, message)
            await self.report_expense_details(expense_payload)
        except Exception as e:
            self.logger.log(self, user_id, f"Exception occured during AI request handling: {e}")
        finally:
            if destination.exists():
                os.remove(destination)
            await progress_msg.delete()
            await message.delete()

    async def handler_text_expense_with_ai(self, message: types.Message):
        user_id = message.from_user.id
        progress_msg = await message.reply(
            "🤖 Your message is being handeled by AI, it may take 5-10 seconds...",
            disable_notification=True
        )

        with self.db.get_session() as db:
            users_comments = db.query(UsersProperties.property_value).filter(
                UsersProperties.properties.has(Properties.property_name == "comments"),
                UsersProperties.user_id == user_id
            ).first()[0]

        ai_response = await GeminiAIProvider(AIModel.GEMINI_2_FLASH).ask(
            PromptTemplateExpenseFromFreeInput({
                "${today}": dt.now().date().isoformat(),
                "${user_comments}": str(users_comments),
                "${user_input}": message.text
            }).render()
        )
        expense_payload = json.loads(ai_response)
        expense_payload = await self.__refine_ai_response(expense_payload, message)
        await self.report_expense_details(expense_payload)
        await progress_msg.delete()
        await message.delete()

    async def __refine_ai_response(self, expense_payload: dict, message: types.Message) -> dict:
        expense_payload["message"] = message
        expense_payload["user_id"] = message.from_user.id
        if not "currency" in expense_payload:
            expense_payload["currency"] = await self.get_base_currency(message.from_user.id)
        expense_payload["rates"] = await self.get_rates_on_expense_date(
            expense_payload["spent_on"],
            expense_payload["currency"]
        )
        return expense_payload
