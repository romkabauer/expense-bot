#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	CREATE DATABASE ${postgres_db_bot};
	CREATE DATABASE ${postgres_db_job_store};
	CREATE DATABASE ${postgres_db_superset_metadata};
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" ${postgres_db_bot} <<-EOSQL
  	CREATE SCHEMA ${postgres_schema_bot};

	CREATE ROLE viewer;
	GRANT USAGE ON SCHEMA ${postgres_schema_bot} TO viewer;
EOSQL
