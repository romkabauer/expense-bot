variable "docker_network_name" {
  type = string
}

variable "docker_image_id" {
  type = string
}

variable "docker_image_worker_id" {
  type = string
}

variable "docker_image_beat_id" {
  type = string
}

variable "db_host_name" {
  type = string
}

variable "redis_host_name" {
  type = string
}

variable "redis_port" {
  type = number
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

variable "postgres_db_superset_metadata" {
  description = "PostgreSQL database name for BI Superset"
  type        = string
}

variable "superset_version" {
    type = string
    sensitive = false
}

variable "bi_version" {
    type = string
    sensitive = false
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

variable "superset_secret_key" {
  description = "Superset secret key"
  type        = string
  sensitive   = true
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
