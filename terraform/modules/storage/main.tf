resource "google_storage_bucket" "app_bucket" {
  name     = "${var.app_name}-${var.project_id}-bucket"
  uniform_bucket_level_access = true
  location = var.location
  force_destroy = true
}

resource "google_firestore_database" "db" {
  project     = var.project_id
  name        = "${var.app_name}-db"
  location_id = var.location
  type        = "FIRESTORE_NATIVE"
}