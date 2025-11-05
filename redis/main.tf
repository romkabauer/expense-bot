resource "docker_image" "redis" {
  name = "redis:${var.redis_version}"
  keep_locally = false
}

resource "docker_volume" "redis_data" {
  name = "redis-data"
}

resource "docker_container" "redis" {
  name  = var.redis_host_name
  image = docker_image.redis.image_id

  networks_advanced {
    name = var.docker_network_name
  }

  ports {
    internal = 6379
    external = var.redis_port
  }

  restart = "unless-stopped"

  volumes {
    volume_name = docker_volume.redis_data.name
    container_path = "/data"
  }
}
