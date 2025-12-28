provider "google" {
  project     = var.project_id
  region      = var.region
}

terraform {
  backend "gcs" {}
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
    DUKE_GPT_API_BASE_URL = "https://litellm.oit.duke.edu/v1" #temporary hardcode
  }

  secrets = {
    CANVAS_API_TOKEN = var.canvas_api_token_secret_id
    DUKE_GPT_TOKEN  = "projects/817349898318/secrets/GLOBAL_DUKE_GPT_TOKEN"
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