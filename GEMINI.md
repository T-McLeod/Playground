# GEMINI.md

This file provides a comprehensive overview of the Canvas TA-Bot project, its architecture, and development conventions. It is intended to be used as a context for future interactions with the Gemini CLI.

## Project Overview

The Canvas TA-Bot is a Flask-based web application that integrates with the Canvas Learning Management System (LMS) as an LTI tool. Its primary purpose is to provide an AI-powered teaching assistant to students. The bot can answer student questions based on the course materials, and it provides an interactive knowledge graph to help students explore the course content. The project also includes an analytics dashboard for professors to gain insights into student queries and areas of confusion.

### Key Technologies

*   **Backend**: Flask (Python)
*   **Frontend**: HTML, CSS, JavaScript
*   **Database**: Google Cloud Firestore
*   **AI/ML**:
    *   Google Vertex AI RAG (Retrieval-Augmented Generation) for question answering
    *   Google Gemini for summarization and topic extraction
*   **Storage**: Google Cloud Storage (GCS) for storing course files
*   **Authentication**: Canvas API token

### Architecture

The application follows a service-oriented architecture. The main components are:

*   **Flask App (`app`)**: The core Flask application, which handles routing, LTI launch, and serving the frontend.
*   **Services (`app/services`)**: A collection of services that encapsulate the business logic and interact with external APIs and databases.
    *   `canvas_service.py`: Interacts with the Canvas API to fetch course files and syllabus.
    *   `firestore_service.py`: Manages all interactions with Google Cloud Firestore for data persistence.
    *   `gcs_service.py`: Handles file uploads to and downloads from Google Cloud Storage.
    *   `rag_service.py`: Manages the creation of and retrieval from the Vertex AI RAG corpus.
    *   `kg_service.py`: Builds and manages the knowledge graph using the `networkx` library.
    *   `gemini_service.py`: Interacts with the Gemini API for summarization and answer generation.
    *   `analytics_logging_service.py`: Logs student interactions for analytics.
    *   `analytics_reporting_service.py`: Generates analytics reports for professors.
*   **Frontend (`app/templates` and `app/static`)**: The user interface, consisting of HTML templates, CSS stylesheets, and JavaScript files.

## Building and Running

### 1. Environment Setup

1.  **Clone the repository.**
2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Environment Variables

1.  **Copy the environment template:**
    ```bash
    cp .env.example .env
    ```
2.  **Configure your `.env` file** with the necessary credentials for Flask, Canvas, and Google Cloud.

### 3. Running the Application

```bash
python run.py
```

The application will be available at `http://localhost:5000`.

### 4. Running Tests

The project uses `pytest` for testing. To run the tests, use the following command:

```bash
python -m pytest
```

## Development Conventions

### Coding Style

The project follows the PEP 8 style guide for Python code.

### Testing

*   Unit tests are written using the `unittest` framework and `pytest`.
*   External services and APIs are mocked using `unittest.mock`.
*   Tests are located in the `tests` directory.

### API Contracts

The API contracts between the frontend and backend are documented in the `README.md` file.
