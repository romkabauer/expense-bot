FROM apache/superset:latest

USER root

RUN apt-get update \
    && apt-get -y install libpq-dev gcc postgresql
RUN pip install psycopg2-binary

COPY --chown=superset superset_init.sh /init_script/
RUN ["chmod", "+x", "/init_script/superset_init.sh"]

COPY --chown=superset superset_config.py /app/
ENV SUPERSET_CONFIG_PATH /app/superset_config.py

USER superset
