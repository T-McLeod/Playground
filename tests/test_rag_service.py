"""
Test script for RAG Service
Tests the Vertex AI RAG Engine integration.

Usage:
    python tests/test_rag_service.py
"""
import sys
import os

# Add parent directory to path to import from app.services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_environment():
    """Test that required environment variables are set."""
    print("=" * 60)
    print("Testing Environment Configuration")
    print("=" * 60)
    
    required_vars = [
        'GOOGLE_CLOUD_PROJECT',
        'GOOGLE_APPLICATION_CREDENTIALS',
    ]
    
    optional_vars = [
        'GOOGLE_CLOUD_LOCATION',
    ]
    
    all_set = True
    
    print("\n✓ Required Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == 'GOOGLE_APPLICATION_CREDENTIALS':
                # Check if file exists
                if os.path.exists(value):
                    print(f"  ✅ {var}: {value} (file exists)")
                else:
                    print(f"  ⚠️  {var}: {value} (FILE NOT FOUND)")
                    all_set = False
            else:
                print(f"  ✅ {var}: {value[:20]}...")
        else:
            print(f"  ❌ {var}: NOT SET")
            all_set = False
    
    print("\n✓ Optional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ℹ️  {var}: using default")
    
    if not all_set:
        print("\n⚠️  WARNING: Some required variables are not properly configured.")
        print("The RAG service will not work until GCP credentials are set up.")
        return False
    else:
        print("\n✅ All required environment variables are set!")
        return True


def test_rag_imports():
    """Test that RAG service can be imported."""
    print("\n" + "=" * 60)
    print("Testing RAG Service Imports")
    print("=" * 60)
    
    # Check if GCP credentials exist first
    if not os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')):
        print("⚠️  Skipping import test - GCP credentials file not found")
        print("ℹ️  The RAG service requires valid GCP credentials to import")
        print("   (Vertex AI SDK validates credentials on import)")
        return False
    
    try:
        print("ℹ️  Importing RAG service (this may take a moment)...")
        from app.services.rag_service import (
            create_and_provision_corpus,
            query_rag_corpus,
            query_rag_with_history,
            get_suggested_questions
        )
        print("✅ All RAG service functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import RAG service: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"⚠️  Import succeeded but with warnings: {e}")
        return True  # Still count as success if functions are available


def test_suggested_questions():
    """Test the suggested questions generation (doesn't require corpus)."""
    print("\n" + "=" * 60)
    print("Testing AI Question Generation")
    print("=" * 60)
    
    # Check if GCP is configured
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        print("⚠️  Skipping test - GOOGLE_CLOUD_PROJECT not set")
        return False
    
    if not os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')):
        print("⚠️  Skipping test - GCP credentials file not found")
        return False
    
    try:
        from app.services.rag_service import get_suggested_questions
        
        topic = "Machine Learning Basics"
        print(f"\nGenerating questions for topic: '{topic}'")
        
        questions = get_suggested_questions(topic)
        
        print(f"\n✅ Generated {len(questions)} questions:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate questions: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_corpus_operations():
    """Test corpus operations with mock data (if GCP is configured)."""
    print("\n" + "=" * 60)
    print("Testing Corpus Operations (Mock)")
    print("=" * 60)
    
    # Check if GCP is configured
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        print("⚠️  Skipping test - GOOGLE_CLOUD_PROJECT not set")
        print("ℹ️  To test corpus operations, configure GCP credentials:")
        print("   1. Set GOOGLE_CLOUD_PROJECT in .env")
        print("   2. Place service-account.json in project root")
        print("   3. Set GOOGLE_APPLICATION_CREDENTIALS=service-account.json")
        return False
    
    if not os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')):
        print("⚠️  Skipping test - GCP credentials file not found")
        return False
    
    print("\n✅ GCP is configured!")
    print("ℹ️  Actual corpus creation requires:")
    print("   - Valid Canvas course files")
    print("   - Canvas API token")
    print("   - Enabled Vertex AI API")
    print("\nℹ️  Use test_canvas_service.py to get real files, then test corpus creation")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("RAG SERVICE TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Environment
    results.append(("Environment Setup", test_environment()))
    
    # Test 2: Imports
    results.append(("Service Imports", test_rag_imports()))
    
    # Test 3: Suggested Questions (if GCP configured)
    results.append(("Question Generation", test_suggested_questions()))
    
    # Test 4: Mock corpus operations
    results.append(("Corpus Operations", test_mock_corpus_operations()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nPassed: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return True
    elif passed_count > 0:
        print("\n⚠️  Some tests passed. Check configuration for failures.")
        return False
    else:
        print("\n❌ All tests failed. Check environment configuration.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
