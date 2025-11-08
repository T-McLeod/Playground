"""
Analytics Reporting Service
Handles batch analytics processing and report generation.

This service is responsible for:
- Fetching analytics data (vectors) from Firestore
- Clustering student queries using MiniBatchKMeans
- Labeling clusters using AI
- Generating comprehensive reports for professors
- Saving reports to Firestore

This is a compute-intensive service that runs periodically (e.g., daily)
or on-demand when professors request analytics.

Dependencies:
- firestore_service: For reading vectors and saving reports
- gemini_service: For AI-powered cluster labeling
"""
import logging
from datetime import datetime
from typing import List, Dict
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
# MAIN ANALYTICS PIPELINE
# ============================================================================

def run_daily_analytics(course_id: str, n_clusters: int = 5) -> dict:
    """
    Runs the complete analytics pipeline for a course.
    
    This is the main analytics function that:
    1. Fetches all chat query vectors from Firestore
    2. Clusters them using MiniBatchKMeans
    3. Labels each cluster using AI
    4. Generates a comprehensive report
    5. Saves the report to Firestore
    
    This should be run periodically (e.g., daily) or on-demand by professors.
    
    Args:
        course_id: The Canvas course ID
        n_clusters: Number of clusters to create (default: 5)
        
    Returns:
        Dictionary containing the analytics report
        
    Example:
        report = run_daily_analytics("12345")
        # Returns: {
        #     'clusters': {
        #         'Getting Started Questions': 15,
        #         'Advanced Concepts': 8,
        #         ...
        #     },
        #     'total_queries': 50,
        #     'generated_at': '2025-11-08T10:30:00Z'
        # }
    """
    try:
        logger.info(f"Starting daily analytics for course {course_id}")
        
        # Step 1: Fetch all chat events
        logger.info("Fetching analytics events...")
        events = firestore_service.get_analytics_events(course_id, event_type='chat')
        
        if not events or len(events) < 5:
            logger.warning(f"Not enough data for clustering (found {len(events)} queries)")
            return {
                'status': 'insufficient_data',
                'total_queries': len(events) if events else 0,
                'message': 'Need at least 5 queries to generate analytics'
            }
        
        logger.info(f"Retrieved {len(events)} chat events for analysis")
        
        # Step 2: Extract vectors and doc IDs
        logger.info("Extracting vectors for clustering...")
        vectors, doc_ids = _extract_vectors(events)
        
        # Step 3: Cluster the vectors
        logger.info(f"Clustering into {n_clusters} groups...")
        cluster_labels = _perform_clustering(vectors, n_clusters)
        
        # Step 4: Group doc IDs by cluster and label each cluster
        logger.info("Labeling clusters...")
        clusters = {}
        
        for cluster_id in range(n_clusters):
            # Get all doc IDs for this cluster
            cluster_doc_ids = [doc_ids[i] for i, label in enumerate(cluster_labels) if label == cluster_id]
            
            if not cluster_doc_ids:
                continue
            
            # Get events for this cluster
            cluster_events = firestore_service.get_analytics_events_by_ids(cluster_doc_ids[:10])  # Use top 10
            
            # Extract query texts
            query_texts = [event.get('query_text', '') for event in cluster_events if event.get('query_text')]
            
            # Generate AI label for this cluster
            cluster_label = _label_cluster(query_texts)
            
            # Store cluster info
            clusters[cluster_label] = {
                'count': len(cluster_doc_ids),
                'sample_queries': query_texts[:3]  # Include 3 sample queries
            }
            
            logger.info(f"Cluster '{cluster_label}': {len(cluster_doc_ids)} queries")
        
        # Step 5: Generate comprehensive report
        report = {
            'status': 'complete',
            'course_id': course_id,
            'total_queries': len(events),
            'num_clusters': len(clusters),
            'clusters': clusters,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Step 6: Save report to Firestore
        logger.info("Saving analytics report...")
        firestore_service.save_analytics_report(course_id, report)
        
        logger.info(f"Daily analytics completed for course {course_id}")
        return report
        
    except Exception as e:
        logger.error(f"Failed to run daily analytics: {e}", exc_info=True)
        raise


# ============================================================================
# REPORT RETRIEVAL
# ============================================================================

def get_analytics_report(course_id: str) -> dict:
    """
    Retrieves the latest analytics report for a course.
    
    This is a simple passthrough to the firestore_service.
    Called by the API when professors view their dashboard.
    
    Args:
        course_id: The Canvas course ID
        
    Returns:
        Dictionary containing the analytics report
    """
    logger.info(f"Retrieving analytics report for course {course_id}")
    return firestore_service.get_analytics_report(course_id)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _extract_vectors(events: List[dict]) -> tuple:
    """
    Helper function to extract vectors and doc_ids from event data.
    This is where the analytics service parses what it needs from Firestore data.
    
    Args:
        events: List of event dicts from Firestore (with 'doc_id' and 'query_vector' keys)
        
    Returns:
        Tuple of (vectors_array, doc_ids_list)
    """
    # TODO: Implement when embeddings are ready
    # import numpy as np
    # 
    # # Filter events that have vectors
    # events_with_vectors = [e for e in events if e.get('query_vector')]
    # 
    # vectors = np.array([e['query_vector'] for e in events_with_vectors])
    # doc_ids = [e['doc_id'] for e in events_with_vectors]
    # 
    # return vectors, doc_ids
    
    # Placeholder until embeddings are implemented
    logger.warning("Embeddings not yet implemented - using placeholder")
    import numpy as np
    
    # Generate random vectors for testing
    doc_ids = [event['doc_id'] for event in events]
    vectors = np.random.rand(len(doc_ids), 768)  # 768-dim vectors (text-embedding-004 size)
    
    return vectors, doc_ids


def _perform_clustering(vectors, n_clusters: int = 5):
    """
    Helper function to perform MiniBatchKMeans clustering.
    
    Args:
        vectors: Numpy array of vectors
        n_clusters: Number of clusters to create
        
    Returns:
        Cluster labels array
    """
    # TODO: Install sklearn: pip install scikit-learn
    try:
        from sklearn.cluster import MiniBatchKMeans
        
        logger.info(f"Performing MiniBatchKMeans clustering with {n_clusters} clusters")
        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100)
        labels = kmeans.fit_predict(vectors)
        
        logger.info(f"Clustering complete. Cluster distribution: {dict(zip(*[range(n_clusters), [sum(labels == i) for i in range(n_clusters)]]))}") 
        
        return labels
        
    except ImportError:
        logger.error("scikit-learn not installed. Please run: pip install scikit-learn")
        raise


def _label_cluster(query_texts: List[str]) -> str:
    """
    Helper function to generate AI label for a cluster.
    
    Args:
        query_texts: List of representative queries from this cluster
        
    Returns:
        Human-readable label for the cluster
    """
    if not query_texts:
        return "Miscellaneous Questions"
    
    # TODO: Use Gemini to generate better labels
    # For now, create a simple descriptive label
    try:
        # Combine sample queries
        samples = "\n".join([f"- {q}" for q in query_texts[:5]])
        
        prompt = (
            f"Given these student questions from a course:\n{samples}\n\n"
            f"Generate a short category label (2-4 words) that describes the common theme or topic. "
            f"Be specific and use technical terms when appropriate. "
            f"Only return the category label, nothing else."
        )
        
        label = gemini_service.generate_answer(prompt)
        
        # Clean up the label (remove quotes, extra whitespace)
        label = label.strip().strip('"').strip("'").strip()
        
        logger.info(f"Generated cluster label: {label}")
        return label
        
    except Exception as e:
        logger.error(f"Failed to generate AI label: {e}")
        # Fallback: use first few words of first query
        fallback = query_texts[0][:50]
        return f"Questions about {fallback}..."


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test the analytics reporting functions.
    """
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("="*70)
    print("ANALYTICS REPORTING SERVICE TEST")
    print("="*70)
    
    TEST_COURSE_ID = "test_course_123"
    
    print(f"\nTest Course ID: {TEST_COURSE_ID}")
    
    # Test 1: Run analytics
    print("\n" + "="*70)
    print("Test 1: Running daily analytics")
    print("="*70)
    
    try:
        report = run_daily_analytics(TEST_COURSE_ID, n_clusters=3)
        print(f"✓ Analytics completed")
        print(f"  Status: {report.get('status')}")
        print(f"  Total Queries: {report.get('total_queries')}")
        
        if report.get('status') == 'complete':
            print(f"  Number of Clusters: {report.get('num_clusters')}")
            print(f"\n  Cluster Breakdown:")
            for label, info in report.get('clusters', {}).items():
                print(f"    - {label}: {info['count']} queries")
    except Exception as e:
        print(f"✗ Failed to run analytics: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Get report
    print("\n" + "="*70)
    print("Test 2: Retrieving analytics report")
    print("="*70)
    
    try:
        report = get_analytics_report(TEST_COURSE_ID)
        if report:
            print(f"✓ Report retrieved")
            print(f"  Status: {report.get('status')}")
            print(f"  Generated at: {report.get('generated_at')}")
            if report.get('clusters'):
                print(f"  Clusters found: {len(report.get('clusters'))}")
        else:
            print("⚠ No report found")
    except Exception as e:
        print(f"✗ Failed to retrieve report: {e}")
    
    print("\n" + "="*70)
    print("✓ Analytics reporting service ready!")
    print("\nNote: Currently using placeholder vectors.")
    print("Next step: Implement embeddings in gemini_service")
    print("="*70)
