resource "docker_image" "superset" {
  name = "expense-bot-bi:v${var.superset_version}-${var.bi_version}"
  build {
    context = "${path.module}/assets"
    dockerfile = "Dockerfile"
    no_cache = false
    build_args = {
      SUPERSET_VERSION = var.superset_version
    }
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/assets", "**"): filesha1("${path.module}/assets/${f}")]))
  }
}

resource "docker_image" "superset_celery_worker" {
  name = "expense-bot-bi-worker:v${var.superset_version}-${var.bi_version}"
  build {
    context = "${path.module}/assets"
    dockerfile = "Dockerfile_worker"
    no_cache = false
    build_args = {
      SUPERSET_VERSION = var.superset_version
    }
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/assets", "**"): filesha1("${path.module}/assets/${f}")]))
  }
}

resource "docker_image" "superset_celery_beat" {
  name = "expense-bot-bi-beat:v${var.superset_version}-${var.bi_version}"
  build {
    context = "${path.module}/assets"
    dockerfile = "Dockerfile_beat"
    no_cache = false
    build_args = {
      SUPERSET_VERSION = var.superset_version
    }
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/assets", "**"): filesha1("${path.module}/assets/${f}")]))
  }
}

resource "docker_container" "superset" {
  name  = "superset"
  image = docker_image.superset.image_id

  networks_advanced {
    name = var.docker_network_name
  }

  ports {
    internal = 8088
    external = 3000
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
  image = docker_image.superset_celery_worker.image_id

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
  image = docker_image.superset_celery_beat.image_id

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