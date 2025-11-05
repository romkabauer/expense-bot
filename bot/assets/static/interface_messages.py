ASK_EXPENSE_DATE = "📅When did you spend?"
ASK_EXPENSE_DATE_FORMAT_HINT = "🔤Input expense date in format '2023-10-13':"
ASK_EXPENSE_CATEGORY = "🛍️What is the expense category?"
ASK_SHORTCUT = "💵Choose frequent payment shortcut:"
ASK_EXPENSE_AMOUNT = ("💵What is an amount paid?\n"
                      "Examples:\n"
                      "    100.11\n"
                      "    10 USD\n"
                      "    10 AMD\n"
                      "Amount will be recorded along "
                      "with conversion rate on the expense date")
ASK_COMMENT = "🔤Choose any comment to add or write custom one:"
ASK_COMMENT_CUSTOM = "🔤Write custom comment:"
HINT_COPY_COMMENT = "🔶You can copy current comment tapping on it.\n\n"

SETTINGS_START = "🔤Choose setting to change:"
SETTINGS_NOT_IMPLEMENTED = ("🙈Sorry, changes for this setting are not available yet! "
                            "But I'm working on it!")
SETTINGS_CATEGORIES_VISIBILITY = "Pick categories you would like to see while adding new expense:"
SETTINGS_CATEGORIES_CHOICE = "🔤Choose category to set values for:"
SETTINGS_BASE_CURRENCY_CHOICE = ("🔤Choose base (default) currency for your expenses.\n"
                                 "Notes:\n"
                                 "TRY - Turkish Lira\n"
                                 "GEL - Georgian Lari\n"
                                 "RSD - Serbian Dinar\n"
                                 "AMD - Armenian Dram\n")
SETTINGS_REQUEST_VALUES_FOR_CATEGORY = ("Please, specify default values for this category\.\n"
                                        "Examples:\n"
                                        "_1, 1\.50, 2, 3\.99_ \- decimal parts of values for amounts "
                                        "within categories should be divided by point, "
                                        "values itself should be divided by comma\n"
                                        "_Cat1, Cat2, Cat 3, Cat\_4_ \- values for comments "
                                        "within categories should be divided by comma")

SETTINGS_ASK_SHORTCUT_NAME = ("🔤 What will be the shortcut name?\n"
                            "If you provide already existing name, it will be overwritten.")

SETTINGS_SCHEDULED_JOBS_EDIT_MENU = "You can add/edit/delete job:"
SETTINGS_SCHEDULED_JOBS_TASKS_TO_ADD = ("Choose job to schedule\.\n\n"
                                        "*Weekly Report* \- "
                                        "bot will send summary of expenses for last week every Sunday, "
                                        "at 20:30 UTC\+3 by default")
SETTINGS_SCHEDULED_JOBS_TASKS_TO_EDIT = ("Choose job to edit/delete.\n\n")
SETTINGS_SCHEDULED_JOBS_ATTRIBUTES_TO_EDIT = ("Choose job attribute to edit.\n\n")
SETTINGS_SCHEDULED_JOBS_EDIT_TIME = ("Enter new job time in UTC+0 timezone in format HH:MM. For example, 23:15.")
SETTINGS_SCHEDULED_JOBS_EDIT_WEEKDAY = ("Choose weekday to send job on.")

ERROR_EXPENSE_AMOUNT_FORMAT = ("⛔️Wrong format for spending amount(s).\n"
                               "🔤Should contain only positive numbers "
                               "with . decimal separator and currency label:")
ERROR_DATE_FORMAT = "⛔️Wrong date format.\n"
ERROR_TIME_FORMAT = "⛔️Wrong time format.\n"
ERROR_DATE_TIMELINESS = "⛔️Input cannot contain future dates.\n"
ERROR_NO_SHORTCUTS = "⛔No shortcuts registered. Please use /settings command to set one up."
ERROR_SCHEDULED_JOB_TYPE_EXISTS = "Job type already scheduled!"
ERROR_EXPENSE_DELETION_FAILED = "⚠️Deletion failed. Please try again or contact @romka_bauer."

SUCCESS_DEFAULT_SETUP = ("✅Your profile is set.\n\n"
                        "⚙️/settings - to change default settings\n\n"
                        "💵/add - to add your expense\n\n"
                        "📊/analytics - to set analytics profile")
SUCCESS_RESET = ("✅Default profile configuration is set. "
                "Your previous settings were rewritten.\n\n"
                "⚙️/settings - to change default settings\n\n"
                "💵/add - to add your expense\n\n"
                "📊/analytics - to set analytics profile")

SUCCESS_RECORD = "✅*Expense has been recorded\!*\n\nRecorded data:\n"
FAILED_RECORD = "⚠️*NOT recorded\!*\n\nData to be recorded:\n"
SUCCESS_SETTINGS_SET = "✅Setting set successfully!"
FAILED_SETTINGS_SET = "⛔️Setting was not set!"

AI_PROGRESS_MSG = "🤖 Your voice message is being handeled by AI, it may take 5-10 seconds..."

HEALTH_CHECK = ("I'm alive, everything is perfect🙃 "
                "This message will be deleted in 2 seconds.")
