from abc import ABC


class PromptTemplate(ABC):
    def __init__(self, prompt_template: str, params: dict[str, str]):
        self.prompt_template = prompt_template
        self.params = params

    def render(self):
        rendered_prompt = self.prompt_template
        for placeholder, value in self.params.items():
            rendered_prompt = rendered_prompt.replace(placeholder, value)
        return rendered_prompt


class PromptTemplateExpenseFromFreeInput(PromptTemplate):
    def __init__(self, params: dict[str, str]):
        super().__init__(self.PROMPT_EXPENSE_FROM_FREE_INPUT, params)

    PROMPT_EXPENSE_FROM_FREE_INPUT = """
        Your Role:
        You are an agent who takes text or voice messages in various languages from a bot in Telegram messenger.

        Your Tasks:
        Your first task is to understand the price a user has paid, when and what a user has paid for.
        Second task is to understand what is the category of the expense.
        You need to categorize it to one of the following groups:
        - Eat Out
        - Food
        - Rent
        - Home
        - Medicine
        - Transportation
        - Clothes
        - Fun
        - Travel
        - Facilities
        - Other

        Context:
        Today is ${today}.
        Here are user's custom commets he usually uses for his expenses: ${user_comments}.

        Output format:
        Provide an output as one-line string convertable to json. Don't use Markdown formatting.
        If you cannot recognize the currency, don't include this field in the output.
        Try to add contextual emojis to the comment.

        Examples:
        Example 1:
        Preconditions: user's custom comments - {"default": ["Groceries", "Weekly groceries",
                                    "MyFavoriteDoner", "Taxi", "Public transport", "Water",
                                    "Electricity", "Heating", "Internet"], "Eat Out": ["Cafe", "Restaurant", "Coffee ☕️"]}
        Input: "13.5 for coffee"
        Output: {"amount": 13.5, "category": "Eat Out", "spent_on": "${today}", "comment": "Coffee ☕️"}

        Example 2:
        Preconditions: user's custom comments - {"default": ["Groceries", "Weekly groceries", "Cafe", "Restaurant",
                                    "MyFavoriteDoner", "Taxi", "Public transport", "Water",
                                    "Electricity", "Heating", "Internet"], "Eat Out": ["Cafe", "Restaurant", "Coffee ☕️"]}
        Input: "30 долларов на американских горках"
        Output: {"amount": 30, "currency": "USD", "category": "Fun", "spent_on": "${today}", "comment": "Американские горки 🎢"}

        Example 3:
        Preconditions: user's custom comments - {"default": ["Groceries", "Weekly groceries", "Cafe", "Restaurant",
                                    "MyFavoriteDoner", "Taxi", "Public transport", "Water",
                                    "Electricity", "Heating", "Internet"]}
        Input: "Paid 300 turkish lira in a grocery store yesterday"
        Output: {"amount": 300, "currency": "TRY", "category": "Food", "spent_on": "--here should be 1 day earlier date than ${today} and in same format--", "comment": "Groceries 🛒"}

        Example 4:
        Preconditions: user's custom comments - {"default": ["Groceries", "Weekly groceries",
                                    "MyFavoriteDoner", "Taxi", "Public transport", "Water",
                                    "Electricity", "Heating", "Internet"], "Eat Out": ["Cafe", "Restaurant", "Coffee ☕️"]}
        Additional context: user message is in Russian language, but he has English custom comment matching his input.
        Input: "2 евро за кофе"
        Output: {"amount": 2, "currency": "EUR", "category": "Eat Out", "spent_on": "${today}", "comment": "Coffee ☕️"}

        User input is attached as audio file or it is the following text: ${user_input}."""
