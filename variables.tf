# General
variable "docker_host" {
    type = string
    sensitive = false
    default = "unix:///var/run/docker.sock"
}

variable "docker_network_name" {
  type = string
  default = "expense-bot-network"
}

# DB
variable "db_host_name" {
  type    = string
  default = "db"
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16.8"
}

variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "service_user"
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  default     = "secure_password_123"
  sensitive   = true
}

variable "postgres_db_bot" {
  description = "PostgreSQL database name for bot data"
  type        = string
  default     = "expense_bot"
}

variable "postgres_schema_bot" {
  description = "PostgreSQL schema name for tables created by bot"
  type        = string
  default     = "expense_bot"
}

variable "postgres_db_job_store" {
  description = "PostgreSQL database name for bot scheduled jobs store via apscheduler"
  type        = string
  default     = "scheduler_jobstore"
}

variable "postgres_db_superset_metadata" {
  description = "PostgreSQL database name for BI Superset"
  type        = string
  default     = "superset_metadata"
}

# REDIS
variable "redis_host_name" {
  type = string
  default = "redis"
}

variable "redis_version" {
  type = string
  default = "7.2"
}

# BI
variable "superset_version" {
    type = string
    sensitive = false
    default = "5.0.0-py311"
}

variable "bi_version" {
    type = string
    sensitive = false
    default = "0.1.0"
}

variable "superset_admin_username" {
  description = "Superset admin username"
  type        = string
  default     = "admin"
}

variable "superset_admin_password" {
  description = "Superset admin password"
  type        = string
  sensitive   = true
}

variable "superset_secret_key" {
  description = "Superset secret key"
  type        = string
  sensitive   = true
}

variable "superset_container_name" {
  description = "Superset container name and host name in the Docker network"
  type = string
  default = "superset"
}

variable "superset_internal_port" {
  description = "Superset internal port"
  type        = number
  default     = 8088
}

variable "superset_external_port" {
  description = "Superset external port"
  type        = number
  default     = 3000
}

variable "superset_ui_url" {
  description = "Superset UI URL"
  type        = string
  default     = "http://localhost:3000"
}

# BOT
variable "bot_version" {
    type = string
    sensitive = false
    default = "python3.12-0.1.0"
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
  default     = ""
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}
