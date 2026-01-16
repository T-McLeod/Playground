# CI/CD Pipeline Documentation

This repository uses **GitHub Actions** for Continuous Integration and Continuous Deployment. The pipeline is defined in `.github/workflows/google.yml`.

## Workflow Overview

The pipeline is designed to be **environment-aware** based on the Git branch. It supports a "Build Once, Deploy Anywhere" pattern where a single Docker image is built and then promoted to specific environments.

### Triggers

The workflow triggers on `push` and `pull_request` events to the following branches:
*   `development` (Deploys to the Dev environment)
*   `main` (Deploys to the Prod environment)

### Jobs

#### 1. `test` (Automated Testing)
*   **Purpose**: Runs unit and integration tests to ensure code quality.
*   **Current Status**: Placeholder script. Fails the pipeline if tests fail.

#### 2. `deploy_build` (Build & Publish)
*   **Runs On**: All triggers (Push & PR).
*   **Purpose**: Builds the Docker container and pushes it to the **Global Artifact Registry**.
*   **Output**:
    *   Image: `us-docker.pkg.dev/playground-ai-478208/playground-global-repo/playground-backend`
    *   Tags: `latest` and `${github.sha}`
*   **Why Global?**: We build the image once and store it centrally. This ensures that the exact same binary that was tested is the one that gets deployed.

#### 3. `deploy_infrastructure` (Provision & Promote)
*   **Runs On**: Only `push` events to `development` or `main`.
*   **Dependencies**: Waits for `test` and `deploy_build` to succeed.
*   **Steps**:
    1.  **Authenticate**: Uses Workload Identity Federation (WIF) to authenticate with GCP as a Service Account.
    2.  **Terraform Init**: Initializes Terraform using the backend configuration specific to the branch (e.g., `environments/development/backend.conf`).
    3.  **Terraform Apply**: Applies infrastructure changes using the environment's variable file (e.g., `environments/development/terraform.tfvars`).
    4.  **Promote Image**:
        *   Pulls the image from the **Global** registry (built in the previous job).
        *   Retags it for the **Environment-Specific** registry (managed by Terraform).
        *   Pushes the image to the environment registry.
        *   *Note*: Cloud Run is configured to pull from this environment-specific registry.

## Secrets & Configuration

The pipeline relies on the following GitHub Secrets/Variables (defined in the workflow `env` block):

*   `PROJECT_ID`: The GCP Project ID.
*   `WIF_PROVIDER`: The Workload Identity Provider resource name.
*   `WIF_SERVICE_ACCOUNT`: The Service Account email to impersonate.

## Branching Strategy

| Branch | Environment | Terraform Config | State Bucket |
| :--- | :--- | :--- | :--- |
| `development` | **Dev** | `environments/development/` | `...-dev-terraform-state` |
| `main` | **Prod** | `environments/prod/` | `...-prod-terraform-state` |
