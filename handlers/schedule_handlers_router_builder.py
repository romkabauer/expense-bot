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

from handlers.abstract_router_builder import AbstractRouterBuilder
from database.database import DatabaseFacade
from logger import Logger
from resources import (
    interface_messages,
    keyboards,
    analytics_sql_templates,
    scheduler_job_templates
)


class ScheduleHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self, scheduler: ContextSchedulerDecorator):
        super().__init__()
        self.router = Router(name=self.__class__.__name__)
        self.scheduler = scheduler
        self.scheduled_jobs_map = {
            "weekly_report": {
                "name": "weekly_report_",
                "scheduled_query": analytics_sql_templates.DEFAULT_WEEKLY_REPORT,
                "default_cron_schedule": CronTrigger.from_crontab('*/1 * * * *', 'Etc/GMT-3')
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
        self.router.callback_query.register(self.handler_confirm_job_deletion,
                                            self.state.settings_sch_jobs_confirm_deletion)
        self.router.callback_query.register(self.handler_delete_job,
                                            F.data == "confirm_job_deletion")
        self.router.callback_query.register(self.handler_cancel_job_deletion,
                                            F.data == "cancel_job_deletion")
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
                                           parse_mode="MarkdownV2",
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.settings_sch_jobs_choose_job_to_add)

    async def handler_add_job(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        try:
            self.scheduler.ctx.add_instance(self.logger, Logger)
            self.scheduler.ctx.add_instance(self.db, DatabaseFacade)
        except OverridingServiceException:
            pass

        try:
            self.scheduler.add_job(scheduler_job_templates.job_send_message,
                                   self.scheduled_jobs_map[callback.data].get("default_cron_schedule"),
                                   id=self.scheduled_jobs_map[callback.data].get("name", "default_job_name_") +
                                        str(callback.from_user.id),
                                   kwargs={
                                       "user_id": callback.from_user.id,
                                       "logger": self.logger,
                                       "db": self.db
                                   })
            await callback.answer(interface_messages.SETTINGS_SET_SUCCESS)
        except ConflictingIdError:
            await callback.answer("Job type already scheduled!")

        await callback.message.delete()
        await state.clear()

    async def handler_choose_job_to_delete(self, callback: types.CallbackQuery, state: FSMContext):
        jobs = self.scheduler.get_jobs()
        user_jobs = [job.id for job in jobs if str(callback.from_user.id) in job.id]
        if not user_jobs:
            await callback.answer("No scheduled jobs.")
            await callback.message.delete()
            await state.clear()
            return

        msg = await callback.message.reply(interface_messages.SETTINGS_SCHEDULED_JOBS_TASKS_TO_DELETE,
                                           reply_markup=keyboards.build_listlike_keyboard(
                                               entities=user_jobs,
                                               max_items_in_a_row=2
                                           ),
                                           parse_mode="MarkdownV2",
                                           disable_notification=True)
        await state.update_data({"user_jobs": user_jobs})
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.settings_sch_jobs_confirm_deletion)

    async def handler_confirm_job_deletion(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text(text=f"Please confirm deletion of job: {callback.data}")
        await callback.message.edit_reply_markup(str(callback.message.message_id),
                                                 keyboards.build_listlike_keyboard(
                                                     ["confirm_job_deletion", "cancel_job_deletion"],
                                                     title_button_names=True
                                                 ))
        await state.update_data({"job_under_edit": callback.data})
        await state.set_state()

    async def handler_cancel_job_deletion(self, callback: types.CallbackQuery, state: FSMContext):
        user_data = await state.get_data()
        user_jobs = user_data.get("user_jobs")

        await callback.message.edit_text(text=interface_messages.SETTINGS_SCHEDULED_JOBS_TASKS_TO_DELETE,
                                         parse_mode="MarkdownV2")
        await callback.message.edit_reply_markup(str(callback.message.message_id),
                                                 reply_markup=keyboards.build_listlike_keyboard(
                                                     entities=user_jobs,
                                                     max_items_in_a_row=2
                                                 ))
        await state.set_state(self.state.settings_sch_jobs_confirm_deletion)

    async def handler_delete_job(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        job_data = await state.get_data()
        self.scheduler.remove_job(job_id=job_data.get("job_under_edit"))
        await self.delete_init_instruction(callback.from_user.id, state, bot)
        await callback.answer("Job deleted!")
        await state.clear()

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
