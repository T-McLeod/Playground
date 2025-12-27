# Infrastructure Documentation

This repository uses **Terraform** to manage Google Cloud Platform (GCP) infrastructure. The setup is designed to support multiple isolated environments (e.g., `development`, `prod`) within a single GCP project (or across multiple projects) using a shared codebase.

## Architecture Overview

The infrastructure is modularized into three main components:

1.  **Compute**: Manages Cloud Run services and Artifact Registry repositories.
2.  **Storage**: Manages Cloud Storage buckets and Firestore databases.
3.  **Networking**: Manages IAM roles and Service Accounts.

### Directory Structure

```
terraform/
├── main.tf                 # Root configuration, calls modules
├── variables.tf            # Global variables
├── outputs.tf              # Global outputs
├── modules/                # Reusable infrastructure components
│   ├── compute/            # Cloud Run, Artifact Registry
│   ├── networking/         # IAM, Service Accounts
│   └── storage/            # GCS, Firestore
└── environments/           # Environment-specific configurations
    ├── development/
    │   ├── backend.conf    # State bucket config for dev
    │   └── terraform.tfvars# Variable values for dev
    └── prod/
        ├── backend.conf    # State bucket config for prod
        └── terraform.tfvars# Variable values for prod
bootstrap/                  # One-time setup for state buckets
```

## Environment Isolation Strategy

We use a **Directory-Based Environment Config** strategy combined with **Terraform Workspaces** (implicitly via separate state files).

*   **Code Reusability**: The code in `terraform/` and `terraform/modules/` is shared across all environments.
*   **Configuration Isolation**: Each environment has its own folder in `terraform/environments/` containing:
    *   `terraform.tfvars`: Defines the specific values (e.g., `app_name = "playground-dev"`) that make the environment unique.
    *   `backend.conf`: Defines the specific GCS bucket where the Terraform state for that environment is stored.

## Key Resources

| Resource Type | Naming Convention | Managed By |
| :--- | :--- | :--- |
| **Cloud Run** | `${app_name}-service` | `modules/compute` |
| **Artifact Registry** | `${app_name}-backend-repo` | `modules/compute` |
| **GCS Bucket** | `${app_name}-${project_id}-bucket` | `modules/storage` |
| **Firestore DB** | `${app_name}-db` | `modules/storage` |
| **Service Account** | `${app_name}-sa` | `modules/networking` |

## Bootstrap (State Management)

The `bootstrap/` directory contains a separate Terraform configuration used to create the GCS buckets that store the Terraform state for the main infrastructure. This is a "chicken-and-egg" prerequisite: you need a bucket to store state, so you create those buckets first with a local state.

*   **Location**: `bootstrap/`
*   **Purpose**: Creates `playground-ai-478208-dev-terraform-state` and `playground-ai-478208-prod-terraform-state`.
*   **Usage**: Run once (or when adding new environments) to provision the backend buckets.
