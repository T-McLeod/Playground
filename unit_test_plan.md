# Unit Test Plan

This document provides a detailed technical summary of the Canvas TA-Bot application and a comprehensive plan for implementing a robust unit testing suite.

## 1. Technical Summary

The Canvas TA-Bot is a Python-based Flask application designed to act as an AI-powered teaching assistant within the Canvas LMS. It leverages several Google Cloud services to provide its functionality.

### Application Workflow

1.  **LTI Launch**: The application is initiated from within a Canvas course via an LTI (Learning Tools Interoperability) launch. The launch request contains information about the course ID, the user's ID, and their role (e.g., student, instructor). Based on the course's status in Firestore and the user's role, the application directs them to the appropriate view (e.g., course initialization for professors, student view, or analytics dashboard).

2.  **Course Initialization**: This is a professor-only feature. The process is as follows:
    *   The professor initiates the process from the frontend.
    *   `routes.py` receives the request and calls the `initialize_course` function.
    *   The `canvas_service` fetches all the files from the Canvas course.
    *   The `gcs_service` uploads these files to a Google Cloud Storage bucket.
    *   The `rag_service` creates a Vertex AI RAG corpus and populates it with the files from GCS.
    *   The `kg_service` uses the `gemini_service` to extract key topics from the course materials and then builds a knowledge graph using the `networkx` library. The graph connects the topics to the relevant course files.
    *   The `firestore_service` saves the state of the course, the RAG corpus ID, and the knowledge graph data to Firestore.

3.  **Student Interaction**:
    *   **Chat**: Students can ask questions through a chat interface. The `chat` route in `routes.py` handles these requests. It uses the `gemini_service` to generate an answer with context from the RAG corpus. The student's query and the bot's answer are logged for analytics.
    *   **Knowledge Graph**: Students can explore the course content through an interactive knowledge graph. The `get_graph` route provides the data for the graph, which is rendered in the frontend using a JavaScript library.

4.  **Analytics**:
    *   The `analytics_logging_service` logs student interactions (chat queries and knowledge graph clicks) to Firestore.
    *   The `analytics_reporting_service` can be triggered by a professor to analyze the logged data. It uses the `gemini_service` to perform clustering on student queries to identify common areas of confusion. The results are saved to Firestore and displayed on the analytics dashboard.

### Service Layer

*   `canvas_service.py`: A wrapper around the Canvas API. It uses the `requests` library to make HTTP calls to fetch course files and other information.
*   `firestore_service.py`: The data access layer for Firestore. It provides a set of functions for creating, reading, updating, and deleting documents in the Firestore database.
*   `gcs_service.py`: Manages file operations with Google Cloud Storage. It uses the `google-cloud-storage` library.
*   `rag_service.py`: Interacts with the Vertex AI RAG engine. It uses the `vertexai` library to create and query RAG corpora.
*   `kg_service.py`: Responsible for the creation and manipulation of the knowledge graph. It uses the `networkx` library to build the graph and the `gemini_service` to extract topics and summarize them.
*   `gemini_service.py`: A wrapper around the Gemini API. It uses the `google.generativeai` library to generate text for summaries, topic extraction, and chat responses.
*   `analytics_logging_service.py`: Handles the logging of analytics events to Firestore. It uses the `firestore_service`.
*   `analytics_reporting_service.py`: Generates analytics reports. It uses the `firestore_service` to fetch data and the `gemini_service` to perform analysis.

## 2. Unit Testing Plan

The goal of this plan is to achieve comprehensive unit test coverage for the application's backend logic. The testing strategy will focus on testing each component in isolation by mocking its dependencies.

### Testing Framework and Tools

*   **Test Runner**: `pytest`
*   **Mocking Library**: `unittest.mock`

### Phase 1: Service Layer Testing

This is the most critical phase, as the service layer contains the core business logic of the application.

*   **`firestore_service.py`**:
    *   **Objective**: Test all Firestore CRUD operations.
    *   **Mocking**: Mock the `google.cloud.firestore.Client` object.
    *   **Assertions**: Assert that the correct Firestore methods are called with the expected arguments. For read operations, assert that the function returns the mocked data correctly.

*   **`canvas_service.py`**:
    *   **Objective**: Test the functions that interact with the Canvas API.
    *   **Mocking**: Mock the `requests.get` method to simulate API responses, including paginated responses and error cases.
    *   **Assertions**: Assert that the functions correctly parse the API responses and handle different HTTP status codes.

*   **`gcs_service.py`**:
    *   **Objective**: Test file uploads and signed URL generation.
    *   **Mocking**: Mock the `google.cloud.storage.Client` object.
    *   **Assertions**: Assert that the correct GCS methods are called with the expected arguments.

*   **`rag_service.py`**:
    *   **Objective**: Test the creation and querying of RAG corpora.
    *   **Mocking**: Mock the `vertexai.preview.rag` and `vertexai.generative_models` modules.
    *   **Assertions**: Assert that the correct Vertex AI methods are called with the expected arguments.

*   **`kg_service.py`**:
    *   **Objective**: Test the knowledge graph creation and manipulation logic.
    *   **Mocking**: Mock the `gemini_service` to provide predefined summaries and topics.
    *   **Assertions**: Assert that the generated graph structure (nodes and edges) is correct based on the mocked input.

*   **`gemini_service.py`**:
    *   **Objective**: Test the functions that interact with the Gemini API.
    *   **Mocking**: Mock the `google.generativeai.GenerativeModel` object.
    *   **Assertions**: Assert that the correct Gemini methods are called with the expected arguments.

*   **`analytics_logging_service.py` and `analytics_reporting_service.py`**:
    *   **Objective**: Test the analytics logging and reporting logic.
    *   **Mocking**: Mock the `firestore_service` and `gemini_service`.
    *   **Assertions**: Assert that the correct data is logged to Firestore and that the reports are generated correctly based on the mocked data.

### Phase 2: API Route Testing

Once the service layer is well-tested, we will test the API routes.

*   **Objective**: Test the routing logic, request/response handling, and status codes for all API endpoints in `app/routes.py`.
*   **Methodology**:
    *   Use the Flask test client to send HTTP requests to each endpoint.
    *   Mock the entire service layer (e.g., `firestore_service`, `canvas_service`, etc.) to isolate the route logic.
    *   Test for both successful and error scenarios (e.g., valid and invalid input, authentication errors, etc.).
*   **Assertions**:
    *   Assert that the HTTP status code of the response is correct.
    *   Assert that the JSON response body is correct.
    *   Assert that the mocked service functions are called with the expected arguments.

### Phase 3: Frontend Testing (Future Consideration)

While the primary focus of this plan is backend unit testing, end-to-end testing of the user interface could be considered in the future. Tools like Selenium or Cypress could be used to automate browser interactions and verify the frontend functionality.

### Continuous Integration

A GitHub Actions workflow will be created to automatically run the entire test suite on every push and pull request to the main branch. This will ensure that code quality is maintained and that new changes do not introduce regressions.
