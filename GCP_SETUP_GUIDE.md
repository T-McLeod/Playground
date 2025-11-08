# Google Cloud Platform (GCP) Setup Guide

## What is `service-account.json`?

The `service-account.json` file is a **Google Cloud Platform service account key** that contains credentials for authenticating your application with GCP services (Vertex AI, Firestore, etc.).

### ⚠️ **SECURITY WARNING**
- **NEVER commit this file to git**
- **NEVER share this file publicly**
- **NEVER hardcode credentials in your code**
- The file is already in `.gitignore` to prevent accidental commits

## File Structure

See `service-account.json.example` for the structure (with fake credentials).

The actual file contains:
- `project_id`: Your GCP project identifier
- `private_key`: RSA private key for authentication (SENSITIVE!)
- `client_email`: Service account email address
- Other authentication metadata

## How to Create a Service Account

### Option 1: Using GCP Console (Web UI)

1. **Go to GCP Console**
   - Visit: https://console.cloud.google.com
   - Select your project (or create a new one)

2. **Navigate to IAM & Admin**
   - Menu → IAM & Admin → Service Accounts
   - Or visit: https://console.cloud.google.com/iam-admin/serviceaccounts

3. **Create Service Account**
   - Click **"+ CREATE SERVICE ACCOUNT"**
   - Enter details:
     - **Name**: `canvas-ta-bot`
     - **ID**: `canvas-ta-bot` (auto-generated)
     - **Description**: `Service account for Canvas TA-Bot application`
   - Click **"CREATE AND CONTINUE"**

4. **Grant Roles** (Step 2)
   - Add the following roles:
     - ✅ **Vertex AI User** (`roles/aiplatform.user`)
       - Required for: RAG corpus creation, Gemini API calls
     - ✅ **Cloud Datastore User** (`roles/datastore.user`)
       - Required for: Firestore read/write operations
     - Optional (if using other services):
       - **Storage Object Viewer** (`roles/storage.objectViewer`) - If storing files in Cloud Storage
       - **Logging Writer** (`roles/logging.logWriter`) - For Cloud Logging
   - Click **"CONTINUE"**

5. **Grant User Access** (Step 3 - Optional)
   - Skip this step (click **"DONE"**)
   - This is for giving other users access to manage the service account

6. **Create Key**
   - Find your newly created service account in the list
   - Click the **three dots** (⋮) → **"Manage keys"**
   - Click **"ADD KEY"** → **"Create new key"**
   - Select **JSON** format
   - Click **"CREATE"**
   - The `service-account.json` file will download automatically
   - **Save this file securely!**

7. **Move File to Project**
   ```bash
   # Move the downloaded file to your project root
   mv ~/Downloads/your-project-abc123-xyz789.json service-account.json
   ```

### Option 2: Using `gcloud` CLI

```bash
# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Create service account
gcloud iam service-accounts create canvas-ta-bot \
    --display-name="Canvas TA Bot Service Account" \
    --description="Service account for Canvas TA-Bot application"

# 3. Grant Vertex AI User role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:canvas-ta-bot@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# 4. Grant Cloud Datastore User role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:canvas-ta-bot@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

# 5. Create and download key
gcloud iam service-accounts keys create service-account.json \
    --iam-account=canvas-ta-bot@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 6. Verify file was created
ls -la service-account.json
```

## Enable Required APIs

Before using the service account, enable the necessary APIs:

### Via GCP Console
1. Navigate to **APIs & Services** → **Library**
2. Search and enable:
   - ✅ **Vertex AI API** (`aiplatform.googleapis.com`)
   - ✅ **Cloud Firestore API** (`firestore.googleapis.com`)
   - ✅ **Generative Language API** (`generativelanguage.googleapis.com`)

### Via `gcloud` CLI
```bash
# Enable all required APIs at once
gcloud services enable \
    aiplatform.googleapis.com \
    firestore.googleapis.com \
    generativelanguage.googleapis.com
```

## Configure Application

1. **Place the file in project root**
   ```
   canvas-ta-bot/
   ├── service-account.json  ← HERE (gitignored)
   ├── .env
   ├── requirements.txt
   └── ...
   ```

2. **Update `.env` file**
   ```bash
   GOOGLE_CLOUD_PROJECT=your-actual-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   GOOGLE_APPLICATION_CREDENTIALS=service-account.json
   ```

3. **Verify setup**
   ```bash
   python check_env.py
   ```

## Testing the Connection

### Test 1: Verify Credentials
```bash
python -c "
from google.cloud import firestore
import os

# This will use the service account file
db = firestore.Client()
print('✅ Successfully authenticated with GCP!')
"
```

### Test 2: Test Vertex AI
```bash
python -c "
import vertexai
import os

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
vertexai.init(project=project_id, location='us-central1')
print('✅ Vertex AI initialized successfully!')
"
```

## Security Best Practices

### ✅ DO:
- Keep `service-account.json` in `.gitignore`
- Store the file securely on your local machine
- Use different service accounts for dev/staging/production
- Regularly rotate service account keys (every 90 days recommended)
- Grant minimum required permissions (principle of least privilege)
- Use environment variables to reference the file path

### ❌ DON'T:
- Commit the file to git
- Share the file via email, Slack, etc.
- Hardcode credentials in source code
- Use the same service account for multiple unrelated projects
- Grant overly broad permissions (e.g., Project Owner)
- Store the file in publicly accessible locations

## Troubleshooting

### Error: "Could not automatically determine credentials"
**Cause**: `service-account.json` not found or not in correct location

**Solution**:
```bash
# Check file exists
ls service-account.json

# Check environment variable
python -c "import os; print(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))"

# Should output: service-account.json
```

### Error: "Permission denied" or "403 Forbidden"
**Cause**: Service account lacks required permissions

**Solution**:
1. Go to IAM & Admin → IAM in GCP Console
2. Find your service account
3. Verify it has `Vertex AI User` and `Cloud Datastore User` roles
4. Add missing roles if needed

### Error: "API not enabled"
**Cause**: Required APIs not enabled in GCP project

**Solution**:
```bash
# Enable all required APIs
gcloud services enable \
    aiplatform.googleapis.com \
    firestore.googleapis.com \
    generativelanguage.googleapis.com
```

### Error: "Invalid JSON in service account file"
**Cause**: Corrupted or improperly formatted service account file

**Solution**:
1. Validate JSON format:
   ```bash
   python -c "import json; json.load(open('service-account.json'))"
   ```
2. If invalid, re-download the key from GCP Console
3. Compare structure with `service-account.json.example`

## Alternative Authentication Methods

### For Production/CI-CD
Instead of using a JSON key file, consider:

1. **Workload Identity** (GKE)
   - No key files needed
   - Automatically managed by Kubernetes

2. **Application Default Credentials**
   - Uses `gcloud auth application-default login`
   - Good for local development

3. **Secret Manager**
   - Store credentials in GCP Secret Manager
   - Reference at runtime

### For Local Development
The JSON key file method (current approach) is standard and recommended.

## Key Rotation

Service account keys should be rotated periodically:

1. **Create new key** (following steps above)
2. **Update application** to use new key
3. **Test** that new key works
4. **Delete old key** from GCP Console
   - IAM & Admin → Service Accounts → Keys
   - Delete the old key

**Recommended rotation schedule**: Every 90 days

## Resources

- [GCP Service Accounts Overview](https://cloud.google.com/iam/docs/service-accounts)
- [Creating Service Account Keys](https://cloud.google.com/iam/docs/creating-managing-service-account-keys)
- [Vertex AI Authentication](https://cloud.google.com/vertex-ai/docs/authentication)
- [Best Practices for Service Accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts)

---

**For team setup**: Each developer should create their own service account key for local development. Never share service account keys between team members.
