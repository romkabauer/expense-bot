import time
import re
from datetime import datetime as dt, timedelta as td
from datetime import timezone

from aiogram import (
    types,
    Router,
    Bot,
    F
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from handlers.abstract_router_builder import AbstractRouterBuilder
from resources import (
    interface_messages,
    keyboards,
    bi_interface,
    analytics_sql_templates
)
from database.models import (
    UsersProperties,
    Properties
)


class ScheduleHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self):
        super().__init__()
        self.router = Router(name=self.__class__.__name__)
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.scheduled_jobs_map = {
            "weekly_report": {
                "scheduled_query": analytics_sql_templates.DEFAULT_WEEKLY_REPORT,
                "default_cron_schedule": CronTrigger.from_crontab('*/5 * * * *', 'Etc/GMT-3')
                # "default_cron_schedule": CronTrigger.from_crontab('30 20 * * sun', 'Etc/GMT-3')
            }
        }

    def build_default_router(self):
        self.router.callback_query.register(self.handler_scheduled_jobs_menu,
                                            F.data == "scheduled_jobs")

        self.router.callback_query.register(self.handler_choose_job_to_add,
                                            F.data == "add_job")
        self.router.callback_query.register(self.handler_add_job,
                                            self.state.settings_sch_jobs_choose_job_to_add)
        self.router.callback_query.register(self.handler_choose_job_to_edit,
                                            F.data == "edit_job")
        self.router.callback_query.register(self.handler_choose_job_to_delete,
                                            F.data == "delete_job")
        return self.router

    async def handler_scheduled_jobs_menu(self, callback: types.CallbackQuery, state: FSMContext):
        msg = await callback.message.reply("You can add/edit/delete job:",
                                           reply_markup=keyboards.build_listlike_keyboard(
                                               entities=['add_job', 'edit_job', 'delete_job'],
                                               max_items_in_a_row=3
                                           ),
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)

    async def handler_choose_job_to_add(self, callback: types.CallbackQuery, state: FSMContext):
        msg = await callback.message.reply(interface_messages.SETTINGS_SCHEDULED_JOBS_TASKS_TO_ADD,
                                           reply_markup=keyboards.build_listlike_keyboard(
                                               entities=list(self.scheduled_jobs_map.keys()),
                                               max_items_in_a_row=3
                                           ),
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.settings_sch_jobs_choose_job_to_add)

    async def handler_add_job(self, callback: types.CallbackQuery, state: FSMContext):
        self.scheduler.add_job(self.job_send_hello,
                               self.scheduled_jobs_map[callback.data].get("default_cron_schedule"),
                               kwargs={
                                   "message": callback.message
                               })
        await callback.message.delete()
        await callback.answer(interface_messages.SETTINGS_SET_SUCCESS)
        await state.clear()

    async def handler_choose_job_to_delete(self, callback: types.CallbackQuery, state: FSMContext):
        pass

    async def handler_choose_job_to_edit(self, callback: types.CallbackQuery):
        is_no_jobs = False
        # with self.db.get_session() as db:
        #     scheduled_jobs_props = db.query(UsersProperties).filter(
        #         UsersProperties.user_id == callback.from_user.id,
        #         UsersProperties.properties.has(
        #             Properties.property_name == "scheduled_jobs"
        #         )
        #     ).first()

        # if scheduled_jobs_props:
            # say no jobs to edit, redirect to adding jobs
            # is_no_jobs = True
            # return
        # else:
            # add property to db and say no jobs to edit
            # return
        pass

    @staticmethod
    async def job_send_hello(message: types.Message):
        await message.answer("Hello!")
