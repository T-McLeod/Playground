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
    FIRESTORE_DATABASE    = module.storage.firestore_database_name
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

data "google_dns_managed_zone" "env_dns_zone" {
  name = var.dns_managed_zone # Must match the manual name in Console
}

# 1. Create the Domain Mapping in Cloud Run
resource "google_cloud_run_domain_mapping" "app_mapping" {
  location = var.region
  name     = "${var.subdomain}.playground-learning.space"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = module.compute.service_name
  }
}

# 2. Dynamically create the DNS records based on what Cloud Run says it needs
resource "google_dns_record_set" "app_dns_records" {
  managed_zone = data.google_dns_managed_zone.env_dns_zone.name
  
  name    = "${var.subdomain}.${data.google_dns_managed_zone.env_dns_zone.dns_name}"
  type    = "CNAME"
  ttl     = 300
  rrdatas = ["ghs.googlehosted.com."] 
}