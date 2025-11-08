"""
Master Test Runner for Canvas TA-Bot
Runs all test suites and provides a comprehensive summary.

Usage:
    python tests/run_all_tests.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import test modules
from tests.test_canvas_service import (
    test_get_course_files,
    test_get_syllabus,
    test_get_course_info
)
from tests.test_rag_service import (
    test_environment,
    test_rag_imports,
    test_suggested_questions,
    test_mock_corpus_operations
)


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "-" * 70)
    print(f"  {title}")
    print("-" * 70)


def run_environment_tests():
    """Run environment configuration tests."""
    print_section("ENVIRONMENT TESTS")
    
    results = []
    
    # Check environment setup
    results.append(("Environment Configuration", test_environment()))
    
    return results


def run_canvas_tests():
    """Run Canvas service tests."""
    print_section("CANVAS SERVICE TESTS")
    
    COURSE_ID = os.environ.get('CANVAS_TEST_COURSE_ID')
    CANVAS_TOKEN = os.environ.get('CANVAS_API_TOKEN')
    
    results = []
    
    if not COURSE_ID or not CANVAS_TOKEN:
        print("\n⚠️  Canvas credentials not configured")
        print("   Set CANVAS_TEST_COURSE_ID and CANVAS_API_TOKEN in .env")
        results.append(("Canvas: get_course_files", False))
        results.append(("Canvas: get_syllabus", False))
        results.append(("Canvas: get_course_info", False))
    else:
        results.append(("Canvas: get_course_files", test_get_course_files()))
        results.append(("Canvas: get_syllabus", test_get_syllabus()))
        results.append(("Canvas: get_course_info", test_get_course_info()))
    
    return results


def run_rag_tests():
    """Run RAG service tests."""
    print_section("RAG SERVICE TESTS")
    
    results = []
    
    # Import test
    results.append(("RAG: Service Imports", test_rag_imports()))
    
    # Question generation test (if GCP configured)
    results.append(("RAG: Question Generation", test_suggested_questions()))
    
    # Mock corpus operations
    results.append(("RAG: Corpus Operations", test_mock_corpus_operations()))
    
    return results


def print_summary(all_results):
    """Print comprehensive test summary."""
    print_header("TEST SUMMARY")
    
    # Group by category
    categories = {
        'Environment': [],
        'Canvas Service': [],
        'RAG Service': []
    }
    
    for name, passed in all_results:
        if name.startswith('Environment'):
            categories['Environment'].append((name, passed))
        elif name.startswith('Canvas'):
            categories['Canvas Service'].append((name, passed))
        elif name.startswith('RAG'):
            categories['RAG Service'].append((name, passed))
    
    # Print by category
    for category, tests in categories.items():
        if tests:
            print(f"\n{category}:")
            for name, passed in tests:
                status = "✅ PASS" if passed else "❌ FAIL"
                clean_name = name.split(': ', 1)[1] if ': ' in name else name
                print(f"  {status}  {clean_name}")
    
    # Overall stats
    total_count = len(all_results)
    passed_count = sum(1 for _, passed in all_results if passed)
    failed_count = total_count - passed_count
    
    print(f"\n{'='*70}")
    print(f"Total Tests: {total_count}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"Success Rate: {(passed_count/total_count*100):.1f}%")
    print(f"{'='*70}")
    
    return passed_count == total_count


def main():
    """Run all test suites."""
    print_header("CANVAS TA-BOT - COMPREHENSIVE TEST SUITE")
    
    all_results = []
    
    # Run environment tests
    all_results.extend(run_environment_tests())
    
    # Run Canvas service tests
    all_results.extend(run_canvas_tests())
    
    # Run RAG service tests
    all_results.extend(run_rag_tests())
    
    # Print summary
    success = print_summary(all_results)
    
    if success:
        print("\n🎉 All tests passed! Your environment is fully configured.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        print("\n📚 Helpful Resources:")
        print("   - README.md - Project setup guide")
        print("   - GCP_SETUP_GUIDE.md - Google Cloud Platform setup")
        print("   - SECURITY_GUIDE.md - Security best practices")
        print("   - check_env.py - Environment validation")
    
    print("\n" + "=" * 70 + "\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
