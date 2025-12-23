resource "google_artifact_registry_repository" "playground-tf-repo" {
  location      = var.location
  repository_id = "${var.app_name}-backend-repo"
  description   = "docker container repository for playground app backend"
  format        = "DOCKER"

  cleanup_policies {
    action = "KEEP"
    id     = "Old images"

    most_recent_versions {
      keep_count            = 1
      package_name_prefixes = []
    }
  }
}

resource "google_cloud_run_v2_service" "app" {
  name     = "${var.app_name}-service"
  location = var.location

  scaling {
    max_instance_count = 5
  }

  template {
    containers {
      image = "${var.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.playground-tf-repo.repository_id}/playground-backend:latest"
      ports {
        container_port = 5000
      }
    }
  }
}