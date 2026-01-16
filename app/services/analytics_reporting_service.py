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
from datetime import datetime, timezone
from typing import List
import sys
import os
from sklearn.cluster import MiniBatchKMeans
import numpy as np

from .llm_services import get_llm_service

# Handle imports for both module use and standalone testing
if __name__ == "__main__":
    # Running as standalone script
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from app.services import firestore_service
else:
    # Imported as a module
    from . import firestore_service

logger = logging.getLogger(__name__)

llm_service = get_llm_service() 

# ============================================================================
# MAIN ANALYTICS PIPELINE
# ============================================================================

def determine_optimal_clusters(vectors, max_clusters: int = 10) -> int:
    """
    Uses the elbow method to determine the optimal number of clusters.
    
    The elbow method calculates inertia (sum of squared distances to cluster centers)
    for different values of k and finds the "elbow point" where adding more clusters
    provides diminishing returns.
    
    Args:
        vectors: Numpy array of vectors
        max_clusters: Maximum number of clusters to test (default: 10)
        
    Returns:
        Optimal number of clusters
        
    Example:
        optimal_k = determine_optimal_clusters(vectors, max_clusters=10)
        # Returns: 5 (if that's the elbow point)
    """
    try:
        
        n_samples = len(vectors)
        
        # Can't have more clusters than samples
        max_k = min(max_clusters, n_samples - 1)
        
        # Need at least 2 clusters for elbow method
        if max_k < 2:
            logger.warning(f"Not enough samples ({n_samples}) for elbow method, using k=1")
            return 1
        
        logger.info(f"Running elbow method to determine optimal clusters (testing k=1 to k={max_k})")
        
        inertias = []
        k_values = range(1, max_k + 1)
        
        # Calculate inertia for each k
        for k in k_values:
            kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=100)
            kmeans.fit(vectors)
            inertias.append(kmeans.inertia_)
            logger.info(f"  k={k}: inertia={kmeans.inertia_:.2f}")
        
        # Find the elbow point using the "elbow" heuristic
        # Calculate the rate of change in inertia
        if len(inertias) < 3:
            optimal_k = len(inertias)
        else:
            # Calculate second derivative (rate of change of rate of change)
            # The elbow is where the second derivative is maximized
            inertias_array = np.array(inertias)
            
            # Normalize inertias to 0-1 scale for better comparison
            inertias_normalized = (inertias_array - inertias_array.min()) / (inertias_array.max() - inertias_array.min() + 1e-10)
            
            # Calculate rate of decrease
            differences = np.diff(inertias_normalized)
            
            # Calculate second derivative (change in rate of decrease)
            second_diff = np.diff(differences)
            
            # The elbow is where the second derivative is largest (most positive)
            # This indicates the point where adding clusters stops being as beneficial
            elbow_index = min(np.argmax(second_diff) + 2, len(k_values) - 1)  # +2 because we lost 2 elements in diff operations
            
            optimal_k = k_values[elbow_index]
        
        logger.info(f"Elbow method suggests optimal k={optimal_k}")
        
        return optimal_k
        
    except Exception as e:
        logger.error(f"Failed to determine optimal clusters: {e}", exc_info=True)
        # Fallback to a reasonable default
        return min(5, len(vectors) // 10)  # Use 5 or 10% of samples, whichever is smaller


def run_daily_analytics(playground_id: str, n_clusters: int = None, auto_detect_clusters: bool = True) -> dict:
    """
    Runs the complete analytics pipeline for a playground.
    
    This is the main analytics function that:
    1. Fetches all chat query vectors from Firestore
    2. Determines optimal number of clusters (if auto_detect_clusters=True)
    3. Clusters them using MiniBatchKMeans
    4. Labels each cluster using AI
    5. Generates a comprehensive report
    6. Saves the report to Firestore
    
    This should be run periodically (e.g., daily) or on-demand by professors.
    
    Args:
        playground_id: The playground document ID
        n_clusters: Number of clusters to create (optional if auto_detect_clusters=True)
        auto_detect_clusters: Use elbow method to automatically determine optimal k (default: True)
        
    Returns:
        Dictionary containing the analytics report
        
    Example:
        # Auto-detect optimal clusters
        report = run_daily_analytics("abc123")
        
        # Or specify exact number
        report = run_daily_analytics("abc123", n_clusters=5, auto_detect_clusters=False)
        
        # Returns: {
        #     'clusters': {
        #         'Getting Started Questions': 15,
        #         'Advanced Concepts': 8,
        #         ...
        #     },
        #     'total_queries': 50,
        #     'optimal_clusters': 5,
        #     'generated_at': '2025-11-08T10:30:00Z'
        # }
    """
    try:
        logger.info(f"Starting daily analytics for playground {playground_id}")
        
        # Step 1: Fetch all chat events
        logger.info("Fetching analytics events...")
        events = firestore_service.get_analytics_events(playground_id, event_type='chat')
        
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
        
        # Step 2.5: Determine optimal number of clusters if needed
        if auto_detect_clusters:
            logger.info("Auto-detecting optimal number of clusters using elbow method...")
            n_clusters = determine_optimal_clusters(vectors, max_clusters=15)
        elif n_clusters is None:
            # Default to 5 if not specified and auto-detect is off
            n_clusters = 5
            logger.info(f"Using default n_clusters={n_clusters}")
        
        # Step 3: Cluster the vectors
        logger.info(f"Clustering into {n_clusters} groups...")
        cluster_labels, cluster_centers = _perform_clustering(vectors, n_clusters)
        
        # Step 4: Group doc IDs by cluster and label each cluster
        logger.info("Labeling clusters...")
        clusters = {}
        
        import numpy as np
        
        for cluster_id in range(n_clusters):
            # Get all indices for this cluster
            cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
            
            if not cluster_indices:
                continue
            
            # Get the centroid for this cluster
            centroid = cluster_centers[cluster_id]
            
            # Calculate distances from centroid for all vectors in this cluster
            cluster_vectors = vectors[cluster_indices]
            distances = np.linalg.norm(cluster_vectors - centroid, axis=1)
            
            # Sort indices by distance (closest to centroid first)
            sorted_cluster_indices = [cluster_indices[i] for i in np.argsort(distances)]
            
            # Get doc IDs in sorted order (closest to centroid first)
            cluster_doc_ids = [doc_ids[i] for i in sorted_cluster_indices]
            
            # Get ALL events for this cluster (already sorted by distance to centroid)
            all_cluster_events = firestore_service.get_analytics_events_by_ids(cluster_doc_ids)
            
            # Count ratings
            good_count = sum(1 for event in all_cluster_events if event.get('rating') == 'helpful')
            bad_count = sum(1 for event in all_cluster_events if event.get('rating') == 'not_helpful')
            none_count = sum(1 for event in all_cluster_events if not event.get('rating'))
            
            # Get top 10 for labeling (already sorted by distance to centroid)
            cluster_events = all_cluster_events[:10]
            
            # Extract query texts (most representative queries first)
            query_texts = [event.get('query_text', '') for event in cluster_events if event.get('query_text')]
            
            # Generate AI label for this cluster
            cluster_label = _label_cluster(query_texts)
            
            # Store cluster info with ratings
            clusters[cluster_label] = {
                'count': len(cluster_doc_ids),
                'sample_queries': query_texts[:3],  # Include 3 most representative queries
                'ratings': {
                    'good': good_count,
                    'bad': bad_count,
                    'none': none_count
                }
            }
            
            logger.info(f"Cluster '{cluster_label}': {len(cluster_doc_ids)} queries (👍 {good_count}, 👎 {bad_count}, ⚪ {none_count})")
        
        # Step 5: Generate comprehensive report
        report = {
            'status': 'complete',
            'playground_id': playground_id,
            'total_queries': len(events),
            'num_clusters': len(clusters),
            'optimal_clusters': n_clusters,  # Include the k value used
            'auto_detected': auto_detect_clusters,  # Flag whether it was auto-detected
            'clusters': clusters,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Step 6: Save report to Firestore
        logger.info("Saving analytics report...")
        firestore_service.save_analytics_report(playground_id, report)
        
        logger.info(f"Daily analytics completed for playground {playground_id}")
        return report
        
    except Exception as e:
        logger.error(f"Failed to run daily analytics: {e}", exc_info=True)
        raise


# ============================================================================
# REPORT RETRIEVAL
# ============================================================================

def get_analytics_report(playground_id: str) -> dict:
    """
    Retrieves the latest analytics report for a playground.
    
    This is a simple passthrough to the firestore_service.
    Called by the API when professors view their dashboard.
    
    Args:
        playground_id: The playground document ID
        
    Returns:
        Dictionary containing the analytics report
    """
    logger.info(f"Retrieving analytics report for playground {playground_id}")
    return firestore_service.get_analytics_report(playground_id)


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
    import numpy as np
    
    # Filter events that have vectors
    events_with_vectors = [e for e in events if e.get('query_vector')]
    
    if not events_with_vectors:
        logger.warning("No events with vectors found")
        return np.array([]), []
    
    # Extract vectors and doc_ids
    vectors = np.array([e['query_vector'] for e in events_with_vectors])
    doc_ids = [e['doc_id'] for e in events_with_vectors]
    
    logger.info(f"Extracted {len(vectors)} vectors with {vectors.shape[1] if len(vectors) > 0 else 0} dimensions")
    
    return vectors, doc_ids


def _perform_clustering(vectors, n_clusters: int = 5):
    """
    Helper function to perform MiniBatchKMeans clustering.
    
    Args:
        vectors: Numpy array of vectors
        n_clusters: Number of clusters to create
        
    Returns:
        Tuple of (cluster_labels, cluster_centers)
        - cluster_labels: Array of cluster assignments for each vector
        - cluster_centers: Array of cluster centroid vectors
    """
    try:
        logger.info(f"Performing MiniBatchKMeans clustering with {n_clusters} clusters")
        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100)
        labels = kmeans.fit_predict(vectors)
        
        logger.info(f"Clustering complete. Cluster distribution: {dict(zip(*[range(n_clusters), [sum(labels == i) for i in range(n_clusters)]]))}") 
        
        return labels, kmeans.cluster_centers_
        
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
        
        label = llm_service.generate_text(prompt)
        
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
    Test the analytics reporting functions with real data.
    """
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("="*70)
    print("ANALYTICS REPORTING SERVICE TEST")
    print("="*70)
    
    # Use the actual course ID with 50 queries we just logged
    TEST_COURSE_ID = "13299557"
    
    print(f"\nCourse ID: {TEST_COURSE_ID}")
    
    # Test 1: Run analytics with real data
    print("\n" + "="*70)
    print("Test 1: Running daily analytics on real data")
    print("="*70)
    
    try:
        # Run analytics with auto-detection (elbow method)
        print("\nUsing elbow method to auto-detect optimal clusters...")
        report = run_daily_analytics(TEST_COURSE_ID, auto_detect_clusters=True)
        
        print(f"\n✓ Analytics completed!")
        print(f"\n{'='*70}")
        print(f"ANALYTICS REPORT SUMMARY")
        print(f"{'='*70}")
        print(f"Status: {report.get('status')}")
        print(f"Total Queries: {report.get('total_queries')}")
        print(f"Optimal Clusters (auto-detected): {report.get('optimal_clusters')}")
        print(f"Auto-detected: {report.get('auto_detected')}")
        print(f"Generated At: {report.get('generated_at')}")
        
        if report.get('status') == 'complete':
            print(f"Number of Clusters: {report.get('num_clusters')}")
            print(f"\n{'='*70}")
            print(f"CLUSTER BREAKDOWN")
            print(f"{'='*70}")
            
            clusters = report.get('clusters', {})
            
            # Sort clusters by count (descending)
            sorted_clusters = sorted(clusters.items(), key=lambda x: x[1]['count'], reverse=True)
            
            for i, (label, info) in enumerate(sorted_clusters, 1):
                print(f"\nCluster {i}: {label}")
                print(f"  Count: {info['count']} queries")
                print(f"  Sample queries:")
                for j, query in enumerate(info.get('sample_queries', []), 1):
                    # Truncate long queries for display
                    display_query = query[:80] + "..." if len(query) > 80 else query
                    print(f"    {j}. {display_query}")
        else:
            print(f"\n⚠ Status: {report.get('status')}")
            print(f"Message: {report.get('message', 'No message')}")
            
    except Exception as e:
        print(f"\n✗ Failed to run analytics: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Retrieve the saved report
    print("\n" + "="*70)
    print("Test 2: Retrieving saved analytics report")
    print("="*70)
    
    try:
        report = get_analytics_report(TEST_COURSE_ID)
        if report:
            print(f"✓ Report retrieved successfully")
            print(f"  Status: {report.get('status')}")
            print(f"  Generated at: {report.get('generated_at')}")
            if report.get('clusters'):
                print(f"  Clusters: {len(report.get('clusters'))}")
                print(f"  Total queries: {report.get('total_queries')}")
        else:
            print("⚠ No report found in Firestore")
    except Exception as e:
        print(f"✗ Failed to retrieve report: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("✓ Analytics reporting service test complete!")
    print("="*70)
    print("\nThe report has been:")
    print("  1. Generated with clustering and AI labeling")
    print("  2. Saved to Firestore (analytics_reports collection)")
    print("  3. Ready to be retrieved via API")
    print("="*70)
