provider "google" {
  project     = var.project_id
  region      = var.region
}

terraform {
  backend "gcs" {}
}

resource "google_secret_manager_secret" "canvas_api_token" {
  secret_id = var.canvas_api_token_secret_id
  replication {
    auto {}
  }
}

module "compute" {
  source      = "./modules/compute"
  project_id  = var.project_id
  app_name    = var.environment
  location    = var.region
  artifact_image_path = var.artifact_image_path
  image_tag   = var.image_tag
  service_account_email = module.networking.service_account_email
  
  env_vars = {
    GOOGLE_CLOUD_PROJECT  = var.project_id
    GOOGLE_CLOUD_LOCATION = var.region
    GCS_BUCKET_NAME       = module.storage.app_gcs_bucket
    CANVAS_BASE_URL       = var.canvas_base_url
  }

  secrets = {
    CANVAS_API_TOKEN = google_secret_manager_secret.canvas_api_token.id
  }
}

module "storage" {
  source      = "./modules/storage"
  project_id  = var.project_id
  app_name    = var.environment
  location    = var.region
}

module "networking" {
  source      = "./modules/networking"
  app_name    = var.environment
  project_id  = var.project_id
}