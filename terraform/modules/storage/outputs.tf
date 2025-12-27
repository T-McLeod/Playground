output "app_gcs_bucket" {
  value = google_storage_bucket.app_bucket.name
}

output "firestore_database_name" {
  value = google_firestore_database.db.name
}