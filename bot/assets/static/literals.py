from enum import Enum


class UserProperty(Enum):
    BASE_CURRENCY = "base_currency"
    CATEGORIES = "categories"
    AMOUNTS = "amounts"
    COMMENTS = "comments"
    SHORTCUTS = "shortcuts"
    SCHEDULED_JOBS = "scheduled_jobs"


class ShortcutLabels(Enum):
    SHORTCUT_PAYLOADS = "shortcut_payloads"

    SHORTCUT_PAYLOAD_CATEGORY = "category"
    SHORTCUT_PAYLOAD_AMOUNT = "amount"


class UILabels(Enum):
    DEFAULT = "default"

    EXPENSE_DRAFT = "expense_draft"
    INIT_INSTRUCTION = "init_instruction"

    TODAY = "today"
    YESTERDAY = "yesterday"
    ANOTHER_DATE = "another_date"

    EDIT = "edit"
    EDIT_DATE = "edit_date"
    EDIT_CATEGORY = "edit_category"
    EDIT_AMOUNT = "edit_amount"
    EDIT_COMMENT = "edit_comment"

    SETTINGS_CATEGORIES = "settings_categories"
    SETTINGS_PROPERTY = "settings_property"
    SETTINGS_PROPERTY_CATEGORY = "settings_property_category"
    SETTINGS_SHORTCUTS_ADD_EDIT = "add_or_overwrite_shortcut"
    SETTINGS_SHORTCUTS_DELETE = "delete_shortcut"

    JOB_ADD = "add_job"
    JOB_DELETE = "delete_job"
    JOB_EDIT = "edit_job"
    JOB_CANCAEL_DELETION = "cancel_job_deletion"
    JOB_CONFIRM_DELETION = "confirm_job_deletion"
    JOB_SCHEDULED_TIME = "scheduled_time"
    JOB_SCHEDULED_WEEKDAY = "scheduled_weekday"
    JOB_USER_JOBS = "user_jobs"
    JOB_UNDER_EDIT = "job_under_edit"

    BACK = "back"
    CONFIRM = "Confirm!"

    DELETE = "delete"
    DELETE_CONFIRM = "confirm_deletion"
    DELETE_ABORT = "abort_deletion"


class UpsertStatus(Enum):
    INSERTED = "inserted"
    UPDATED = "updated"
    ERROR = "error"
