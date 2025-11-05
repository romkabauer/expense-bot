# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import os

from cachelib.redis import RedisCache
from celery.schedules import crontab

from superset.tasks.types import FixedExecutor

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

SQLALCHEMY_DATABASE_URI = \
    f'postgresql://{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}@{os.getenv("POSTGRES_HOST")}/{os.getenv("METADATA_DB_NAME")}'

# Enables SWAGGER UI for superset openapi spec
# ex: http://localhost:8080/swagger/v1
FAB_API_SWAGGER_UI = True
FAB_ADD_SECURITY_API = True

FAB_ADD_SECURITY_VIEWS = True
FAB_ADD_SECURITY_PERMISSION_VIEW = True
FAB_ADD_SECURITY_VIEW_MENU_VIEW = True
FAB_ADD_SECURITY_PERMISSION_VIEWS_VIEW = True

FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "THUMBNAILS": True,
    "THUMBNAILS_SQLA_LISTENERS": True,
    "PLAYWRIGHT_REPORTS_AND_THUMBNAILS": True
}

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_CACHE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
RESULT_BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

class CeleryConfig:
    broker_url = REDIS_CACHE_URL
    broker_connection_retry_on_startup = True
    imports = (
        "superset.sql_lab",
        "superset.tasks",
        "superset.tasks.thumbnails"
    )
    result_backend = RESULT_BACKEND_URL
    worker_prefetch_multiplier = 10
    task_acks_late = True
    task_annotations = {
        "sql_lab.get_sql_results": {
            "rate_limit": "100/s",
        }
    }

    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }
    beat_schedule_filename = "/tmp/celerybeat-schedule"

CELERY_CONFIG = CeleryConfig

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": REDIS_CACHE_URL,
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": REDIS_CACHE_URL,
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_results_cache_",
}

FILTER_STATE_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": REDIS_CACHE_URL,
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_filter_cache_",
}

EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": REDIS_CACHE_URL,
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_explore_cache_",
}

THUMBNAIL_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": REDIS_CACHE_URL,
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_thumb_dashboard_",
}

RESULT_BACKEND = RedisCache(
    host=REDIS_HOST,
    port=REDIS_PORT,
    key_prefix="superset_results_backend_",
)

ALERT_REPORTS_NOTIFICATION_DRY_RUN = False

SCREENSHOT_LOCATE_WAIT = 100
SCREENSHOT_LOAD_WAIT = 600

WEBDRIVER_BASEURL = "http://superset:8088"
WEBDRIVER_BASEURL_USER_FRIENDLY = "http://localhost:3000"

ALERT_REPORTS_EXECUTORS = [FixedExecutor("admin")]
THUMBNAIL_EXECUTORS = [FixedExecutor("admin")]
