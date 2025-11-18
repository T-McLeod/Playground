"""
Command to randomly rate queries in the database based on specified percentages.

Usage:
    python -m app.commands.rate_queries --course-id 12345 --helpful 70 --not-helpful 20 --none 10

This will randomly assign ratings to queries in the database:
    - 70% rated as "helpful"
    - 20% rated as "not_helpful"
    - 10% with no rating

Percentages must add up to 100.
"""
import argparse
import random
import logging
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.firestore_service import get_analytics_events, rate_analytics_event

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def rate_queries(course_id, helpful_percent=5, not_helpful_percent=15, none_percent=80, dry_run=False):
    """
    Randomly rate queries in the database based on specified percentages.
    
    Args:
        course_id: Canvas course ID
        helpful_percent: Percentage of queries to rate as "helpful"
        not_helpful_percent: Percentage of queries to rate as "not_helpful"
        none_percent: Percentage of queries to leave with no rating
        dry_run: If True, don't actually update the database
    
    Returns:
        dict: Summary of ratings applied
    """
    # Validate percentages
    total_percent = helpful_percent + not_helpful_percent + none_percent
    if total_percent != 100:
        raise ValueError(f"Percentages must add up to 100, got {total_percent}")
    
    # Get all chat events (queries) for this course using firestore_service
    logger.info(f"Fetching queries for course {course_id}...")
    all_queries = get_analytics_events(course_id, event_type='chat')
    
    total_queries = len(all_queries)
    
    if total_queries == 0:
        logger.warning(f"No queries found for course {course_id}")
        return {
            "course_id": course_id,
            "total_queries": 0,
            "helpful": 0,
            "not_helpful": 0,
            "none": 0
        }
    
    logger.info(f"Found {total_queries} queries")
    
    # Shuffle queries randomly
    random.shuffle(all_queries)
    
    # Calculate counts for each rating
    helpful_count = int(total_queries * helpful_percent / 100)
    not_helpful_count = int(total_queries * not_helpful_percent / 100)
    none_count = total_queries - helpful_count - not_helpful_count  # Remaining queries get no rating
    
    logger.info(f"Distribution: {helpful_count} helpful, {not_helpful_count} not_helpful, {none_count} none")
    
    # Assign ratings
    ratings_assigned = {
        "helpful": 0,
        "not_helpful": 0,
        "none": 0
    }
    
    index = 0
    
    # Assign "helpful" ratings
    for i in range(helpful_count):
        query = all_queries[index]
        doc_id = query['doc_id']
        if not dry_run:
            rate_analytics_event(doc_id, 'helpful')
        ratings_assigned["helpful"] += 1
        index += 1
        
        if (i + 1) % 50 == 0:
            logger.info(f"Assigned {i + 1}/{helpful_count} helpful ratings...")
    
    # Assign "not_helpful" ratings
    for i in range(not_helpful_count):
        query = all_queries[index]
        doc_id = query['doc_id']
        if not dry_run:
            rate_analytics_event(doc_id, 'not_helpful')
        ratings_assigned["not_helpful"] += 1
        index += 1
        
        if (i + 1) % 50 == 0:
            logger.info(f"Assigned {i + 1}/{not_helpful_count} not_helpful ratings...")
    
    # Assign "none" (don't add any rating field)
    for i in range(none_count):
        query = all_queries[index]
        doc_id = query['doc_id']
        if not dry_run:
            rate_analytics_event(doc_id, None)  # This will remove the rating field
        ratings_assigned["none"] += 1
        index += 1
        
        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i + 1}/{none_count} unrated queries...")
    
    return {
        "course_id": course_id,
        "total_queries": total_queries,
        "helpful": ratings_assigned["helpful"],
        "not_helpful": ratings_assigned["not_helpful"],
        "none": ratings_assigned["none"]
    }


def main():
    parser = argparse.ArgumentParser(
        description='Randomly rate queries in the database based on specified percentages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--course-id',
        required=True,
        help='Canvas course ID'
    )
    
    parser.add_argument(
        '--helpful',
        type=float,
        default=7.5,
        help='Percentage of queries to rate as "helpful" - default: 7.5'
    )
    
    parser.add_argument(
        '--not-helpful',
        type=float,
        default=17.5,
        help='Percentage of queries to rate as "not_helpful" - default: 17.5'
    )
    
    parser.add_argument(
        '--none',
        type=float,
        default=75.0,
        help='Percentage of queries to leave with no rating - default: 75.0'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate the rating process without actually updating the database'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducible results (optional)'
    )
    
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)
        logger.info(f"Using random seed: {args.seed}")
    
    try:
        # Validate percentages
        total = args.helpful + args.not_helpful + args.none
        if abs(total - 100.0) > 0.01:  # Allow small floating point errors
            logger.error(f"Percentages must add up to 100, got {total}")
            return 1
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No database changes will be made")
        
        # Rate queries
        results = rate_queries(
            course_id=args.course_id,
            helpful_percent=args.helpful,
            not_helpful_percent=args.not_helpful,
            none_percent=args.none,
            dry_run=args.dry_run
        )
        
        # Print summary
        print("\n" + "="*60)
        print("RATING SUMMARY")
        print("="*60)
        print(f"Course ID:        {results['course_id']}")
        print(f"Total Queries:    {results['total_queries']}")
        if results['total_queries'] > 0:
            print(f"Helpful:          {results['helpful']} ({results['helpful']/results['total_queries']*100:.1f}%)")
            print(f"Not Helpful:      {results['not_helpful']} ({results['not_helpful']/results['total_queries']*100:.1f}%)")
            print(f"No Rating:        {results['none']} ({results['none']/results['total_queries']*100:.1f}%)")
        else:
            print("Helpful:          0")
            print("Not Helpful:      0")
            print("No Rating:        0")
        
        if args.dry_run:
            print("\nNOTE: This was a dry run. No changes were made to the database.")
        else:
            print("\nRatings have been successfully applied to the database.")
        
        print("="*60)
        
        return 0
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
