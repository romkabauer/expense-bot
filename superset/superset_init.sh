#!/bin/bash
set -e

superset fab create-admin \
             --username "$SUPERSET_ADMIN_USERNAME" \
             --firstname Superset \
             --lastname Admin \
             --email example@localhost \
             --password "$SUPERSET_ADMIN_PASSWORD"
superset db upgrade
superset init
