# Developer Guide

This guide outlines common tasks for developers working on the Playground infrastructure and application.

## Prerequisites

Ensure you have the following tools installed:
*   [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
*   [Terraform](https://developer.hashicorp.com/terraform/downloads)
*   [Docker](https://docs.docker.com/get-docker/)

## Local Development

### 1. Authenticate with GCP
You need Application Default Credentials (ADC) to run Terraform locally.
```bash
gcloud auth application-default login
gcloud auth login
```

### 2. Working with Terraform
To make changes to a specific environment (e.g., `development`):

1.  **Navigate to the terraform directory**:
    ```bash
    cd terraform
    ```

2.  **Initialize the Backend**:
    You must tell Terraform which environment's state to use.
    ```bash
    terraform init -reconfigure -backend-config="environments/development/backend.conf"
    ```

3.  **Plan & Apply**:
    Always use the environment's variable file.
    ```bash
    terraform plan -var-file="environments/development/terraform.tfvars"
    terraform apply -var-file="environments/development/terraform.tfvars"
    ```

**Important**: If you switch between environments (e.g., from dev to prod), you **must** re-run the `init` command with the new backend config.

## Creating a New Environment

To spin up a new isolated environment (e.g., `staging`), follow these steps:

### Step 1: Provision the State Bucket
1.  Open `bootstrap/terraform.tfvars` (create it if it doesn't exist, using `terraform.tfvars.example` as a template).
2.  Add `"staging"` to the `environments` list.
    ```hcl
    environments = ["dev", "prod", "staging"]
    ```
3.  Apply the bootstrap configuration:
    ```bash
    cd bootstrap
    terraform apply
    ```
4.  Note the bucket name output (e.g., `playground-ai-478208-staging-terraform-state`).

### Step 2: Create Environment Configuration
1.  Create a new directory: `terraform/environments/staging/`.
2.  Create `terraform/environments/staging/backend.conf`:
    ```hcl
    bucket = "playground-ai-478208-staging-terraform-state"
    prefix = "terraform/state"
    ```
3.  Create `terraform/environments/staging/terraform.tfvars`:
    ```hcl
    project_id = "playground-ai-478208"
    app_name   = "playground-staging" # Unique prefix for resources
    region     = "us-east1"
    image_tag  = "latest"
    ```

### Step 3: Deploy Infrastructure
1.  Initialize Terraform for the new environment:
    ```bash
    cd terraform
    terraform init -reconfigure -backend-config="environments/staging/backend.conf"
    ```
2.  Apply the infrastructure:
    ```bash
    terraform apply -var-file="environments/staging/terraform.tfvars"
    ```

### Step 4: Configure CI/CD (Optional)
If you want automatic deployments for this environment:
1.  Create a branch named `staging`.
2.  Update `.github/workflows/google.yml`:
    *   Add `staging` to the `on: push: branches` list.
    *   Update the `if` condition in the `deploy_infrastructure` job to include `staging`.

## Troubleshooting

### State Lock Error
If Terraform fails with "Error acquiring the state lock", it means another process (or a crashed process) is holding the lock.
1.  Check the `Lock Info` in the error message for the `ID`.
2.  **Verify no other CI jobs or teammates are running apply.**
3.  Force unlock (use with caution):
    ```bash
    terraform force-unlock <LOCK_ID>
    ```

### Docker Auth Errors
If `docker push` fails with 403/Unauthorized:
1.  Ensure you are authenticated to the correct region's registry.
    ```bash
    gcloud auth configure-docker us-east1-docker.pkg.dev
    ```
2.  Verify your account has `Artifact Registry Writer` permissions.
