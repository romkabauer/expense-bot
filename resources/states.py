from aiogram.fsm.state import State, StatesGroup


class States(StatesGroup):
    other_date_input = State()
    reading_expense_category = State()
    entering_amount = State()
    commenting = State()
    shortcut = State()
    shortcut_parsing = State()

    settings_request_values_for_category = State()
    settings_parse_values_for_category = State()
    settings_choosing_active_categories = State()
    settings_ask_shortcut_amount = State()
    settings_parse_shortcut_amount = State()
    settings_ask_shortcut_name = State()
    settings_delete_shortcut = State()

    settings_sch_jobs_choose_job_to_add = State()
    settings_sch_jobs_confirm_deletion = State()
    settings_sch_jobs_choose_attribute_to_edit = State()
    settings_sch_jobs_request_new_attribute_value = State()
    settings_sch_jobs_parse_new_time = State()
    settings_sch_jobs_parse_new_weekday = State()

    edit_mode = State()
    edit_date = State()
    edit_category = State()
    edit_amount = State()
    edit_comment = State()
    delete_mode = State()
