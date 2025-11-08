# Tests Directory

This directory contains all test suites for the Canvas TA-Bot project.

## Test Files

### `test_canvas_service.py`
Tests the Canvas LMS API integration service.

**Tests:**
- `test_get_course_files()` - Retrieves and validates course files
- `test_get_syllabus()` - Fetches syllabus content
- `test_get_course_info()` - Gets course metadata

**Requirements:**
- `CANVAS_API_TOKEN` in `.env`
- `CANVAS_TEST_COURSE_ID` in `.env`

**Run:**
```bash
python tests/test_canvas_service.py
```

### `test_rag_service.py`
Tests the Vertex AI RAG Engine integration.

**Tests:**
- `test_environment()` - Validates GCP environment setup
- `test_rag_imports()` - Checks service can be imported
- `test_suggested_questions()` - Tests AI question generation
- `test_mock_corpus_operations()` - Validates corpus setup

**Requirements:**
- `GOOGLE_CLOUD_PROJECT` in `.env`
- `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
- `service-account.json` file in project root

**Run:**
```bash
python tests/test_rag_service.py
```

### `run_all_tests.py`
Master test runner that executes all test suites.

**Run:**
```bash
python tests/run_all_tests.py
```

## Quick Start

### 1. Set Up Environment

Ensure your `.env` file is configured:
```bash
# Canvas LMS
CANVAS_API_TOKEN=your-token-here
CANVAS_TEST_COURSE_ID=12345

# Google Cloud Platform
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=service-account.json
```

### 2. Run All Tests

```bash
python tests/run_all_tests.py
```

### 3. Run Individual Test Suites

```bash
# Canvas service only
python tests/test_canvas_service.py

# RAG service only
python tests/test_rag_service.py
```

## Test Results Interpretation

### ✅ PASS
- Test executed successfully
- All assertions passed
- Service is working correctly

### ❌ FAIL
- Test encountered an error
- Check the error message for details
- May indicate configuration issues

### ⚠️ SKIP
- Test was skipped due to missing configuration
- Not necessarily a failure
- Set up required credentials to run

## Common Issues

### "Canvas credentials not configured"
**Solution:**
1. Set `CANVAS_API_TOKEN` in `.env`
2. Set `CANVAS_TEST_COURSE_ID` in `.env`
3. See Canvas API setup in README.md

### "GCP credentials file not found"
**Solution:**
1. Download `service-account.json` from GCP Console
2. Place in project root
3. Set `GOOGLE_APPLICATION_CREDENTIALS=service-account.json` in `.env`
4. See GCP_SETUP_GUIDE.md for details

### "Import failed: No module named 'app'"
**Solution:**
- Tests automatically add parent directory to Python path
- Run from project root: `python tests/test_canvas_service.py`
- Don't run from within tests/ directory

### "Permission denied" or "403 Forbidden"
**Solution:**
- Check API tokens are valid and not expired
- Verify service account has required permissions
- See troubleshooting in GCP_SETUP_GUIDE.md

## Adding New Tests

To add a new test file:

1. **Create test file**: `tests/test_new_service.py`

2. **Add path setup**:
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```

3. **Import service**:
   ```python
   from app.services.new_service import function_to_test
   ```

4. **Write tests**:
   ```python
   def test_function():
       result = function_to_test()
       assert result is not None
       return True
   ```

5. **Add to run_all_tests.py**:
   ```python
   from tests.test_new_service import test_function
   # Add to appropriate test category
   ```

## Test Coverage

### ✅ Implemented
- Canvas service (3 functions)
- RAG service (4 functions)
- Environment validation

### ⏳ Pending
- Firestore service
- Knowledge Graph service
- API Router endpoints
- Frontend integration

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: python tests/run_all_tests.py
  env:
    CANVAS_API_TOKEN: ${{ secrets.CANVAS_TOKEN }}
    GOOGLE_CLOUD_PROJECT: ${{ secrets.GCP_PROJECT }}
```

## Resources

- [Main README](../README.md) - Project setup
- [GCP Setup Guide](../GCP_SETUP_GUIDE.md) - Google Cloud setup
- [Security Guide](../SECURITY_GUIDE.md) - Credential management
- [check_env.py](../check_env.py) - Environment validation

---

**Note**: Tests require valid API credentials. Never commit credentials to the repository!
