variable "project_id" {
  description = "The ID of the Google Cloud project where buckets will be created"
  type        = string
}

variable "app_name" {
  description = "The application name used as a prefix for bucket names"
  type        = string
}

variable "region" {
  description = "The region for the buckets"
  type        = string
  default     = "us-east1"
}

variable "environments" {
  description = "A set of environment names (e.g. dev, prod) to create buckets for"
  type        = set(string)
}