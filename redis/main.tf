resource "docker_volume" "redis_data" {
  name = "redis-data"
}

resource "docker_container" "redis" {
  name  = var.redis_host_name
  image = var.docker_image_id

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
