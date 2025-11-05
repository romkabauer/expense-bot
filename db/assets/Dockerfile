ARG POSTGRES_VERSION=16.8
FROM postgres:${POSTGRES_VERSION}

COPY db_init.sh /docker-entrypoint-initdb.d/
