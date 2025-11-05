#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	CREATE DATABASE expense_bot;
	CREATE DATABASE scheduler_jobstore;
	CREATE DATABASE superset_metadata;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" expense_bot <<-EOSQL
  	CREATE SCHEMA expense_bot;

	CREATE ROLE viewer;
	GRANT USAGE ON SCHEMA expense_bot TO viewer;
EOSQL
