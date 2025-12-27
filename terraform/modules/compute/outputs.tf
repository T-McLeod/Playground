output "service_url" {
  value = google_cloud_run_v2_service.app.uri
}

output "artifact_registry_repo" {
  value = google_artifact_registry_repository.playground-tf-repo.repository_id
}

output "artifact_registry_repo_path" {
  description = "The base path for the Docker repository"
  # This constructs the path: us-east1-docker.pkg.dev/playground-ai-478208/playground-global-backend-repo
  value = "${google_artifact_registry_repository.playground-tf-repo.location}-docker.pkg.dev/${google_artifact_registry_repository.playground-tf-repo.project}/${google_artifact_registry_repository.playground-tf-repo.repository_id}"
}