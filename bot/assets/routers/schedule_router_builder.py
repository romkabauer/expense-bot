from datetime import datetime as dt

from aiogram import (
    types,
    Router,
    Bot,
    F
)
from aiogram.fsm.context import FSMContext
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler_di.decorator import ContextSchedulerDecorator
from rodi import OverridingServiceException

from static.literals import UserProperty
from static import analytics_sql_templates
from static.interface_messages import *
from utils.messaging import *
from utils import scheduler_job_templates
from routers.abstract_router_builder import AbstractRouterBuilder
from database.database import DatabaseFacade
from logger import Logger


class ScheduleRouterBuilder(AbstractRouterBuilder):
    def __init__(self, logger: Logger, scheduler: ContextSchedulerDecorator):
        super().__init__(logger)
        self.router = Router(name=self.__class__.__name__)
        self.scheduler = scheduler
        self.scheduled_jobs_map = {
            "weekly_report": {
                "name": "weekly_report_",
                "job_executable": scheduler_job_templates.job_send_message,
                "scheduled_query": analytics_sql_templates.DEFAULT_WEEKLY_REPORT,
                "default_cron_schedule": CronTrigger.from_crontab('30 17 * * sun')
                # "default_cron_schedule": CronTrigger.from_crontab('*/1 * * * *')
            }
        }

    @staticmethod
    def pretty_print_job(job_id: str):
        return " ".join([x.capitalize() for x in job_id.split("_")[:-1]])

    def build_default_router(self):
        self.router.callback_query.register(self.handler_scheduled_jobs_menu,
                                            F.data == UserProperty.SCHEDULED_JOBS.value)

        self.router.callback_query.register(self.handler_choose_job_to_add,
                                            F.data == UILabels.JOB_ADD.value)
        self.router.callback_query.register(self.handler_add_job,
                                            self.state.settings_sch_jobs_choose_job_to_add)
        self.router.callback_query.register(self.handler_choose_job_to_edit,
                                            F.data.in_({UILabels.JOB_EDIT.value, UILabels.JOB_DELETE.value}))
        self.router.callback_query.register(self.handler_confirm_job_deletion,
                                            self.state.settings_sch_jobs_confirm_deletion)
        self.router.callback_query.register(self.handler_delete_job,
                                            F.data == UILabels.JOB_CONFIRM_DELETION.value)
        self.router.callback_query.register(self.handler_cancel_job_deletion,
                                            F.data == UILabels.JOB_CANCAEL_DELETION.value)
        self.router.callback_query.register(self.handler_choose_attribute_to_edit,
                                            self.state.settings_sch_jobs_choose_attribute_to_edit)
        self.router.callback_query.register(self.handler_edit_job_time,
                                            self.state.settings_sch_jobs_request_new_attribute_value,
                                            F.data == UILabels.JOB_SCHEDULED_TIME.value)
        self.router.callback_query.register(self.handler_edit_job_weekday,
                                            self.state.settings_sch_jobs_request_new_attribute_value,
                                            F.data == UILabels.JOB_SCHEDULED_WEEKDAY.value)
        self.router.message.register(self.handler_parse_new_job_time,
                                     self.state.settings_sch_jobs_parse_new_time)
        self.router.callback_query.register(self.handler_parse_new_job_weekday,
                                            self.state.settings_sch_jobs_parse_new_weekday,
                                            F.data.in_(
                                                {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
                                            ))
        return self.router

    async def handler_scheduled_jobs_menu(self, callback: types.CallbackQuery, state: FSMContext):
        await self.send_silent_reply(
            callback,
            state,
            SETTINGS_SCHEDULED_JOBS_EDIT_MENU,
            (KBBuilder()
                .set_buttons(
                    [UILabels.JOB_ADD.value,
                    UILabels.JOB_EDIT.value,
                    UILabels.JOB_DELETE.value]
                )
                .inline())
        )
        await callback.message.delete()

    async def handler_choose_job_to_add(self, callback: types.CallbackQuery, state: FSMContext):
        await self.send_silent_reply(
            callback,
            state,
            SETTINGS_SCHEDULED_JOBS_TASKS_TO_ADD,
            KBBuilder().set_buttons(list(self.scheduled_jobs_map.keys())).inline(),
            is_msg_text_markdown=True
        )
        await state.set_state(self.state.settings_sch_jobs_choose_job_to_add)
        await callback.message.delete()

    async def handler_add_job(self, callback: types.CallbackQuery, state: FSMContext):
        try:
            self.scheduler.ctx.add_instance(self.logger, Logger)
            self.scheduler.ctx.add_instance(self.db, DatabaseFacade)
        except OverridingServiceException:
            pass

        try:
            self.scheduler.add_job(
                self.scheduled_jobs_map[callback.data].get("job_executable"),
                self.scheduled_jobs_map[callback.data].get("default_cron_schedule"),
                id=self.scheduled_jobs_map[callback.data].get("name", "default_job_name_") +
                    str(callback.from_user.id),
                kwargs={
                    "user_id": callback.from_user.id,
                    "logger": self.logger,
                    "db": self.db
                }
            )
            await callback.answer(SUCCESS_SETTINGS_SET)
        except ConflictingIdError:
            await callback.answer(ERROR_SCHEDULED_JOB_TYPE_EXISTS)

        await callback.message.delete()
        await state.clear()

    async def handler_choose_job_to_edit (self, callback: types.CallbackQuery, state: FSMContext):
        jobs = self.scheduler.get_jobs()
        user_jobs = [job.id for job in jobs if str(callback.from_user.id) in job.id]
        if not user_jobs:
            await callback.answer("No scheduled jobs.")
            await callback.message.delete()
            await state.clear()
            return

        await self.send_silent_reply(
            callback,
            state,
            SETTINGS_SCHEDULED_JOBS_TASKS_TO_EDIT,
            KBBuilder().set_buttons(user_jobs).set_max_items_in_a_row(2).inline()
        )
        await state.update_data({UILabels.JOB_USER_JOBS.value: user_jobs})
        await callback.message.delete()
        if callback.data == UILabels.JOB_DELETE.value:
            await state.set_state(self.state.settings_sch_jobs_confirm_deletion)
        else:
            await state.set_state(self.state.settings_sch_jobs_choose_attribute_to_edit)

    async def handler_confirm_job_deletion(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text(text=f"Please confirm deletion of job: {callback.data}")
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            (KBBuilder()
                .set_buttons(
                    [UILabels.JOB_CONFIRM_DELETION.value, UILabels.JOB_CANCAEL_DELETION.value]
                )
                .inline())
        )
        await state.update_data({UILabels.JOB_UNDER_EDIT.value: callback.data})
        await state.set_state()

    async def handler_cancel_job_deletion(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Handler for canceling a job deletion.

        This handler is called when the user cancels the deletion of a job.
        It changes the text of the message to the starting msg and reverts
        the reply markup to the keyboard with the list of jobs.
        """
        user_data = await state.get_data()
        user_jobs = user_data.get(UILabels.JOB_USER_JOBS.value)

        await callback.message.edit_text(
            text=escape_markdown(SETTINGS_SCHEDULED_JOBS_TASKS_TO_EDIT, 2),
            parse_mode="MarkdownV2"
        )
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            reply_markup=KBBuilder().set_buttons(user_jobs).set_max_items_in_a_row(2).inline()
        )
        await state.set_state(self.state.settings_sch_jobs_confirm_deletion)

    async def handler_delete_job(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        """
        Handler for deleting a job.

        This handler is called when the user confirms job deletion.
        It removes the job from the scheduler and clears the state.
        """
        job_data = await state.get_data()
        self.scheduler.remove_job(job_id=job_data.get(UILabels.JOB_UNDER_EDIT.value))
        await self.delete_init_instruction(callback.from_user.id, state, bot)
        await callback.answer("Job deleted!")
        await state.clear()

    async def handler_choose_attribute_to_edit(self, callback: types.CallbackQuery, state: FSMContext):
        await state.update_data({UILabels.JOB_UNDER_EDIT.value: callback.data})
        await self.send_silent_reply(
            callback,
            state,
            SETTINGS_SCHEDULED_JOBS_ATTRIBUTES_TO_EDIT,
            (KBBuilder()
                .set_buttons(
                    [UILabels.JOB_SCHEDULED_TIME.value,
                    UILabels.JOB_SCHEDULED_WEEKDAY.value]
                )
                .inline())
        )
        await callback.message.delete()
        await state.set_state(self.state.settings_sch_jobs_request_new_attribute_value)

    async def handler_edit_job_time(self, callback: types.CallbackQuery, state: FSMContext):
        await self.send_silent_reply(
            callback,
            state,
            SETTINGS_SCHEDULED_JOBS_EDIT_TIME
        )
        await callback.message.delete()
        await state.set_state(self.state.settings_sch_jobs_parse_new_time)

    async def handler_parse_new_job_time(self, message: types.Message, state: FSMContext, bot: Bot):
        data = await state.get_data()
        await self.delete_init_instruction(message.chat.id, state, bot)

        try:
            dt.strptime(message.text.strip(), "%H:%M")
        except ValueError:
            await self.send_silent_reply(
                message,
                state,
                ERROR_TIME_FORMAT + SETTINGS_SCHEDULED_JOBS_EDIT_TIME
            )
            await message.delete()
            return

        new_job_hour = message.text.split(":")[0]
        new_job_min = message.text.split(":")[1]
        job_id = data.get(UILabels.JOB_UNDER_EDIT.value)
        next_run_time = self.scheduler.get_job(job_id).next_run_time
        self.scheduler.reschedule_job(
            job_id,
            trigger=CronTrigger.from_crontab(
                f'{new_job_min} {new_job_hour} * * {next_run_time.weekday()}'
            )
        )
        await message.answer(
            f"Job \"{self.pretty_print_job(data.get(UILabels.JOB_UNDER_EDIT.value))}\" "
            f"will be executing every {next_run_time.strftime('%a')} at "
            f"{new_job_hour}:{new_job_min} UTC.",
            disable_notification=True
        )
        await message.delete()
        await state.clear()

    async def handler_edit_job_weekday(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.message.reply(
            escape_markdown(SETTINGS_SCHEDULED_JOBS_EDIT_WEEKDAY, 2),
            reply_markup=(KBBuilder()
                .set_buttons(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
                .inline()),
            parse_mode="MarkdownV2",
            disable_notification=True
        )
        await callback.message.delete()
        await state.set_state(self.state.settings_sch_jobs_parse_new_weekday)

    async def handler_parse_new_job_weekday(self, callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        job_id = data.get(UILabels.JOB_UNDER_EDIT.value)
        next_run_time = self.scheduler.get_job(job_id).next_run_time
        self.scheduler.reschedule_job(
            job_id,
            trigger=CronTrigger.from_crontab(
                f'{next_run_time.minute} {next_run_time.hour} * * {callback.data}'
            )
        )
        await callback.message.answer(
            f"Job \"{self.pretty_print_job(data.get('job_under_edit'))}\" "
            f"will be executing every {callback.data.capitalize()} at "
            f"{next_run_time.hour}:{next_run_time.minute:02} UTC.",
            disable_notification=True
        )
        await callback.message.delete()
        await state.clear()
