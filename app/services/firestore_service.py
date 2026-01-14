"""
Firestore Service
Handles all Cloud Firestore operations for course data persistence.
"""
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.collection import CollectionReference
import os
import logging

logger = logging.getLogger(__name__)

# Get GCP configuration from environment
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
DATABASE = os.environ.get('FIRESTORE_DATABASE', '(default)')

# Initialize Firestore client
# If GOOGLE_APPLICATION_CREDENTIALS is set, it will be used automatically
# Otherwise, it will use Application Default Credentials (ADC)
try:
    if PROJECT_ID:
        db = firestore.Client(project=PROJECT_ID, database=DATABASE)
        logger.info(f"Firestore initialized for project: {PROJECT_ID}")
    else:
        db = firestore.Client(database=DATABASE)
        logger.warning("GOOGLE_CLOUD_PROJECT not set, using default project")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    db = None

PLAYGROUNDS_COLLECTION = 'playgrounds'
GRAPH_NODES_COLLECTION = 'graph_nodes'
FILES_COLLECTION = 'files'
ANALYTICS_COLLECTION = 'course_analytics'
REPORTS_COLLECTION = 'analytics_reports'


def _ensure_db():
    """Ensure database is initialized."""
    if db is None:
        raise RuntimeError(
            "Firestore not initialized. Please check GOOGLE_CLOUD_PROJECT "
            "and GOOGLE_APPLICATION_CREDENTIALS environment variables."
        )


def get_course_state(playground_id: str) -> str:
    """
    Returns the current state of the course.
    
    Args:
        course_id: The Canvas course ID (context_id)
        
    Returns:
        One of: 'NEEDS_INIT', 'GENERATING', 'ACTIVE'
    """
    _ensure_db()
    try:
        doc = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).get()
        
        if not doc.exists:
            return 'NEEDS_INIT'
        status = doc.get('status')
        if status == 'GENERATING':
            return 'GENERATING'
        elif status == 'ACTIVE':
            return 'ACTIVE'
        else:
            return 'NOT_READY'
    except Exception as e:
        logger.error(f"Error accessing Firestore database: {e}")
        if "Missing or insufficient permissions" in str(e):
            logger.error("Service account lacks Firestore permissions. Please grant 'Cloud Datastore User' role.")
        # If database doesn't exist or other error, return NEEDS_INIT
        return 'NEEDS_INIT'


def is_canvas_course(playground_id: str) -> bool:
    """
    Checks if the playground is associated with a Canvas course.
    
    Args:
        playground_id: The playground document ID
    Returns:
        True if associated with a Canvas course, False otherwise
    """
    _ensure_db()
    doc = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).get()
    if not doc.exists:
        return False
    source = doc.get('source')
    return source.get('type') == 'canvas_course'


def create_playground_entity(
    name: str,
    source_type: str = "standalone",
    course_id: str = None
) -> str:
    """
    Creates a standardized playground document in Firestore.
    This is the single source of truth for playground entity creation.
    
    Args:
        name: Display name for the playground
        source_type: Either "standalone" or "canvas"
        course_id: Canvas course ID (required if source_type is "canvas")
        
    Returns:
        playground_id: The generated document ID
    """
    _ensure_db()
    
    # Build source metadata based on type
    if source_type == "canvas":
        if not course_id:
            raise ValueError("course_id is required for canvas source type")
        source = {
            'type': 'canvas',
            'course_id': course_id
        }
    else:
        source = {
            'type': 'standalone'
        }
    
    # Create the playground document with standardized schema
    playground_ref = db.collection(PLAYGROUNDS_COLLECTION).document()
    playground_data = {
        'display_name': name,
        'created_at': firestore.SERVER_TIMESTAMP,
        'last_modified_at': firestore.SERVER_TIMESTAMP,
        'source': source,
        'status': 'CREATED',
        'corpus_id': None,  # Will be set after RAG provisioning
        'config': {
            'model': 'default',
            'temperature': 0.7
        }
    }
    
    playground_ref.set(playground_data)
    logger.info(f"Created playground entity: {playground_ref.id} ({name})")
    
    return playground_ref.id


def add_init_log(course_id: str, message: str, level: str = 'info') -> None:
    """
    Adds a log message to the course document during initialization.
    
    Args:
        course_id: The Canvas course ID
        message: The log message
        level: Log level ('info', 'success', 'warning', 'error')
    """
    _ensure_db()
    import time
    from google.cloud.firestore_v1 import ArrayUnion
    log_entry = {
        'message': message,
        'level': level,
        'timestamp': time.time()
    }
    db.collection(PLAYGROUNDS_COLLECTION).document(course_id).update({
        'init_logs': ArrayUnion([log_entry])
    })


def get_init_logs(course_id: str) -> list:
    """
    Retrieves initialization logs for a course.
    
    Args:
        course_id: The Canvas course ID
        
    Returns:
        List of log entries
    """
    _ensure_db()
    doc = db.collection(PLAYGROUNDS_COLLECTION).document(course_id).get()
    if doc.exists:
        return doc.get('init_logs', [])
    return []


def get_playground_data(playground_id: str):
    """
    Fetches the complete playground document.
    
    Args:
        playground_id: The playground document ID
        
    Returns:
        DocumentSnapshot containing all playground data
    """
    _ensure_db()
    return db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).get()


def get_canvas_course_id(playground_id: str) -> str | None:
    """
    Retrieves the Canvas course ID associated with a playground.
    
    Args:
        playground_id: The playground document ID
        
    Returns:
        The Canvas course ID, or None if not found
    """
    _ensure_db()
    doc = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).get()
    if doc.exists:
        source = doc.get('source')
        return source.get('course_id')
    return None


def initialize_file(playground_id: str) -> str:
    """
    Creates a new file document in the files subcollection for a playground.
    
    Args:
        playground_id: The playground document ID
    Returns:
        The new file document ID
    """
    _ensure_db()
    file_collection = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).collection("files")
    new_file_ref = file_collection.document()
    new_file_ref.set({
        'created_at': firestore.SERVER_TIMESTAMP,
        'status': 'initialized'
    })
    return new_file_ref.id


REQUIRED_FILE_FIELDS = ["name", "size", "gcs_uri", "content_type", "source"]
def add_files(playground_id: str, files: list[dict]) -> None:
    """
    Adds or updates the indexed_files field in the course document.
    
    Args:
        playground_id: The playground document ID
        files: List of dictionaries representing indexed files to add/update
    """
    _ensure_db()

    batch = db.batch()
    file_collection = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).collection("files")

    for file in files:
        # Validate required fields
        for field in REQUIRED_FILE_FIELDS:
            if field not in file:
                raise ValueError(f"File is missing required field: {field}")
            
        if 'id' not in file:
            file_id = file_collection.document().id
            file_document = file_collection.document(file_id)
            file['id'] = file_id
        else:
            file_document = file_collection.document(file['id'])
        
        batch.set(file_document, file)

    batch.commit()


def update_status(course_id: str, status: str) -> None:
    """
    Updates the status field in the course document.
    
    Args:
        course_id: The Canvas course ID
        status: The new status value for the course
    """
    _ensure_db()
    db.collection(PLAYGROUNDS_COLLECTION).document(course_id).update({
        'status': status
    })


def add_corpus_id(playground_id: str, corpus_id: str) -> None:
    """
    Adds the corpus_id field to the course document.
    
    Args:
        playground_id: The playground document ID
        corpus_id: The RAG corpus ID
    """
    _ensure_db()
    db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).set({
        'corpus_id': corpus_id
    }, merge=True)


def get_corpus_id(playground_id: str) -> str:
    """
    Retrieves the corpus_id field from the course document.
    
    Args:
        playground_id: The playground document ID
    Returns:
        The RAG corpus ID, or None if not set
    """
    _ensure_db()
    doc = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).get()
    return doc.get('corpus_id')


# call with dictionary of:
# corpus_id, indexed_files, kg_nodes, kg_edges, kg_data
def finalize_course_doc(course_id: str, data: dict) -> None:
    """
    Updates the course document with all RAG/KG data and sets status to ACTIVE.
    
    Args:
        course_id: The Canvas course ID
        data: Dictionary containing corpus_id, indexed_files, kg_nodes, kg_edges, kg_data
    """
    _ensure_db()
    db.collection(PLAYGROUNDS_COLLECTION).document(course_id).update({
        'status': 'ACTIVE',
        'kg_nodes': data.get('kg_nodes'),
        'kg_edges': data.get('kg_edges'),
        'kg_data': data.get('kg_data')
    })


def get_node_collection(playground_id: str) -> CollectionReference:
    """
    Returns the graph_nodes subcollection reference for a playground.
    
    Args:
        playground_id: The playground document ID
    Returns:
        CollectionReference for the graph_nodes subcollection
    """
    _ensure_db()
    return db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).collection(GRAPH_NODES_COLLECTION)


def get_file_map(playground_id: str) -> dict:
    """
    Returns a mapping of file document IDs to their data for a playground.
    
    Args:
        playground_id: The playground document ID
    
    Returns:
        dict: A dictionary where keys are file document IDs and values are file data dictionaries.
    """
    _ensure_db()
    files = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).collection(FILES_COLLECTION).stream()
    file_map = {file.id: file.to_dict() for file in files}
    return file_map


def get_file_by_id(playground_id: str, file_id: str) -> dict | None:
    """
    Retrieves a file document from the files subcollection.
    
    Args:
        playground_id: The playground document ID
        file_id: The file document ID
        
    Returns:
        Dictionary containing file data with doc_id, or None if not found
    """
    _ensure_db()
    
    file_ref = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).collection(FILES_COLLECTION).document(file_id)
    file_doc = file_ref.get()
    
    if not file_doc.exists:
        return None
    
    file_data = file_doc.to_dict()
    file_data['doc_id'] = file_doc.id
    return file_data


def delete_file_document(playground_id: str, file_id: str) -> None:
    """
    Deletes a file document from the files subcollection.
    
    Args:
        playground_id: The playground document ID
        file_id: The file document ID to delete
    """
    _ensure_db()
    
    file_ref = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).collection(FILES_COLLECTION).document(file_id)
    file_ref.delete()


def register_uploaded_file(playground_id: str, file_id: str, file_data: dict) -> str:
    """
    Registers a file uploaded via signed URL in Firestore.
    
    Args:
        playground_id: The playground document ID
        file_id: The unique file ID (from signed URL generation)
        file_data: Dictionary containing file metadata:
            - name: Original filename
            - display_name: Display name
            - size: File size in bytes
            - content_type: MIME type
            - gcs_uri: GCS URI where file is stored
            - source: Source information dict
            - status: Current status (e.g., 'uploaded', 'indexed')
            - indexed: Boolean indicating if file is indexed in RAG
            
    Returns:
        The file document ID
    """
    _ensure_db()
    
    file_ref = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id).collection(FILES_COLLECTION).document(file_id)
    file_ref.set(file_data)
    
    logger.info(f"Registered uploaded file: {file_data.get('name')} ({file_id}) for playground {playground_id}")
    return file_id


def log_analytics_event(data: dict) -> str:
    """
    Logs an analytics event (chat query or KG click) to Firestore.
    
    Args:
        data: Pre-formatted dictionary containing event data.
              Must include: type, course_id, timestamp, and type-specific fields
              
    Returns:
        The document ID of the newly created log entry
        
    Example:
        doc_id = log_analytics_event({
            'type': 'chat',
            'course_id': '12345',
            'query_text': 'What is ML?',
            'query_vector': [0.1, 0.2, ...],
            'timestamp': firestore.SERVER_TIMESTAMP,
            'rating': None
        })
    """
    _ensure_db()
    
    # Create a new document with auto-generated ID
    doc_ref = db.collection(ANALYTICS_COLLECTION).document()
    doc_ref.set(data)
    
    logger.info(f"Logged analytics event: {data.get('type')} for course {data.get('course_id')}")
    
    return doc_ref.id


def get_analytics_events(course_id: str, event_type: str = None) -> list[dict]:
    """
    Fetches analytics events for a course.
    Generic query function - returns all event data for the analytics services to parse.
    
    Args:
        course_id: The Canvas course ID
        event_type: Optional - filter by event type ('chat', 'kg_click', etc.)
                   If None, returns all events for the course
        
    Returns:
        List of dictionaries containing full event data with doc_id
        Example: [
            {
                "doc_id": "xyz123",
                "type": "chat",
                "course_id": "12345",
                "query_text": "What is ML?",
                "query_vector": [0.1, 0.2, ...],
                "timestamp": ...,
                "rating": None
            },
            ...
        ]
    """
    _ensure_db()

    
    query = db.collection(ANALYTICS_COLLECTION).where(filter=FieldFilter('course_id', '==', course_id))
    
    if event_type:
        query = query.where(filter=FieldFilter('type', '==', event_type))
    
    # Fetch all matching documents
    results = []
    for doc in query.stream():
        doc_data = doc.to_dict()
        doc_data['doc_id'] = doc.id  # Include the document ID
        results.append(doc_data)
    
    logger.info(f"Retrieved {len(results)} analytics events for course {course_id}" + 
                (f" (type: {event_type})" if event_type else ""))
    return results


def get_analytics_events_by_ids(doc_ids: list[str]) -> list[dict]:
    """
    Fetches analytics events by document IDs.
    Handles batching automatically (Firestore 'in' queries limited to 10 items).
    
    Args:
        doc_ids: List of Firestore document IDs
        
    Returns:
        List of dictionaries containing full event data with doc_id
        
    Example:
        events = get_analytics_events_by_ids(['doc1', 'doc2', 'doc3'])
        # Returns: [{"doc_id": "doc1", "query_text": "...", ...}, ...]
    """
    _ensure_db()
    
    if not doc_ids:
        return []
    # Firestore 'in' queries are limited to 10 items, so batch if needed
    results = []
    batch_size = 10
    
    for i in range(0, len(doc_ids), batch_size):
        batch = doc_ids[i:i + batch_size]
        
        # Query using document IDs with filter keyword argument
        docs = db.collection(ANALYTICS_COLLECTION).where(
            filter=FieldFilter(
                '__name__', 
                'in', 
                [db.collection(ANALYTICS_COLLECTION).document(doc_id) for doc_id in batch]
            )
        ).stream()
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['doc_id'] = doc.id  # Include the document ID
            results.append(doc_data)
    
    logger.info(f"Retrieved {len(results)} analytics events from {len(doc_ids)} document IDs")
    return results


def save_analytics_report(course_id: str, report_data: dict) -> None:
    """
    Saves or updates the analytics report for a course.
    
    Args:
        course_id: The Canvas course ID
        report_data: Dictionary containing the analytics report
                    (cluster labels, counts, top queries, etc.)
    """
    _ensure_db()
    
    # Set (overwrite) the report document
    db.collection(REPORTS_COLLECTION).document(course_id).set(report_data)
    
    logger.info(f"Saved analytics report for course {course_id}")


def get_analytics_report(course_id: str) -> dict:
    """
    Retrieves the latest analytics report for a course.
    
    Args:
        course_id: The Canvas course ID
        
    Returns:
        Dictionary containing the analytics report, or empty dict if not found
    """
    _ensure_db()
    
    doc = db.collection(REPORTS_COLLECTION).document(course_id).get()
    
    if doc.exists:
        logger.info(f"Retrieved analytics report for course {course_id}")
        return doc.to_dict()
    else:
        logger.warning(f"No analytics report found for course {course_id}")
        return {}


def rate_analytics_event(doc_id: str, rating: str = None) -> None:
    """
    Updates the rating field of an analytics event.
    
    Args:
        doc_id: The Firestore document ID of the analytics event
        rating: The rating value (e.g., 'helpful', 'not_helpful')
                If None, removes the rating field from the document
    """
    _ensure_db()
    
    if rating is None:
        # Remove the rating field
        db.collection(ANALYTICS_COLLECTION).document(doc_id).update({
            'rating': firestore.DELETE_FIELD
        })
        logger.info(f"Removed rating for analytics event {doc_id}")
    else:
        db.collection(ANALYTICS_COLLECTION).document(doc_id).update({
            'rating': rating
        })
        logger.info(f"Updated rating for analytics event {doc_id}: {rating}")


# Not scalable for large numbers of courses, but fine for current use case
def get_playground_id_for_course(course_id: str) -> str | None:
    """
    Retrieves the playground document ID associated with a Canvas course.
    
    Args:
        course_id: The Canvas course ID
        
    Returns:
        The playground document ID, or None if not found
    """
    _ensure_db()
    
    query = db.collection("playgrounds").where(
        filter=FieldFilter('source.course_id', '==', course_id)
    ).limit(1)
    
    docs = query.stream()
    for doc in docs:
        return doc.id  # Return the first matching document ID
    
    logger.warning(f"No playground found for course {course_id}")
    return None