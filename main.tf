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