provider "google" {
  project = var.project_id
  region  = var.region
}

# Create a bucket for each environment defined in the 'environments' variable
resource "google_storage_bucket" "state_buckets" {
  for_each      = var.environments
  name          = "${var.project_id}-${var.app_name}-${each.key}-terraform-state"
  location      = var.region
  storage_class = "STANDARD"

  # Enable versioning to recover from accidental state corruption
  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true
  
  # Prevent Terraform from destroying this bucket if it contains objects (safety)
  force_destroy = false 
}

output "created_buckets" {
  value = [for b in google_storage_bucket.state_buckets : b.name]
}