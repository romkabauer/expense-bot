variable "docker_network_name" {
  type = string
}

variable "docker_image_id" {
  type = string
}

variable "db_host_name" {
  type = string
}

variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "postgres_db_bot" {
  description = "PostgreSQL database name for bot data"
  type        = string
}

variable "postgres_schema_bot" {
  description = "PostgreSQL schema name for tables created by bot"
  type        = string
}

variable "postgres_db_job_store" {
  description = "PostgreSQL database name for bot scheduled jobs store via apscheduler"
  type        = string
}

variable "superset_admin_username" {
  description = "Superset admin username"
  type        = string
}

variable "superset_admin_password" {
  description = "Superset admin password"
  type        = string
  sensitive   = true
}

variable "superset_ui_url" {
  description = "Superset UI URL"
  type        = string
}

variable "superset_base_url" {
  description = "Superset base URL for API calls"
  type        = string
}

variable "bot_version" {
  type = string
  sensitive = false
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token from @BotFather"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.telegram_bot_token) > 0
    error_message = "Telegram bot token is required."
  }
}

variable "freecurrency_api_key" {
  description = "FreeCurrencyAPI key for currency conversion (optional)"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}
