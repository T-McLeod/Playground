resource "google_cloud_run_v2_service" "app" {
  name     = "${var.app_name}-service"
  location = var.location

  scaling {
    max_instance_count = 5
  }

  template {
    containers {
      image = var.image_tag == "" ? "us-docker.pkg.dev/cloudrun/container/hello" : "${var.artifact_image_path}:${var.image_tag}"
      ports {
        container_port = 5000
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