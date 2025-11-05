ARG SUPERSET_VERSION=5.0.0
FROM apache/superset:${SUPERSET_VERSION}

USER root

RUN . /app/.venv/bin/activate && \
    uv pip install psycopg2-binary \
    psycopg2-binary \
    openpyxl \
    Pillow

COPY --chown=superset superset_init.sh /init_script/
RUN ["chmod", "+x", "/init_script/superset_init.sh"]

COPY --chown=superset superset_config.py /app/
ENV SUPERSET_CONFIG_PATH /app/superset_config.py

USER superset

CMD ["/bin/bash", "-c", "/init_script/superset_init.sh && /usr/bin/run-server.sh"]
