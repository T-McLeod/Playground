provider "google" {
  project     = "playground-ai-478208"
  region      = "REGION"
}

resource "google_storage_bucket" "bucket-for-state" {
  name        = "playground-ai-478208"
  location    = "US"
  uniform_bucket_level_access = true
}

terraform {
  backend "gcs" {
    bucket = "playground-ai-478208"
    prefix = "terraform/state"
  }
}

resource "google_artifact_registry_repository" "playground-tf-repo" {
  location      = var.region
  repository_id = "cloud-run-source-deploy"
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