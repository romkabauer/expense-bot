resource "local_file" "db_init_script" {
  filename = "${path.module}/assets/db_init.sh"
  content = templatefile("${path.module}/assets/db_init.sh.tpl", {
    postgres_db_bot = var.postgres_db_bot
    postgres_schema_bot = var.postgres_schema_bot
    postgres_db_job_store = var.postgres_db_job_store
    postgres_db_superset_metadata = var.postgres_db_superset_metadata
  })
}

resource "docker_image" "postgres_custom" {
  name = "expense-bot-db:${var.postgres_version}"
  build {
    context    = "${path.module}/assets"
    dockerfile = "Dockerfile"
    build_args = {
      POSTGRES_VERSION = var.postgres_version
    }
  }

  depends_on = [ local_file.db_init_script ]
}

resource "docker_volume" "postgres_data" {
  name = "db-data"
}

resource "docker_container" "postgres" {
  name  = var.db_host_name
  image = docker_image.postgres_custom.image_id
  
  networks_advanced {
    name = var.docker_network_name
  }
  
  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }
  
  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
  ]
  
  ports {
    internal = 5432
    external = 5432
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test         = ["CMD-SHELL", "pg_isready -U ${var.postgres_user} -d ${var.postgres_db_bot}"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 3
    start_period = "30s"
  }
}
