# Expense Bot

https://t.me/superset_expense_bot

## What you can do with this bot?

- Note expenses💵
- Analyse expenses in BI tool (Apache Superset) privately📊

## How to start using bot?

- Open bot (https://t.me/superset_expense_bot) and send '/setup', this command configs bot for you with initial settings
- Run '/add' to add your first expense, follow instructions by bot
- You are good to go!

Additional features:
- You can adjust your settings via '/settings'
  - Set custom amounts/comments for spending category
  - Adjust displaying categories
  - Add shortcuts for repeatable expenses accessible via '/shortcut' afterward
- Run '/analytics' to create your user in BI tool
  - This command creates user and RLS policy in Apache Superset instance
  - Initial credentials will be issued for you, follow instructions by bot
  - Your password is not stored anywhere, you can change it after first login

## How to deploy your own bot?

### Local deploy
- Fork this repo and make your adjustments
- Deploy using docker-compose.yaml example or the example script below
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
- Create new instance of VM
  - Choose size (e2.micro is enough for low intensity load)
  - Choose container optimized OS with docker >= v24.0.9 (for example, cos-stable-109-17800-147-22)
  - If you change port for Superset, make sure you open it in NIC firewall
- Clone repo to your created VM
- Create deploy script from example above and run it

Probably, you will need some adjustments, please reach out to me via Telegram (@romka_bauer), I will try to help.

## Example of BI view

![bi_view](https://drive.google.com/uc?export=view&id=1wWktv4auGYKZ-8OUF38uhJIS80c8OQo_)

## Examples of usage

- Adding expenses

![adding_expenses](https://drive.google.com/uc?export=view&id=1ZMJRp4brpg3hSU4jDfL3HS-dRvunZWAS)

- Choosing category

![choosing_category](https://drive.google.com/uc?export=view&id=1Cc3xckefQ0kDNTbRVWlLB2dSw1sa8rXM)

- Enter amount

![enter_amount](https://drive.google.com/uc?export=view&id=1vdf_DyDHlRoIKqKn2kM5qAAQizbhFMD8)

- Adding comments

![adding_comments](https://drive.google.com/uc?export=view&id=1vHc21VFpmy4kQuy6gYKwgW7gBUwMuN2O)

## Privacy remarks

- Separate user is being created for every user who issues command "/analytics".
- Every user created has its own RLS (Row-Level Security) policy which configured to display only user's expenses in Apache Superset. More about RLS: https://superset.apache.org/docs/security/#row-level-security 