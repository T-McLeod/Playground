variable "project_id" {
    description = "The GCP Project ID"
    type        = string
}

variable "app_name" {
    description = "The app name. Repository provisioned will be based on this name."
    type        = string
}

variable "location" {
    description = "The location"
    type        = string
}

variable "artifact_image_path" {
    description = "The Artifact Registry image name ex: us-docker.pkg.dev/project-id/repo-name/image-name"
    type        = string
}

variable "image_tag" {
    description = "The container image tag to deploy"
    type        = string
}

variable "service_account_email" {
  description = "The service account email to run the service"
  type        = string
}

variable "env_vars" {
  description = "Environment variables to set for the service"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets to mount as environment variables"
  type        = map(string)
  default     = {}
}