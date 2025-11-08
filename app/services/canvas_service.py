"""
Canvas API Service
Handles all Canvas API calls for fetching course materials.

This service provides functions to:
1. Fetch all course files (with pagination support)
2. Retrieve course syllabus content

All functions use the Canvas REST API and handle authentication via API tokens.
"""
import requests
from typing import Tuple, Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Canvas API configuration
CANVAS_API_BASE = "https://canvas.instructure.com/api/v1"
ALLOWED_FILE_TYPES = ['.pdf', '.txt', '.md', '.doc', '.docx']


def get_course_files(course_id: str, token: str) -> Tuple[List[Dict], Dict]:
    """
    Fetches all files from a Canvas course with pagination support.
    Filters for allowed file types and returns both a list and indexed map.
    
    Args:
        course_id: The Canvas course ID
        token: Canvas API access token
        
    Returns:
        Tuple containing:
        - list: List of file objects with id, display_name, url, etc.
        - dict: Indexed files map for Firestore (file_id -> {hash, url})
        
    Example:
        files, indexed = get_course_files("12345", "canvas_token")
        # files = [{'id': '456', 'display_name': 'Chapter1.pdf', ...}, ...]
        # indexed = {'456': {'hash': 'abc123', 'url': 'https://...'}, ...}
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    files_list = []
    indexed_files = {}
    
    # Initial API endpoint
    url = f"{CANVAS_API_BASE}/courses/{course_id}/files"
    params = {'per_page': 100}  # Max items per page
    
    logger.info(f"Fetching files for course {course_id}...")
    
    try:
        while url:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            page_files = response.json()
            logger.info(f"Retrieved {len(page_files)} files from current page")
            
            # Process each file
            for file in page_files:
                # Get file extension
                filename = file.get('display_name', '')
                file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
                
                # Filter for allowed file types
                if file_ext in ALLOWED_FILE_TYPES:
                    file_obj = {
                        'id': str(file.get('id')),
                        'display_name': file.get('display_name'),
                        'filename': file.get('filename'),
                        'url': file.get('url'),  # Download URL
                        'html_url': file.get('url'),  # Canvas web URL
                        'content_type': file.get('content-type', 'application/pdf'),
                        'size': file.get('size', 0),
                        'created_at': file.get('created_at'),
                        'updated_at': file.get('updated_at')
                    }
                    
                    # Determine hash (prefer md5, fallback to uuid)
                    file_hash = file.get('md5') or file.get('uuid') or file.get('id')
                    
                    files_list.append(file_obj)
                    
                    # Create indexed entry
                    indexed_files[str(file.get('id'))] = {
                        'hash': file_hash,
                        'url': file.get('url')
                    }
            
            # Handle pagination via Link header
            url = None
            params = None  # Clear params for subsequent requests
            
            if 'Link' in response.headers:
                links = response.headers['Link'].split(',')
                for link in links:
                    if 'rel="next"' in link:
                        # Extract URL from <URL>; rel="next"
                        url = link[link.find('<')+1:link.find('>')]
                        logger.info(f"Following pagination to next page...")
                        break
        
        logger.info(f"Successfully retrieved {len(files_list)} total files (filtered)")
        return files_list, indexed_files
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching course files: {str(e)}")
        raise Exception(f"Failed to fetch course files: {str(e)}")


def get_syllabus(course_id: str, token: str) -> str:
    """
    Fetches the syllabus content from a Canvas course.
    
    Args:
        course_id: The Canvas course ID
        token: Canvas API access token
        
    Returns:
        Syllabus body as a string (may contain HTML)
        
    Example:
        syllabus = get_syllabus("12345", "canvas_token")
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{CANVAS_API_BASE}/courses/{course_id}"
    params = {'include[]': 'syllabus_body'}
    
    logger.info(f"Fetching syllabus for course {course_id}...")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        course_data = response.json()
        syllabus_body = course_data.get('syllabus_body', '')
        
        if syllabus_body:
            logger.info(f"Successfully retrieved syllabus ({len(syllabus_body)} characters)")
        else:
            logger.warning(f"No syllabus found for course {course_id}")
        
        return syllabus_body
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching syllabus: {str(e)}")
        raise Exception(f"Failed to fetch syllabus: {str(e)}")


def get_course_info(course_id: str, token: str) -> Dict:
    """
    Fetches general course information from Canvas.
    
    Args:
        course_id: The Canvas course ID
        token: Canvas API access token
        
    Returns:
        Dictionary containing course information
        
    Example:
        info = get_course_info("12345", "canvas_token")
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{CANVAS_API_BASE}/courses/{course_id}"
    
    logger.info(f"Fetching course info for course {course_id}...")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        course_data = response.json()
        logger.info(f"Successfully retrieved course info")
        
        return {
            'id': course_data.get('id'),
            'name': course_data.get('name'),
            'course_code': course_data.get('course_code'),
            'start_at': course_data.get('start_at'),
            'end_at': course_data.get('end_at'),
            'enrollment_term_id': course_data.get('enrollment_term_id')
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching course info: {str(e)}")
        raise Exception(f"Failed to fetch course info: {str(e)}")
