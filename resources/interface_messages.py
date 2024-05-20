DEFAULT_SETUP_SUCCESSFUL = ("✅Your profile is set.\n\n"
                            "⚙️/settings - to change default settings\n\n"
                            "💵/add - to add your expense\n\n"
                            "📊/analytics - to set analytics profile")
RESET_SUCCESSFUL = ("✅Default profile configuration is set. "
                    "Your previous settings were rewritten.\n\n"
                    "⚙️/settings - to change default settings\n\n"
                    "💵/add - to add your expense\n\n"
                    "📊/analytics - to set analytics profile")
ERROR_ADD_BEFORE_SETUP = "⚠️Please setup your bot firstly, call /start."

SETTINGS_START = "🔤Choose setting to change:"
SETTINGS_NOT_IMPLEMENTED = ("🙈Sorry, changes for this setting are not available yet! "
                            "But I'm working on it!")
SETTINGS_CATEGORIES_CHOICE = "🔤Choose category to set values for:"
SETTINGS_BASE_CURRENCY_CHOICE = ("🔤Choose base (default) currency for your expenses.\n"
                                 "Notes:\n"
                                 "TRY - Turkish Lira\n"
                                 "GEL - Georgian Lari\n"
                                 "RSD - Serbian Dinar\n"
                                 "AMD - Armenian Dram\n")
SETTINGS_SET_SUCCESS = "✅Setting set successfully!"
SETTINGS_SET_FAILURE = "⛔️Setting was not set!"
SETTINGS_REQUEST_VALUES_FOR_CATEGORY = ("Please, specify default values for this category\.\n"
                                        "Examples:\n"
                                        "_1, 1\.50, 2, 3\.99_ \- decimal parts of values for amounts "
                                        "within categories should be divided by point, "
                                        "values itself should be divided by comma\n"
                                        "_Cat1, Cat2, Cat 3, Cat\_4_ \- values for comments "
                                        "within categories should be divided by comma")

ASK_EXPENSE_DATE = "📅When did you spend?"
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

INPUT_DATE_FORMAT = "🔤Input expense date in format '2023-10-13':"

WRONG_EXPENSE_AMOUNT_FORMAT = ("⛔️Wrong format for spending amount(s).\n"
                               "🔤Should contain only positive numbers "
                               "with . decimal separator and currency label:")
WRONG_DATE_FORMAT = "⛔️Wrong date format.\n"
WRONG_DATE_TIMELINESS = "⛔️Input cannot contain future dates.\n"
WRONG_NO_SHORTCUTS = "⛔No shortcuts registered. Please use /settings command to set one up."

SUCCESS_RECORD = "✅*Expense has been recorded!*\n\nRecorded data:\n"
FAILED_RECORD = "⛔️*NOT recorded!*\n\nData to be recorded:\n"

HEALTH_CHECK = ("I'm alive, everything is perfect🙃 "
                "This message will be deleted in 2 seconds.")
