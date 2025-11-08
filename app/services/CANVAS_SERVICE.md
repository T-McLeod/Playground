# Canvas Service Documentation

## Overview
The Canvas service (`canvas_service.py`) handles all interactions with the Canvas LMS API. It provides functions to retrieve course materials, syllabus content, and course information.

## Functions

### `get_course_files(course_id: str, token: str) -> Tuple[List[Dict], Dict]`

Fetches all files from a Canvas course with automatic pagination handling.

**Parameters:**
- `course_id` (str): The Canvas course ID
- `token` (str): Canvas API access token

**Returns:**
- Tuple containing:
  1. `files_list` (List[Dict]): List of file objects
  2. `indexed_files` (Dict): Map of file_id to {hash, url}

**File Object Structure:**
```python
{
    'id': '456',
    'display_name': 'Chapter1.pdf',
    'filename': 'chapter1.pdf',
    'url': 'https://canvas.../download',
    'html_url': 'https://canvas.../files/456',
    'content_type': 'application/pdf',
    'size': 1024000,
    'created_at': '2024-01-01T00:00:00Z',
    'updated_at': '2024-01-01T00:00:00Z'
}
```

**Indexed Files Structure:**
```python
{
    '456': {
        'hash': 'abc123...',  # MD5 or UUID
        'url': 'https://canvas.../download'
    }
}
```

**Features:**
- ✅ Automatic pagination handling (processes all pages)
- ✅ Filters for allowed file types (.pdf, .txt, .md, .doc, .docx)
- ✅ Returns both list and indexed map for different use cases
- ✅ Comprehensive error handling and logging

**Example Usage:**
```python
from app.services.canvas_service import get_course_files

files_list, indexed_files = get_course_files("12345", "canvas_api_token")

print(f"Retrieved {len(files_list)} files")
for file in files_list:
    print(f"  - {file['display_name']} ({file['size']} bytes)")
```

---

### `get_syllabus(course_id: str, token: str) -> str`

Fetches the syllabus content from a Canvas course.

**Parameters:**
- `course_id` (str): The Canvas course ID
- `token` (str): Canvas API access token

**Returns:**
- `str`: Syllabus body (may contain HTML)

**Features:**
- ✅ Retrieves syllabus_body from course data
- ✅ Returns empty string if no syllabus exists
- ✅ Handles HTML content gracefully

**Example Usage:**
```python
from app.services.canvas_service import get_syllabus

syllabus = get_syllabus("12345", "canvas_api_token")

if syllabus:
    print(f"Syllabus: {syllabus[:200]}...")
else:
    print("No syllabus available")
```

---

### `get_course_info(course_id: str, token: str) -> Dict`

Fetches general course information from Canvas.

**Parameters:**
- `course_id` (str): The Canvas course ID
- `token` (str): Canvas API access token

**Returns:**
- `Dict`: Course information object

**Course Info Structure:**
```python
{
    'id': 12345,
    'name': 'Introduction to Biology',
    'course_code': 'BIO101',
    'start_at': '2024-01-15T00:00:00Z',
    'end_at': '2024-05-15T00:00:00Z',
    'enrollment_term_id': 1
}
```

**Example Usage:**
```python
from app.services.canvas_service import get_course_info

info = get_course_info("12345", "canvas_api_token")
print(f"Course: {info['name']} ({info['course_code']})")
```

---

## Configuration

### Canvas API Base URL
The default base URL is:
```python
CANVAS_API_BASE = "https://canvas.instructure.com/api/v1"
```

To use a different Canvas instance, modify this constant in `canvas_service.py`.

### Allowed File Types
By default, the following file types are allowed:
```python
ALLOWED_FILE_TYPES = ['.pdf', '.txt', '.md', '.doc', '.docx']
```

Modify this list to include or exclude file types as needed.

---

## API Authentication

All functions require a Canvas API access token. To generate a token:

1. Log in to Canvas
2. Go to **Account → Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Set purpose and expiration
6. Copy the generated token

**Security Note:** Never commit API tokens to version control. Use environment variables or secure storage.

---

## Error Handling

All functions raise exceptions with descriptive messages on failure:

```python
try:
    files, indexed = get_course_files(course_id, token)
except Exception as e:
    print(f"Failed to fetch files: {e}")
```

Common errors:
- **401 Unauthorized**: Invalid or expired API token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Invalid course ID
- **Network errors**: Connection issues

---

## Logging

The service uses Python's logging module:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Log levels:
- `INFO`: Successful operations, pagination progress
- `WARNING`: Missing data (e.g., empty syllabus)
- `ERROR`: API errors, network failures

---

## Testing

Run the test suite to verify functionality:

```bash
# Update credentials in test_canvas_service.py first
python -m app.services.test_canvas_service
```

Or import and test individual functions:

```python
from app.services.canvas_service import get_course_files

files, indexed = get_course_files("YOUR_COURSE_ID", "YOUR_TOKEN")
assert len(files) > 0, "No files retrieved"
print("✅ Test passed!")
```

---

## Contract Fulfillment

This implementation fulfills the following contract from the Service Briefing:

```python
# Returns: (list_of_file_objects, dict_of_indexed_files_map)
def get_course_files(course_id: str, token: str) -> (list, dict): ...

def get_syllabus(course_id: str, token: str) -> str: ...
```

**Changes from original contract:**
- Added type hints for better code clarity
- Return type is `Tuple[List[Dict], Dict]` instead of `(list, dict)`
- Both formats are functionally equivalent

---

## Usage in the Application

The Canvas service integrates with the main application workflow:

```python
# In routes.py (API Router)
from app.services import canvas_service

@app.route('/api/initialize-course', methods=['POST'])
def initialize_course():
    course_id = request.json.get('course_id')
    canvas_token = get_canvas_token()  # From session or config
    
    # Fetch all course files
    files, indexed = canvas_service.get_course_files(course_id, canvas_token)
    
    # Pass to RAG service for indexing
    corpus_id = rag_service.create_and_provision_corpus(files, canvas_token)
    
    # Build knowledge graph
    kg_data = kg_service.build_knowledge_graph(topics, corpus_id, files)
    
    return jsonify({"status": "complete"})
```

---

## Next Steps

After the Canvas service is complete, the following services need implementation:

1. ✅ **canvas_service.py** - Complete
2. ⏳ **rag_service.py** - Next (Vertex AI RAG Engine)
3. ⏳ **kg_service.py** - Pending (Knowledge Graph)
4. ⏳ **firestore_service.py** - Pending (Database)

---

## Support

For Canvas API documentation, visit:
https://canvas.instructure.com/doc/api/

For issues or questions about this implementation, refer to the project documentation or contact the team lead.
