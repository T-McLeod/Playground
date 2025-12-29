"""
Firestore Service
Handles all Cloud Firestore operations for course data persistence.
"""
from typing import Any
import uuid
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import os
import logging

logger = logging.getLogger(__name__)

# Get GCP configuration from environment
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

# Initialize Firestore client
# If GOOGLE_APPLICATION_CREDENTIALS is set, it will be used automatically
# Otherwise, it will use Application Default Credentials (ADC)
try:
    if PROJECT_ID:
        db = firestore.Client(project=PROJECT_ID)
        logger.info(f"Firestore initialized for project: {PROJECT_ID}")
    else:
        db = firestore.Client()
        logger.warning("GOOGLE_CLOUD_PROJECT not set, using default project")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    db = None

COURSES_COLLECTION = 'courses'
PLAYGROUNDS_COLLECTION = 'playgrounds'
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


# Only for playgrounds created from Canvas courses for right now
def create_playground_doc(display_name: str, course_id: str) -> Any:
    new_id = db.collection("playgrounds").document().id

    db.collection("playgrounds").document(new_id).set({
        'display_name': display_name,
        'created_at': firestore.SERVER_TIMESTAMP,
        'last_modified_at': firestore.SERVER_TIMESTAMP,
        'source': {
            'type': 'canvas_course',
            'course_id': course_id
        }
    })

    return new_id


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


# returns the google.cloud.firestore.document.DocumentSnapshot class
def get_course_data(course_id: str):
    """
    Fetches the complete course document.
    
    Args:
        course_id: The Canvas course ID
        
    Returns:
        DocumentSnapshot containing all course data
    """
    _ensure_db()
    return db.collection(COURSES_COLLECTION).document(course_id).get()


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


def add_files(course_id: str, data: dict) -> None:
    """
    Adds or updates the indexed_files field in the course document.
    
    Args:
        course_id: The Canvas course ID
        data: Dictionary of indexed files to add/update
    """
    _ensure_db()
    db.collection(COURSES_COLLECTION).document(course_id).set({
        'indexed_files': data
    }, merge=True)


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


def add_corpus_id(course_id: str, corpus_id: str) -> None:
    """
    Adds the corpus_id field to the course document.
    
    Args:
        course_id: The Canvas course ID
        corpus_id: The RAG corpus ID
    """
    _ensure_db()
    db.collection(PLAYGROUNDS_COLLECTION).document(course_id).set({
        'corpus_id': corpus_id
    }, merge=True)


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

def update_knowledge_graph(playground_id: str = None, kg_nodes: list = None, kg_edges: list = None, kg_data: dict = None, course_id: str = None) -> None:
    """
    Updates only the knowledge graph portion of a course/playground document.
    Does NOT overwrite corpus_id, indexed_files, or status.

    Args:
        playground_id: The playground document ID (preferred)
        kg_nodes: Updated list of node dicts
        kg_edges: Updated list of edge dicts
        kg_data:  Updated dict keyed by topic_id
        course_id: Deprecated - use playground_id instead
    """
    _ensure_db()
    
    # Support both playground_id and legacy course_id
    doc_id = playground_id or course_id
    if not doc_id:
        raise ValueError("Either playground_id or course_id must be provided")

    update_payload = {
        'kg_nodes': kg_nodes,
        'kg_edges': kg_edges,
        'kg_data':  kg_data
    }

    db.collection(PLAYGROUNDS_COLLECTION).document(doc_id).update(update_payload)

    logger.info(f"Updated knowledge graph for playground {doc_id}")



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