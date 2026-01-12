
variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The region for resources"
  default     = "us-east1"
}

variable "environment" {
  description = "The environment name (e.g. global-dev, global-prod)"
}

variable "image_tag" {
  description = "The container image tag to deploy"
  type        = string
  default     = ""
}

variable "artifact_image_path" {
  description = "The Artifact Registry image name ex: us-docker.pkg.dev/project-id/repo-name/image-name"
  type        = string
}

variable "canvas_api_token_secret_id" {
  description = "The Secret Manager secret ID for the Canvas API token"
  type        = string
}

variable "canvas_base_url" {
  description = "The base URL for the Canvas instance"
  type        = string
  default     = "https://canvas.instructure.com/api/v1"
}

variable "subdomain" {
  description = "The subdomain name for the application (e.g. 'dev' in [dev].playground-learning.space)"
  type        = string
}

variable "dns_managed_zone" {
  description = "The DNS managed zone name in Cloud DNS"
  type        = string
}