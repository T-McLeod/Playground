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

variable "cors_origins" {
    description = "List of origins allowed to make CORS requests to the bucket"
    type        = list(string)
    default     = ["*"]
}