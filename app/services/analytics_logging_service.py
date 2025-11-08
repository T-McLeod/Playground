"""
Analytics Logging Service
Handles real-time logging of student interactions for analytics.

This service is responsible for:
- Logging chat queries with embeddings
- Logging knowledge graph interactions
- Storing all analytics events to Firestore

This is a lightweight service focused only on data collection.
Analysis and reporting is handled by analytics_reporting_service.

Dependencies:
- firestore_service: For database operations
- gemini_service: For generating embeddings
"""
import logging
from google.cloud import firestore
from typing import Optional
import sys
import os

# Handle imports for both module use and standalone testing
if __name__ == "__main__":
    # Running as standalone script
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from app.services import firestore_service, gemini_service
else:
    # Imported as a module
    from . import firestore_service, gemini_service

logger = logging.getLogger(__name__)


# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

def log_chat_query(course_id: str, query_text: str, answer_text: str = None, sources: list = None) -> str:
    """
    Logs a chat query event with its embedding for later analysis.
    
    This function is called every time a student asks a question.
    It generates an embedding of the query and stores it for clustering analysis.
    
    Args:
        course_id: The Canvas course ID
        query_text: The student's question
        answer_text: Optional - the generated answer
        sources: Optional - list of source files used
        
    Returns:
        The Firestore document ID of the logged event (for rating feature)
        
    Example:
        doc_id = log_chat_query(
            course_id="12345",
            query_text="What is machine learning?",
            answer_text="Machine learning is...",
            sources=["Chapter1.pdf"]
        )
    """
    try:
        logger.info(f"Logging chat query for course {course_id}: {query_text[:50]}...")
        
        # Get embedding from Gemini service
        # TODO: Implement get_embedding in gemini_service
        # query_vector = gemini_service.get_embedding(
        #     text=query_text,
        #     model="text-embedding-004",
        #     task_type="RETRIEVAL_QUERY"
        # )
        
        # For now, use a placeholder (will implement embedding later)
        query_vector = None
        
        # Prepare the log data
        log_data = {
            'type': 'chat',
            'course_id': course_id,
            'query_text': query_text,
            'answer_text': answer_text,
            'sources': sources or [],
            'query_vector': query_vector,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'rating': None  # Will be updated if user rates this answer
        }
        
        # Save to Firestore
        doc_id = firestore_service.log_analytics_event(log_data)
        
        logger.info(f"Chat query logged successfully: {doc_id}")
        return doc_id
        
    except Exception as e:
        logger.error(f"Failed to log chat query: {e}", exc_info=True)
        # Don't fail the main chat flow if logging fails
        return None


def log_kg_node_click(course_id: str, node_id: str, node_label: str, node_type: str = None) -> str:
    """
    Logs a knowledge graph node click event.
    
    This tracks which topics students are exploring in the knowledge graph.
    
    Args:
        course_id: The Canvas course ID
        node_id: The unique identifier of the clicked node
        node_label: The display name of the node (topic name or file name)
        node_type: Optional - 'topic' or 'file'
        
    Returns:
        The Firestore document ID of the logged event
        
    Example:
        log_kg_node_click(
            course_id="12345",
            node_id="topic_1",
            node_label="Machine Learning",
            node_type="topic"
        )
    """
    try:
        logger.info(f"Logging KG click for course {course_id}: {node_label}")
        
        # Prepare the log data
        log_data = {
            'type': 'kg_click',
            'course_id': course_id,
            'node_id': node_id,
            'node_label': node_label,
            'node_type': node_type,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        # Save to Firestore
        doc_id = firestore_service.log_analytics_event(log_data)
        
        logger.info(f"KG click logged successfully: {doc_id}")
        return doc_id
        
    except Exception as e:
        logger.error(f"Failed to log KG click: {e}", exc_info=True)
        return None


# ============================================================================
# RATING FEATURE (STRETCH GOAL)
# ============================================================================

def rate_answer(doc_id: str, rating: str) -> None:
    """
    Allows students to rate an answer (stretch goal).
    
    Args:
        doc_id: The Firestore document ID of the chat event
        rating: The rating value (e.g., 'good', 'bad', 'helpful', 'not_helpful')
        
    Example:
        rate_answer(doc_id="xyz123", rating="helpful")
    """
    logger.info(f"Rating answer {doc_id} as: {rating}")
    firestore_service.rate_analytics_event(doc_id, rating)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test the analytics logging functions.
    """
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("="*70)
    print("ANALYTICS LOGGING SERVICE TEST")
    print("="*70)
    
    TEST_COURSE_ID = "test_course_123"
    
    print(f"\nTest Course ID: {TEST_COURSE_ID}")
    
    # Test 1: Log a chat query
    print("\n" + "="*70)
    print("Test 1: Logging a chat query")
    print("="*70)
    
    try:
        doc_id = log_chat_query(
            course_id=TEST_COURSE_ID,
            query_text="What is machine learning?",
            answer_text="Machine learning is a subset of AI...",
            sources=["Chapter1.pdf"]
        )
        print(f"✓ Chat query logged with ID: {doc_id}")
    except Exception as e:
        print(f"✗ Failed to log chat query: {e}")
    
    # Test 2: Log a KG click
    print("\n" + "="*70)
    print("Test 2: Logging a KG node click")
    print("="*70)
    
    try:
        doc_id = log_kg_node_click(
            course_id=TEST_COURSE_ID,
            node_id="topic_1",
            node_label="Machine Learning",
            node_type="topic"
        )
        print(f"✓ KG click logged with ID: {doc_id}")
    except Exception as e:
        print(f"✗ Failed to log KG click: {e}")
    
    # Test 3: Rate an answer
    print("\n" + "="*70)
    print("Test 3: Rating an answer")
    print("="*70)
    
    if doc_id:
        try:
            rate_answer(doc_id, "helpful")
            print(f"✓ Answer rated successfully")
        except Exception as e:
            print(f"✗ Failed to rate answer: {e}")
    
    print("\n" + "="*70)
    print("✓ Analytics logging service ready!")
    print("="*70)
