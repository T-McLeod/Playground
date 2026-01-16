resource "google_cloud_run_v2_service" "app" {
  name     = "${var.app_name}-service"
  location = var.location

  scaling {
    max_instance_count = 5
  }

  template {
    service_account = var.service_account_email
    containers {
      image = var.image_tag == "" ? "us-docker.pkg.dev/cloudrun/container/hello" : "${var.artifact_image_path}:${var.image_tag}"
      ports {
        container_port = 5000
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.app.location
  service  = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}