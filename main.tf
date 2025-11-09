# ####################### INFRA #######################

resource "docker_network" "expense_bot_network" {
  name = "expense-bot-network"
  driver = "bridge"
}

# #### DB ####

module "postgres_db" {
  source = "./db"

  providers = {
    docker = docker
  }

  docker_network_name = var.docker_network_name
  docker_image_id = docker_image.postgres_custom.image_id

  db_host_name = var.db_host_name
  postgres_version = var.postgres_version

  postgres_user = var.postgres_user
  postgres_password = var.postgres_password

  postgres_db_bot = var.postgres_db_bot
  postgres_schema_bot = var.postgres_schema_bot
  postgres_db_job_store = var.postgres_db_job_store
  postgres_db_superset_metadata = var.postgres_db_superset_metadata
}

# #### REDIS ####

module "redis" {
  source = "./redis"

  providers = {
    docker = docker
  }

  docker_network_name = var.docker_network_name
  docker_image_id = docker_image.redis.image_id

  redis_host_name = var.redis_host_name
  redis_version = var.redis_version
  redis_port = 6379
}

# #### BI ####

module "bi" {
  source = "./superset"

  providers = {
    docker = docker
  }

  docker_network_name = var.docker_network_name
  docker_image_id = docker_image.superset.image_id
  docker_image_worker_id = docker_image.superset_celery_worker.image_id
  docker_image_beat_id = docker_image.superset_celery_beat.image_id

  db_host_name = var.db_host_name
  postgres_user = var.postgres_user
  postgres_password = var.postgres_password
  postgres_db_superset_metadata = var.postgres_db_superset_metadata

  redis_host_name = var.redis_host_name
  redis_port = 6379

  superset_version = var.superset_version
  bi_version = var.bi_version

  superset_admin_username = var.superset_admin_username
  superset_admin_password = var.superset_admin_password
  superset_secret_key = var.superset_secret_key

  depends_on = [ module.postgres_db, module.redis ]
}

# ####################### BOT #######################

module "bot" {
  source = "./bot"

  providers = {
    docker = docker
  }

  telegram_bot_token = var.telegram_bot_token
  bot_version = var.bot_version
  freecurrency_api_key = var.freecurrency_api_key
  gemini_api_key = var.gemini_api_key

  docker_network_name = var.docker_network_name
  docker_image_id = docker_image.expense_bot.image_id

  db_host_name = var.db_host_name
  postgres_user = var.postgres_user
  postgres_password = var.postgres_password
  postgres_db_bot = var.postgres_db_bot
  postgres_schema_bot = var.postgres_schema_bot
  postgres_db_job_store = var.postgres_db_job_store

  superset_admin_username = var.superset_admin_username
  superset_admin_password = var.superset_admin_password
  superset_base_url = "http://${var.superset_container_name}:${var.superset_internal_port}/api/v1"
  superset_ui_url = "http://localhost:${var.superset_external_port}"

  depends_on = [ module.bi ]
}