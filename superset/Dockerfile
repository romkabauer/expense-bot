FROM apache/superset:latest

USER root

COPY --chown=superset superset/superset_init.sh /init_script/
RUN ["chmod", "+x", "/init_script/superset_init.sh"]

COPY --chown=superset superset/superset_config.py /app/
ENV SUPERSET_CONFIG_PATH /app/superset_config.py

USER superset
