"""
Firestore Service
Handles all Cloud Firestore operations for course data persistence.
"""
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
ANALYTICS_COLLECTION = 'course_analytics'
REPORTS_COLLECTION = 'analytics_reports'


def _ensure_db():
    """Ensure database is initialized."""
    if db is None:
        raise RuntimeError(
            "Firestore not initialized. Please check GOOGLE_CLOUD_PROJECT "
            "and GOOGLE_APPLICATION_CREDENTIALS environment variables."
        )


def get_course_state(course_id: str) -> str:
    """
    Returns the current state of the course.
    
    Args:
        course_id: The Canvas course ID (context_id)
        
    Returns:
        One of: 'NEEDS_INIT', 'GENERATING', 'ACTIVE'
    """
    _ensure_db()
    doc = db.collection(COURSES_COLLECTION).document(course_id).get()
    
    if not doc.exists:
        return 'NEEDS_INIT'
    status = doc.get('status')
    if status == 'GENERATING':
        return 'GENERATING'
    elif status == 'ACTIVE':
        return 'ACTIVE'
    else:
        return 'NOT_READY'



def create_course_doc(course_id: str) -> None:
    """
    Creates the initial course document with GENERATING status.
    
    Args:
        course_id: The Canvas course ID
    """
    _ensure_db()
    #sets status to GENERATING
    db.collection(COURSES_COLLECTION).document(course_id).set({
        'status': 'GENERATING'
    })


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
    db.collection(COURSES_COLLECTION).document(course_id).update({
        'status': 'ACTIVE',
        'corpus_id': data.get('corpus_id'),
        'indexed_files': data.get('indexed_files'),
        'kg_nodes': data.get('kg_nodes'),
        'kg_edges': data.get('kg_edges'),
        'kg_data': data.get('kg_data')
    })


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


def rate_analytics_event(doc_id: str, rating: str) -> None:
    """
    Updates the rating field of an analytics event.
    
    Args:
        doc_id: The Firestore document ID of the analytics event
        rating: The rating value (e.g., 'helpful', 'not_helpful', 'good', 'bad')
    """
    _ensure_db()
    
    db.collection(ANALYTICS_COLLECTION).document(doc_id).update({
        'rating': rating
    })
    
    logger.info(f"Updated rating for analytics event {doc_id}: {rating}")

if __name__ == "__main__":
    # Test Firestore credentials and connection
    from dotenv import load_dotenv
    
    print("="*70)
    print("FIRESTORE SERVICE TEST")
    print("="*70)
    
    # Load environment variables
    load_dotenv()
    
    # Re-initialize after loading env
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
    
    print(f"\nEnvironment Variables:")
    print(f"  GOOGLE_CLOUD_PROJECT: {PROJECT_ID or 'NOT SET'}")

    db = firestore.Client(project=PROJECT_ID)
    test_course_id = 'test_course_12345'

    print(f"Creating course document for {test_course_id}...")
    create_course_doc(test_course_id)
    print("Course document created.")
    state = get_course_state(test_course_id)
    print(f"Course state: {state}")
    
    mock_data = {
        'corpus_id': 'mock_corpus_001',
        'indexed_files': {'file1.pdf': 'gcs://bucket/file1.pdf'},
        'kg_nodes': [{'id': 'node1', 'label': 'Topic 1'}],
        'kg_edges': [{'source': 'node1', 'target': 'node2', 'relation': 'related_to'}],
        'kg_data': {'summary': 'This is a mock knowledge graph.'}
    }
    finalize_course_doc(test_course_id, mock_data)

    course_data = get_course_data(test_course_id)
    print(f"\nFinal Course Document Data for {test_course_id}:")
    print(course_data.to_dict())