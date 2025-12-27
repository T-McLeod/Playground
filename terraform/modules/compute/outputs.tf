output "service_url" {
  value = google_cloud_run_v2_service.app.uri
}

output "artifact_image_tag_path" {
  description = "The full artifact image path with tag"
  value = "${var.artifact_image_path}:${var.image_tag}"
}