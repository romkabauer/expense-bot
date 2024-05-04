# Expense Bot

💸[Start using Expense Bot](https://t.me/superset_expense_bot) 💸

## What you can do with this bot?

- 💵 Enter your expenses [DEMO](https://drive.google.com/file/d/1PeNNdfNKj2sGoNvFi0LxWXUWuhzn7b1v/view?usp=drive_link)
- 📊 Analyse expenses in BI tool (Apache Superset) privately [DEMO](https://drive.google.com/file/d/1PYZhLen7lJgmUGyIJTZKjFEp4FiHXT6F/view?usp=drive_link)

![bi_view](https://drive.google.com/uc?export=view&id=1wWktv4auGYKZ-8OUF38uhJIS80c8OQo_)

## How to start using bot?

💸[Start using Expense Bot](https://t.me/superset_expense_bot) 💸

- 📤 Open [link to bot](https://t.me/superset_expense_bot) and send him '/start' then '/setup', it configs bot for you with initial settings values
- 📲 Run '/add' to add your first expense, follow instructions by bot
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

💸[Start using Expense Bot](https://t.me/superset_expense_bot) 💸

## How to deploy your own bot?

### Local deploy
- Fork this repo and make your adjustments
- Deploy using docker-compose.yaml example from repo or the example script below
```bash
#!/bin/bash

cd expense-bot
docker rm -f db && docker rm -f bi && docker rm -f bot \
&& docker build -t expense-bot-db:0.1.0  -f database/Dockerfile . \
&& docker build -t expense-bot-bi:0.1.0 -f superset/Dockerfile . \
&& docker build -t expense-bot:0.1.0 -f Dockerfile . \
&& docker network rm -f expense-bot \
&& docker network create expense-bot \
&& export POSTGRES_USER=sample_pg_user \
        POSTGRES_PASSWORD='sample_pg_pass' \
        SUPERSET_SECRET_KEY=secret_string_for_encription \
        SUPERSET_ADMIN_USERNAME=superset_admin_user \
        SUPERSET_ADMIN_PASSWORD='superset_admin_user_pass' \
        EXPENSE_BOT_TOKEN='your telegram bot token' \
        EXPENSE_BOT_DB_CONNECTION_STRING='postgresql://sample_pg_user:sample_pg_pass@db/expense_bot'\
        SUPERSET_UI_URL='http://localhost:8088' \
&& docker run --name db -p 5432:5432 \
        -e POSTGRES_USER=$POSTGRES_USER \
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
        -v local_pgdata:/var/lib/postgresql/data \
        --network expense-bot \
        -d expense-bot-db:0.1.0 \
&& docker run --name bi -p 8088:8088 \
        -e SUPERSET_SECRET_KEY=$SUPERSET_SECRET_KEY \
        -e POSTGRES_USER=$POSTGRES_USER \
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
        -e SUPERSET_ADMIN_USERNAME=$SUPERSET_ADMIN_USERNAME \
        -e SUPERSET_ADMIN_PASSWORD=$SUPERSET_ADMIN_PASSWORD \
        -v superset-data:/app/superset_home \
        --network expense-bot \
        -d expense-bot-bi:0.1.0 \
&& docker run --name bot \
        -e EXPENSE_BOT_TOKEN=$EXPENSE_BOT_TOKEN \
        -e EXPENSE_BOT_DB_CONNECTION_STRING=$EXPENSE_BOT_DB_CONNECTION_STRING \
        -e SUPERSET_ADMIN_USERNAME=$SUPERSET_ADMIN_USERNAME \
        -e SUPERSET_ADMIN_PASSWORD=$SUPERSET_ADMIN_PASSWORD \
        -e SUPERSET_UI_URL=$SUPERSET_UI_URL \
        --network expense-bot \
        -d expense-bot:0.1.0
cd ..
```

### GCP deploy
You can deploy your bot on GCP platform using Compute Engine service.
- 🖥️ Create new instance of VM
  - Choose size (e2.micro is enough for low intensity load and it is free 🆓)
  - Choose container optimized OS with docker >= v24.0.9 (for example, cos-stable-109-17800-147-22)
  - If you change port for Superset, make sure you open it in NIC firewall
- 📥 Clone repo to your created VM
- 🛠️ Create deploy script from example above in the same parent directory like cloned repo and run it via ```source deploy_script.sh```

Probably, you will need some adjustments, please reach out to me via Telegram [@romka_bauer](https://t.me/romka_bauer), I will try to help.

## Privacy remarks

- Separate BI user is being created for every bot user who issues command "/analytics".
- Every BI user created has its own RLS (Row-Level Security) policy which configured to display only this BI user's expenses in Apache Superset. More about RLS: https://superset.apache.org/docs/security/#row-level-security

## Future plans:
- Editing / Deleting expenses and shortcuts
- Migrate to `freecurrencyapi` (more exchange rates available)
- Weekly summary on schedule
- Family/Joint expenses in groups + shared access to BI for the group
- Suggestion of new categories with ability for moderation by admins

### Deployment
- Configure env vars and deploy via Terraform

### Security
- Use static DNS name and https for BI interface
