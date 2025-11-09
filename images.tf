# #### POSTGRES IMAGE ####

resource "local_file" "db_init_script" {
  filename = "${path.module}/db/assets/db_init.sh"
  content = templatefile("${path.module}/db/assets/db_init.sh.tpl", {
    postgres_db_bot = var.postgres_db_bot
    postgres_schema_bot = var.postgres_schema_bot
    postgres_db_job_store = var.postgres_db_job_store
    postgres_db_superset_metadata = var.postgres_db_superset_metadata
  })
}

resource "docker_image" "postgres_custom" {
  name = "expense-bot-db:${var.postgres_version}"
  build {
    context    = "${path.module}/db/assets"
    dockerfile = "Dockerfile"
    build_args = {
      POSTGRES_VERSION = var.postgres_version
    }
  }

  depends_on = [ local_file.db_init_script ]
}

# #### REDIS IMAGE ####

resource "docker_image" "redis" {
  name = "redis:${var.redis_version}"
  keep_locally = false
}

# #### SUPERSET IMAGES ####

resource "docker_image" "superset" {
  name = "expense-bot-bi:v${var.superset_version}-${var.bi_version}"
  build {
    context = "${path.module}/superset/assets"
    dockerfile = "Dockerfile"
    no_cache = false
    build_args = {
      SUPERSET_VERSION = var.superset_version
    }
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/superset/assets", "**"): filesha1("${path.module}/superset/assets/${f}")]))
  }
}

resource "docker_image" "superset_celery_worker" {
  name = "expense-bot-bi-worker:v${var.superset_version}-${var.bi_version}"
  build {
    context = "${path.module}/superset/assets"
    dockerfile = "Dockerfile_worker"
    no_cache = false
    build_args = {
      SUPERSET_VERSION = var.superset_version
    }
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/superset/assets", "**"): filesha1("${path.module}/superset/assets/${f}")]))
  }
}

resource "docker_image" "superset_celery_beat" {
  name = "expense-bot-bi-beat:v${var.superset_version}-${var.bi_version}"
  build {
    context = "${path.module}/superset/assets"
    dockerfile = "Dockerfile_beat"
    no_cache = false
    build_args = {
      SUPERSET_VERSION = var.superset_version
    }
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/superset/assets", "**"): filesha1("${path.module}/superset/assets/${f}")]))
  }
}

# #### BOT IMAGE ####

resource "docker_image" "expense_bot" {
  name = "expense-bot:${var.bot_version}"
  build {
    context = "${path.module}/bot/assets"
    dockerfile = "Dockerfile"
    no_cache = false
  }
  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("${path.module}/bot/assets", "**"): filesha1("${path.module}/bot/assets/${f}")]))
  }
}