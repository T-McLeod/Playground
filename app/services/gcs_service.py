"""
Google Cloud Storage Service
Handles file upload/download operations with Google Cloud Storage.

This service provides functions to:
1. Upload local files to GCS bucket
2. Generate GCS URIs for uploaded files
3. List files in a bucket
4. Delete files from bucket

All files are organized by course_id for easy management.
"""
from google.cloud import storage
import os
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GCS configuration from environment variables
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', f'{PROJECT_ID}-canvas-files')
LOCATION = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')


def get_storage_client() -> storage.Client:
    """
    Creates and returns a Google Cloud Storage client.
    
    Returns:
        storage.Client instance
    """
    return storage.Client(project=PROJECT_ID)


def ensure_bucket_exists(bucket_name: str = BUCKET_NAME) -> storage.Bucket:
    """
    Ensures the GCS bucket exists, creates it if it doesn't.
    
    Args:
        bucket_name: Name of the bucket to create/verify
        
    Returns:
        storage.Bucket instance
    """
    client = get_storage_client()
    
    try:
        bucket = client.get_bucket(bucket_name)
        logger.info(f"Bucket '{bucket_name}' already exists")
        return bucket
    except Exception:
        # Bucket doesn't exist, create it
        logger.info(f"Creating bucket '{bucket_name}' in location '{LOCATION}'...")
        bucket = client.create_bucket(bucket_name, location=LOCATION)
        logger.info(f"Bucket '{bucket_name}' created successfully")
        return bucket


def upload_course_files(files: List[Dict], course_id: str, bucket_name: str = BUCKET_NAME) -> List[Dict]:
    """
    Uploads course files to Google Cloud Storage and updates file objects with GCS URIs.
    Files are organized in the bucket as: courses/{course_id}/{filename}
    
    Args:
        files: List of file objects with 'local_path' property
        course_id: Canvas course ID for organizing files
        bucket_name: GCS bucket name (default from env)
        
    Returns:
        Updated list of file objects with 'gcs_uri' property added
        
    Example:
        files, _ = canvas_service.get_course_files(course_id, token)
        files = gcs_service.upload_course_files(files, course_id)
        # Each file now has: file['gcs_uri'] = 'gs://bucket/courses/12345/file.pdf'
    """
    if not PROJECT_ID:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    # Ensure bucket exists
    bucket = ensure_bucket_exists(bucket_name)
    
    logger.info(f"Uploading {len(files)} files to GCS bucket '{bucket_name}'...")
    
    upload_count = 0
    
    for file in files:
        try:
            local_path = file.get('local_path')
            file_id = file.get('id')
            display_name = file.get('display_name', f"file_{file_id}")
            
            # Skip files without local path
            if not local_path or not os.path.exists(local_path):
                logger.warning(f"Skipping file (no local path or not found): {display_name}")
                file['gcs_uri'] = None
                continue
            
            # Create blob path: courses/{course_id}/{filename}
            blob_path = f"courses/{course_id}/{display_name}"
            blob = bucket.blob(blob_path)
            
            logger.info(f"Uploading {display_name} to {blob_path}...")
            
            # Upload file
            blob.upload_from_filename(local_path)
            
            # Generate GCS URI
            gcs_uri = f"gs://{bucket_name}/{blob_path}"
            file['gcs_uri'] = gcs_uri
            
            upload_count += 1
            logger.info(f"✅ Uploaded: {gcs_uri}")
            
        except Exception as e:
            logger.error(f"Failed to upload {file.get('display_name')}: {str(e)}")
            file['gcs_uri'] = None
            continue
    
    logger.info(f"Successfully uploaded {upload_count}/{len(files)} files to GCS")
    
    return files


def upload_file(local_path: str, blob_path: str, bucket_name: str = BUCKET_NAME) -> str:
    """
    Uploads a single file to GCS.
    
    Args:
        local_path: Local file path to upload
        blob_path: Destination path in bucket (e.g., 'courses/12345/file.pdf')
        bucket_name: GCS bucket name
        
    Returns:
        GCS URI (e.g., 'gs://bucket/courses/12345/file.pdf')
        
    Raises:
        FileNotFoundError: If local file doesn't exist
        Exception: If upload fails
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")
    
    bucket = ensure_bucket_exists(bucket_name)
    blob = bucket.blob(blob_path)
    
    logger.info(f"Uploading {local_path} to gs://{bucket_name}/{blob_path}...")
    blob.upload_from_filename(local_path)
    
    gcs_uri = f"gs://{bucket_name}/{blob_path}"
    logger.info(f"✅ Upload complete: {gcs_uri}")
    
    return gcs_uri


def list_course_files(course_id: str, bucket_name: str = BUCKET_NAME) -> List[str]:
    """
    Lists all files for a specific course in GCS.
    
    Args:
        course_id: Canvas course ID
        bucket_name: GCS bucket name
        
    Returns:
        List of GCS URIs for files in this course
    """
    bucket = ensure_bucket_exists(bucket_name)
    prefix = f"courses/{course_id}/"
    
    blobs = bucket.list_blobs(prefix=prefix)
    uris = [f"gs://{bucket_name}/{blob.name}" for blob in blobs]
    
    logger.info(f"Found {len(uris)} files for course {course_id}")
    return uris


def delete_course_files(course_id: str, bucket_name: str = BUCKET_NAME) -> int:
    """
    Deletes all files for a specific course from GCS.
    
    Args:
        course_id: Canvas course ID
        bucket_name: GCS bucket name
        
    Returns:
        Number of files deleted
    """
    bucket = ensure_bucket_exists(bucket_name)
    prefix = f"courses/{course_id}/"
    
    blobs = list(bucket.list_blobs(prefix=prefix))
    delete_count = 0
    
    logger.info(f"Deleting {len(blobs)} files for course {course_id}...")
    
    for blob in blobs:
        try:
            blob.delete()
            delete_count += 1
            logger.info(f"Deleted: {blob.name}")
        except Exception as e:
            logger.error(f"Failed to delete {blob.name}: {str(e)}")
            continue
    
    logger.info(f"Deleted {delete_count}/{len(blobs)} files")
    return delete_count


def get_file_info(gcs_uri: str) -> Optional[Dict]:
    """
    Gets metadata for a file in GCS.
    
    Args:
        gcs_uri: GCS URI (e.g., 'gs://bucket/path/to/file.pdf')
        
    Returns:
        Dict with file metadata or None if not found
    """
    # Parse GCS URI
    if not gcs_uri.startswith('gs://'):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    
    parts = gcs_uri[5:].split('/', 1)
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else ''
    
    try:
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            return None
        
        blob.reload()
        
        return {
            'name': blob.name,
            'size': blob.size,
            'content_type': blob.content_type,
            'created': blob.time_created,
            'updated': blob.updated,
            'gcs_uri': gcs_uri
        }
    except Exception as e:
        logger.error(f"Failed to get info for {gcs_uri}: {str(e)}")
        return None


def generate_signed_url(gcs_uri: str, expiration_minutes: int = 60) -> str:
    """
    Generates a signed URL for downloading a file from GCS.
    
    Args:
        gcs_uri: GCS URI (e.g., 'gs://bucket/path/to/file.pdf')
        expiration_minutes: URL expiration time in minutes (default: 60)
        
    Returns:
        Signed URL string that allows temporary public access
        
    Raises:
        ValueError: If GCS URI is invalid
        Exception: If signed URL generation fails
        
    Example:
        url = generate_signed_url('gs://my-bucket/file.pdf', 30)
        # Returns: https://storage.googleapis.com/my-bucket/file.pdf?X-Goog-Signature=...
    """
    from datetime import timedelta
    
    # Parse GCS URI
    if not gcs_uri.startswith('gs://'):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    
    parts = gcs_uri[5:].split('/', 1)
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else ''
    
    try:
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # Generate signed URL with expiration
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET"
        )
        
        logger.info(f"Generated signed URL for {blob_path} (expires in {expiration_minutes} min)")
        return url
        
    except Exception as e:
        logger.error(f"Failed to generate signed URL for {gcs_uri}: {str(e)}")
        raise


if __name__ == "__main__":
    # Test the GCS service
    from dotenv import load_dotenv
    import sys
    
    # Load environment variables
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(root_dir, '.env')
    load_dotenv(env_path)

    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
    BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', f'{PROJECT_ID}-canvas-files')
    LOCATION = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
    
    print(f"Loaded environment from: {env_path}")
    print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"GCS_BUCKET_NAME: {BUCKET_NAME}")
    
    if not PROJECT_ID:
        print("\n⚠️  Please set GOOGLE_CLOUD_PROJECT in .env")
        sys.exit(1)

    mock_file = {
        'id': '319580865',
        'display_name': 'Lec 1.pdf',
        'filename': 'Lec+1.pdf',
        'url': 'https://canvas.instructure.com/files/319580865/download?download_frd=1&verifier=hPXvy0owVxSkEZ7paw1TVZLD5mrXWcTBvGF4KK1A',
        'html_url': 'https://canvas.instructure.com/files/319580865/download?download_frd=1&verifier=hPXvy0owVxSkEZ7paw1TVZLD5mrXWcTBvGF4KK1A',
        'content_type': 'application/pdf',
        'size': 153935,
        'created_at': '2025-11-07T05:39:33Z',
        'updated_at': '2025-11-07T05:39:33Z',
        'local_path': os.path.join(os.getcwd(), 'app', 'data', 'courses', '13299557', 'Lec 1.pdf')
    }
    
    try:
        # Test bucket creation/verification
        print(f"\nTesting bucket existence...")
        bucket = ensure_bucket_exists(BUCKET_NAME)
        print(f"✅ Bucket ready: {bucket.name}")
        
        # Test file listing (if any exist)
        print(f"\nTesting file listing...")
        test_course_id = "13299557"
        files = list_course_files(test_course_id, BUCKET_NAME)
        print(f"✅ Found {len(files)} files for course '{test_course_id}'")

        # Test file upload
        print(f"\nTesting file upload...")
        files = upload_course_files([mock_file], test_course_id, BUCKET_NAME)
        print(f"✅ Uploaded file to: {files}")

        files = list_course_files(test_course_id, BUCKET_NAME)
        print(f"✅ Found {len(files)} files for course '{test_course_id}'")

        print("\n🎉 GCS service test complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
