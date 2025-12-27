output "service_url" {
  value = module.compute.service_url
}

output "artifact_image_path" {
  value = module.compute.artifact_image_path
}

output "artifact_image_tag_path" {
  value = module.compute.artifact_image_tag_path
}

output "service_name" {
  value = module.compute.service_name
}

output "app_gcs_bucket" {
  value = module.storage.app_gcs_bucket
}

output "firestore_database_name" {
  value = module.storage.firestore_database_name
}

output "service_account_email" {
  value = module.networking.service_account_email
}