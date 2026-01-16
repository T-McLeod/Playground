project_id = "playground-ai-478208"
region     = "us-east1"
environment   = "global-prod"
image_tag  = "main"
artifact_image_path="us-docker.pkg.dev/playground-ai-478208/playground-global-repo/playground-backend"

canvas_api_token_secret_id="projects/817349898318/secrets/GLOBAL_CANVAS_API_TOKEN"

subdomain="demo"
dns_managed_zone="playground-root-zone"
origins=["https://demo.playground-learning.space", "https://playground-learning.space"]