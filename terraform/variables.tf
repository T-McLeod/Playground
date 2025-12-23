
variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The region for resources"
  default     = "us-east1"
}

variable "app_name" {
  default = "my-docker-app"
}