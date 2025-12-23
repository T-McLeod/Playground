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