variable "docker_network_name" {
  type = string
}

variable "db_host_name" {
  type = string
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
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

variable "postgres_db_superset_metadata" {
  description = "PostgreSQL database name for BI Superset"
  type        = string
}
