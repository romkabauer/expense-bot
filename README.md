# Expense Bot

💸[Start using Expense Bot](https://t.me/superset_expense_bot) 💸

## What you can do with this bot?

- 💵 Enter your expenses [DEMO](https://drive.google.com/file/d/1PeNNdfNKj2sGoNvFi0LxWXUWuhzn7b1v/view?usp=drive_link)
- 📊 Analyse expenses in BI tool (Apache Superset) privately [DEMO](https://drive.google.com/file/d/1PYZhLen7lJgmUGyIJTZKjFEp4FiHXT6F/view?usp=drive_link)

![bi_view](https://drive.google.com/uc?export=view&id=1wWktv4auGYKZ-8OUF38uhJIS80c8OQo_)

## How to start using bot?

💸[Start using Expense Bot](https://t.me/superset_expense_bot) 💸

- 📲 Just type/voice your expense in the bot chat OR run '/add' to add your first expense following bot's instructions
- 🎉 Congrats, you recorded your first expense with Expense Bot!

## Which currencies bot supports?
USD, EUR, RUB, TRY, GEL, RSD, AMD

Despite used currency rate provider supports wide range of currencies, I limit available currencies for support simplicity purpose.

## Additional features
### 📊 Analyse data with useful charts
- Run '/analytics' to create your user in BI tool
  - 🪪 Initial credentials will be issued for you as well as link to the BI interface
  - 🔐 Your password is not saved anywhere, and you can change it after first login
### ⚙️ Personalize bot settings
- You can adjust your settings via '/settings' command
  - 📝 Set your own templates for amounts/comments for each spending category
  - 🏷️ Adjust categories displaying in '/add' command
  - ⚡️ Add shortcuts for repeatable expenses accessible via '/shortcut' command afterward
  - 🗓️ Schedule weekly expense report to track difference with previous week by category

💸[Start using Expense Bot](https://t.me/superset_expense_bot) 💸

## How to deploy your own bot?

### Prerequisites
- Terraform >= 1.0.0
- Docker >= 24.0.0
- Docker Engine if you are on MacOS (for example, colima)

### Local deploy
- Fork this repo and make your adjustments
- Deploy via
```bash
terraform init
terraform apply
```

### GCP deploy
You can deploy your bot on GCP platform using Compute Engine service.
- 🖥️ Create new instance of VM
  - Choose size (e2.micro is enough for low intensity load and it is free 🆓)
  - Any linux dist should be fine (for example, Debian)
  - If you change port for Superset, make sure you open it in NIC firewall
- 📥 Clone repo to your created VM and run
```bash
terraform init
terraform apply
```

Probably, you will need some adjustments, please reach out to me via Telegram [@romka_bauer](https://t.me/romka_bauer), I will try to help.

## Privacy remarks

- Separate BI user is being created for every bot user who issues command "/analytics".
- Every BI user created has its own RLS (Row-Level Security) policy which configured to display only this BI user's expenses in Apache Superset. More about RLS: https://superset.apache.org/docs/security/#row-level-security

## Future plans:
- Family/Joint expenses in groups + shared access to BI for the group
- Suggestion of new categories with ability for moderation by admins

### Security
- Use static DNS name and https for BI interface
