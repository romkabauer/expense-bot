FROM python:3.11-slim
LABEL authors="romkabauer"

COPY requirements.txt /app/
WORKDIR /app

RUN apt-get update \
    && apt-get -y install libpq-dev gcc
RUN pip install -r requirements.txt

COPY handlers/. /app/handlers/.
COPY resources/. /app/resources/.
COPY database/migrations/. /app/database/migrations/.
COPY database/models/. /app/database/models/.
COPY database/__init__.py /app/database/
COPY database/database.py /app/database/
COPY alembic.ini /app/
COPY bot.py /app/
COPY run.py /app/
COPY logger.py /app/
COPY init_bot.sh /app/
COPY README.md /app/

RUN ["chmod", "+x", "/app/init_bot.sh"]
ENTRYPOINT ["/app/init_bot.sh"]
