resource "google_storage_bucket" "app_bucket" {
  name     = "${var.app_name}-bucket"
  uniform_bucket_level_access = true
  location = var.location
  force_destroy = true
}