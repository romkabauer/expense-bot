resource "docker_image" "expense_bot" {
  name = "expense-bot:${var.bot_version}"
  build {
    context = "${path.module}/assets"
    dockerfile = "Dockerfile"
    no_cache = false
  }
  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/assets", "**"): filesha1("${path.module}/assets/${f}")]))
  }
}

resource "docker_container" "expense_bot" {
  name  = "bot"
  image = docker_image.expense_bot.image_id
  
  networks_advanced {
    name = var.docker_network_name
  }
  
  env = [
    # Telegram Bot Token (*required)
    "EXPENSE_BOT_TOKEN=${var.telegram_bot_token}",

    # Database configuration
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_HOST=${var.db_host_name}",
    "POSTGRES_DB_BOT=${var.postgres_db_bot}",
    "POSTGRES_SCHEMA_BOT=${var.postgres_schema_bot}",
    "POSTGRES_DB_JOB_STORE=${var.postgres_db_job_store}",

    # Superset configuration
    "SUPERSET_ADMIN_USERNAME=${var.superset_admin_username}",
    "SUPERSET_ADMIN_PASSWORD=${var.superset_admin_password}",
    "SUPERSET_UI_URL=${var.superset_ui_url}",
  
    # API keys
    "GEMINI_API_KEY=${var.gemini_api_key}",
    "FREECURRENCYAPI_API_KEY=${var.freecurrency_api_key}" # Currency API Key from freecurrencyapi.com (*optional)
  ]
  
  restart = "unless-stopped"
}
