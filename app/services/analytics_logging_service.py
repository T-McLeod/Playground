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
# HELPER FUNCTIONS
# ============================================================================

def get_query_vector(query_text: str) -> list:
    """
    Generates an embedding vector for a query using Gemini's text-embedding model.
    
    Args:
        query_text: The text to embed
        
    Returns:
        List of floats representing the embedding vector
        
    Example:
        vector = get_query_vector("What is machine learning?")
        # Returns: [0.123, -0.456, 0.789, ...]
    """
    try:
        logger.info(f"Generating embedding for query: {query_text[:50]}...")
        
        # Use Gemini's text-embedding model for query embeddings
        vector = gemini_service.get_embedding(
            text=query_text,
            model_name="text-embedding-004",
            task_type="RETRIEVAL_QUERY"
        )
        
        return vector
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}", exc_info=True)
        return None


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
        
        # Get embedding vector for the query
        query_vector = get_query_vector(query_text)
        
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
    Script to randomly rate existing queries in Firestore.
    Fetches chat queries and assigns random helpful/not_helpful ratings.
    """
    from dotenv import load_dotenv
    import time
    import random
    
    load_dotenv()
    
    print("="*70)
    print("RANDOM RATING SCRIPT FOR ANALYTICS TESTING")
    print("="*70)
    
    # Configuration
    COURSE_ID = "13299557"  # Update this to your course ID
    
    print(f"\nCourse ID: {COURSE_ID}")
    print(f"\nFetching existing chat queries...")
    print("="*70)
    
    try:
        # Fetch existing chat events
        events = firestore_service.get_analytics_events(COURSE_ID, event_type='chat')
        
        if not events:
            print("\n❌ No chat queries found for this course.")
            print("Run the chat interface or batch logging script first to create queries.")
            exit(1)
        
        print(f"\n✓ Found {len(events)} chat queries")
        print(f"\nRandomly rating queries...")
        print("="*70)
        
        rated_count = 0
        skipped_count = 0
        
        for i, event in enumerate(events, 1):
            doc_id = event.get('doc_id')
            query_text = event.get('query_text', 'N/A')
            current_rating = event.get('rating')
            
            if not doc_id:
                print(f"\n[{i}/{len(events)}] ⚠️  Skipped: No doc_id found")
                skipped_count += 1
                continue
            
            # Randomly choose a rating (60% helpful, 30% not_helpful, 10% skip for no rating)
            rand = random.random()
            if rand < 0.7:
                # 10% chance to skip (leave unrated)
                print(f"\n[{i}/{len(events)}] ⚪ Skipped (no rating): {query_text[:50]}...")
                print(f"  doc_id: {doc_id}")
                skipped_count += 1
                continue
            elif rand < 0.8:
                # 60% chance for helpful
                rating = "helpful"
                emoji = "👍"
            else:
                # 30% chance for not_helpful
                rating = "not_helpful"
                emoji = "👎"
            
            print(f"\n[{i}/{len(events)}] {emoji} Rating as '{rating}': {query_text[:50]}...")
            print(f"  doc_id: {doc_id}")
            
            try:
                # Rate the answer
                rate_answer(doc_id, rating)
                rated_count += 1
                print(f"  ✓ Successfully rated")
                
                # Small delay to avoid overwhelming Firestore
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  ✗ Error rating: {e}")
        
        print(f"\n{'='*70}")
        print(f"RATING COMPLETE")
        print(f"{'='*70}")
        print(f"  👍 Rated as helpful: ~{int(rated_count * 0.6)}")
        print(f"  👎 Rated as not_helpful: ~{int(rated_count * 0.4)}")
        print(f"  ⚪ Left unrated: {skipped_count}")
        print(f"  Total processed: {len(events)}")
        print(f"{'='*70}")
        print(f"\nRatings saved to Firestore!")
        print(f"Run analytics_reporting_service to see the breakdown in reports.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    
    # Configuration
    
    queries = [] #script for logging multiple queries
    
    print(f"\nCourse ID: {COURSE_ID}")
    print(f"Total queries to log: {len(queries)}")
    print(f"\nStarting batch logging...")
    print("="*70)
    
    logged_count = 0
    failed_count = 0
    
    for i, query_text in enumerate(queries, 1):
        try:
            print(f"\n[{i}/{len(queries)}] Logging: {query_text[:60]}...")
            
            # Use the log_chat_query function which handles embedding generation
            doc_id = log_chat_query(
                course_id=COURSE_ID,
                query_text=query_text,
                answer_text=None,  # Leave blank as requested
                sources=None       # Leave blank as requested
            )
            
            if doc_id:
                logged_count += 1
                print(f"  ✓ Logged successfully (doc_id: {doc_id})")
            else:
                failed_count += 1
                print(f"  ✗ Failed to log")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Error: {e}")
    
    print(f"\n{'='*70}")
    print(f"BATCH LOGGING COMPLETE")
    print(f"{'='*70}")
    print(f"  Successfully logged: {logged_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total processed: {len(queries)}")
    print(f"{'='*70}")
    print(f"\nAll queries logged to Firestore with:")
    print(f"  - course_id: {COURSE_ID}")
    print(f"  - type: chat")
    print(f"  - query_text: <each query>")
    print(f"  - query_vector: <768-dim embedding>")
    print(f"  - timestamp: <server timestamp>")
    print(f"  - answer_text: None")
    print(f"  - sources: []")
    print(f"  - rating: None")
    
    print("\nNote: Vector generation requires get_embedding() to be implemented in gemini_service")