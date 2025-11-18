"""
Command to run a batch of queries against the /api/chat endpoint.

Usage:
    python -m app.commands.run_queries --course-id 12345 --input queries.json --output results.json

Input JSON format:
    {
        "questions": [
            "What is machine learning?",
            "How does gradient descent work?",
            "What is a neural network?"
        ]
    }

Output JSON format:
    {
        "course_id": "12345",
        "total_queries": 3,
        "successful": 2,
        "failed": 1,
        "results": [
            {
                "query": "What is machine learning?",
                "answer": "...",
                "sources": [...],
                "log_doc_id": "...",
                "status": "success"
            },
            {
                "query": "How does gradient descent work?",
                "answer": null,
                "error": "...",
                "status": "failed"
            }
        ]
    }
"""
import argparse
import json
import requests
import time
import logging
import urllib3
from pathlib import Path

# Disable SSL warnings for localhost testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_queries(input_file):
    """Load queries from a JSON file."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support multiple formats
        if isinstance(data, list):
            # Simple list of questions
            return data
        elif isinstance(data, dict):
            # Object with 'questions' or 'queries' key
            return data.get('questions') or data.get('queries') or []
        else:
            raise ValueError("Invalid JSON format. Expected list or object with 'questions' key.")
    
    except Exception as e:
        logger.error(f"Failed to load queries from {input_file}: {e}")
        raise


def run_query(base_url, course_id, query_text, timeout=30):
    """
    Send a single query to the /api/chat endpoint.
    
    Args:
        base_url: Base URL of the application (e.g., https://localhost:5000)
        course_id: Canvas course ID
        query_text: The question to ask
        timeout: Request timeout in seconds
    
    Returns:
        dict: Response data or error information
    """
    endpoint = f"{base_url}/api/chat"
    
    payload = {
        "course_id": course_id,
        "query": query_text
    }
    
    try:
        logger.info(f"Sending query: {query_text[:50]}...")
        
        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
            headers={'Content-Type': 'application/json'},
            verify=False  # Disable SSL verification for localhost
        )
        
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "query": query_text,
            "answer": data.get("answer") or data.get("response"),
            "sources": data.get("sources", []),
            "log_doc_id": data.get("log_doc_id"),
            "status": "success"
        }
    
    except requests.exceptions.Timeout:
        logger.error(f"Query timed out after {timeout}s")
        return {
            "query": query_text,
            "answer": None,
            "error": f"Request timed out after {timeout} seconds",
            "status": "failed"
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {
            "query": query_text,
            "answer": None,
            "error": str(e),
            "status": "failed"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "query": query_text,
            "answer": None,
            "error": str(e),
            "status": "failed"
        }


def run_batch_queries(base_url, course_id, queries, delay=1.0, timeout=30):
    """
    Run a batch of queries against the /api/chat endpoint.
    
    Args:
        base_url: Base URL of the application
        course_id: Canvas course ID
        queries: List of query strings
        delay: Delay in seconds between queries (to avoid rate limiting)
        timeout: Request timeout in seconds
    
    Returns:
        dict: Summary of results
    """
    results = []
    successful = 0
    failed = 0
    
    total = len(queries)
    logger.info(f"Starting batch run of {total} queries for course {course_id}")
    
    for i, query_text in enumerate(queries, 1):
        logger.info(f"Query {i}/{total}")
        
        result = run_query(base_url, course_id, query_text, timeout)
        results.append(result)
        
        if result["status"] == "success":
            successful += 1
            logger.info(f"✓ Success")
        else:
            failed += 1
            logger.warning(f"✗ Failed: {result.get('error')}")
        
        # Add delay between requests (except for the last one)
        if i < total:
            time.sleep(delay)
    
    return {
        "course_id": course_id,
        "total_queries": total,
        "successful": successful,
        "failed": failed,
        "results": results
    }


def save_results(output_file, results):
    """Save results to a JSON file."""
    try:
        # Create parent directories if they don't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_file}")
    
    except Exception as e:
        logger.error(f"Failed to save results to {output_file}: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Run batch queries against the /api/chat endpoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--course-id',
        required=True,
        help='Canvas course ID'
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input JSON file containing queries'
    )
    
    parser.add_argument(
        '--output',
        default='query_results.json',
        help='Path to output JSON file for results (default: query_results.json)'
    )
    
    parser.add_argument(
        '--base-url',
        default='https://localhost:5000',
        help='Base URL of the application (default: https://localhost:5000)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay in seconds between queries (default: 1.0)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load queries
        queries = load_queries(args.input)
        
        if not queries:
            logger.error("No queries found in input file")
            return 1
        
        logger.info(f"Loaded {len(queries)} queries from {args.input}")
        
        # Run batch queries
        results = run_batch_queries(
            base_url=args.base_url,
            course_id=args.course_id,
            queries=queries,
            delay=args.delay,
            timeout=args.timeout
        )
        
        # Save results
        save_results(args.output, results)
        
        # Print summary
        print("\n" + "="*60)
        print("BATCH QUERY SUMMARY")
        print("="*60)
        print(f"Course ID:        {results['course_id']}")
        print(f"Total Queries:    {results['total_queries']}")
        print(f"Successful:       {results['successful']}")
        print(f"Failed:           {results['failed']}")
        print(f"Success Rate:     {results['successful']/results['total_queries']*100:.1f}%")
        print(f"Results saved to: {args.output}")
        print("="*60)
        
        return 0
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
