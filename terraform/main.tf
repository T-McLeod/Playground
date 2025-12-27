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
  app_name    = var.app_name
  location    = var.region
  image_tag   = var.image_tag
}

module "storage" {
  source      = "./modules/storage"
  project_id  = var.project_id
  app_name    = var.app_name
  location    = var.region
}

module "networking" {
  source      = "./modules/networking"
  app_name    = var.app_name
  project_id  = var.project_id
}