provider "google" {
  project     = "playground-ai-478208"
  region      = "REGION"
}

resource "google_storage_bucket" "bucket-for-state" {
  name        = "playground-ai-478208-terraform-state"
  location    = "US"
  uniform_bucket_level_access = true
  force_destroy = true
}

terraform {
  backend "gcs" {
    bucket = "playground-ai-478208-terraform-state"
    prefix = "terraform.tfstate"
  }
}

module "compute" {
  source      = "./modules/compute"
  app_name    = var.app_name
  location    = var.region
}

resource "google_storage_bucket" "app_bucket" {
  name     = "${var.app_name}-bucket"
  uniform_bucket_level_access = true
  force_destroy = true
  location = var.region
}