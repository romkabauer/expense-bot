FROM python:3.12-slim
LABEL authors="romkabauer"

COPY requirements.txt /app/
WORKDIR /app

RUN apt-get update \
    && apt-get -y install libpq-dev gcc curl ca-certificates

ADD https://astral.sh/uv/0.8.23/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

RUN uv pip install --system -r requirements.txt

COPY . /app/.

RUN ["chmod", "+x", "/app/init_bot.sh"]
ENTRYPOINT ["/app/init_bot.sh"]
