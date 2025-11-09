resource "docker_container" "superset" {
  name  = "superset"
  image = var.docker_image_id

  networks_advanced {
    name = var.docker_network_name
  }

  ports {
    internal = var.superset_internal_port
    external = var.superset_external_port
  }

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_HOST=${var.db_host_name}",
    "METADATA_DB_NAME=${var.postgres_db_superset_metadata}",

    "REDIS_HOST=${var.redis_host_name}",
    "REDIS_PORT=${var.redis_port}",

    "SUPERSET_ADMIN_USERNAME=${var.superset_admin_username}",
    "SUPERSET_ADMIN_PASSWORD=${var.superset_admin_password}",
    "SUPERSET_SECRET_KEY=${var.superset_secret_key}"
  ]

  restart = "unless-stopped"
}

resource "docker_container" "superset_worker" {
  name  = "superset-worker"
  image = var.docker_image_worker_id

  networks_advanced {
    name = var.docker_network_name
  }

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_HOST=${var.db_host_name}",
    "METADATA_DB_NAME=${var.postgres_db_superset_metadata}",

    "REDIS_HOST=${var.redis_host_name}",
    "REDIS_PORT=${var.redis_port}",

    "SUPERSET_SECRET_KEY=${var.superset_secret_key}"
  ]

  restart = "unless-stopped"

  depends_on = [ docker_container.superset ]
}

resource "docker_container" "superset_beat" {
  name  = "superset-beat"
  image = var.docker_image_beat_id

  networks_advanced {
    name = var.docker_network_name
  }

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_HOST=${var.db_host_name}",
    "METADATA_DB_NAME=${var.postgres_db_superset_metadata}",

    "REDIS_HOST=${var.redis_host_name}",
    "REDIS_PORT=${var.redis_port}",

    "SUPERSET_SECRET_KEY=${var.superset_secret_key}"
  ]

  restart = "unless-stopped"

  depends_on = [ docker_container.superset ]
}