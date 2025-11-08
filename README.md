# Canvas TA-Bot

A Canvas-integrated LTI app that indexes course materials into a Vertex AI RAG Engine and generates an interactive Knowledge Graph for students to explore course content.

## 📂 Repository Structure

```
/canvas-ta-bot/
|
|-- /app                   # Main Flask application package
|   |
|   |-- /static/           # CSS, JS, and libraries
|   |   |-- style.css
|   |   |-- app.js         # All frontend JS logic
|   |   |-- vis-network.min.js
|   |
|   |-- /templates/        # Flask HTML templates
|   |   |-- index.html     # Main UI file
|   |
|   |-- /services/         # Core business logic
|   |   |-- __init__.py
|   |   |-- rag_service.py       # Vertex AI RAG SDK calls
|   |   |-- kg_service.py        # networkx graph logic
|   |   |-- firestore_service.py # Firestore operations
|   |   |-- canvas_service.py    # Canvas API calls
|   |
|   |-- __init__.py        # Flask app initialization
|   |-- routes.py          # All Flask API routes
|
|-- requirements.txt       # Python dependencies
|-- service-account.json   # GCP auth key (not tracked)
|-- .gitignore
|-- README.md
```

## 🚀 Setup & Configuration

### 1. Environment Setup

1. **Clone the repository and navigate to the project directory**
   ```bash
   git clone <repository-url>
   cd canvas-ta-bot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   # On Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # On Unix/Mac:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### 2. Environment Variables

1. **Copy the environment template**
   ```bash
   cp .env.example .env
   ```

2. **Configure your `.env` file with the following variables:**

   ```bash
   # Flask Configuration
   SECRET_KEY=your-secret-key-here

   # Canvas LMS API Configuration
   CANVAS_API_TOKEN=your_canvas_api_token_here
   CANVAS_BASE_URL=https://canvas.instructure.com/api/v1
   CANVAS_TEST_COURSE_ID=your_test_course_id_here

   # Google Cloud Platform Configuration
   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   GOOGLE_APPLICATION_CREDENTIALS=service-account.json

   # Application Configuration
   FLASK_ENV=development
   FLASK_DEBUG=True

   # Logging Configuration
   LOG_LEVEL=INFO
   ```

### 3. API Credentials Setup

#### Canvas API Token
1. Log in to your Canvas instance
2. Go to **Account → Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Set purpose and expiration
6. Copy the generated token to `CANVAS_API_TOKEN` in your `.env` file

#### Google Cloud Credentials
1. Create a GCP project or use an existing one
2. Enable the following APIs:
   - Vertex AI API
   - Cloud Firestore API
3. Create a service account with appropriate permissions
4. Download the service account key JSON file
5. Place it as `service-account.json` in the project root
6. Update `GOOGLE_CLOUD_PROJECT` in your `.env` file

### 4. Run the Application

```bash
# Make sure your virtual environment is activated
python run.py
```

The application will start on `http://localhost:5000`

## 🤝 API Contracts

### Frontend <-> Backend (HTTP API)

| Endpoint | Method | Request Body | Response Body |
|----------|--------|--------------|---------------|
| `/api/initialize-course` | POST | `{ "course_id": "str", "topics": "str" }` | `{ "status": "complete" }` |
| `/api/chat` | POST | `{ "course_id": "str", "query": "str" }` | `{ "answer": "str", "sources": ["str", "str"] }` |
| `/api/get-graph` | GET | Query param: `?course_id=str` | `{ "nodes": "json-str", "edges": "json-str", "data": "json-str" }` |

### Backend Internal API (Python Functions)

#### firestore_service.py
- `get_course_state(course_id: str) -> str`: Returns the STATE (e.g., NEEDS_INIT, ACTIVE)
- `create_course_doc(course_id: str)`: Creates initial doc with status: GENERATING
- `get_course_data(course_id: str) -> DocumentSnapshot`: Fetches the whole course doc
- `finalize_course_doc(course_id: str, data: dict)`: Updates doc with RAG/KG data and sets status: ACTIVE

#### rag_service.py
- `create_and_provision_corpus(files: list) -> str`: Creates corpus, uploads files, returns corpus_id
- `query_rag_corpus(corpus_id: str, query: str) -> (str, list)`: Returns (answer_text, [source_names])

#### kg_service.py
- `build_knowledge_graph(topic_list: list, corpus_id: str, files: list) -> (str, str, str)`: Returns (nodes_json, edges_json, data_json)

#### canvas_service.py
- `get_course_files(course_id: str, token: str) -> list`: Fetches all file objects from Canvas
- `get_syllabus(course_id: str, token: str) -> str`: Fetches syllabus text

## 🚀 Setup & Installation

### 1. Environment Configuration

The application uses environment variables for configuration. Copy the example file and configure your settings:

```bash
# Copy the environment template
cp .env.example .env

# Edit with your actual values
# nano .env  # or your preferred editor
```

#### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret | `your-random-secret-key` |
| `CANVAS_API_TOKEN` | Canvas LMS API token | `7~abc123...` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | `my-canvas-project` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key | `service-account.json` |

#### Environment Check

Run the environment verification script to ensure everything is configured correctly:

```bash
python check_env.py
```

This will show you:
- ✅ Which variables are properly set
- ❌ Which variables need configuration
- 📁 File existence checks

### 2. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

### 3. Google Cloud Setup

1. **Create a GCP Project** (or use existing)
2. **Enable Required APIs:**
   - Vertex AI API
   - Firestore API
3. **Create Service Account:**
   - Go to IAM & Admin → Service Accounts
   - Create new service account with necessary permissions
   - Download JSON key file as `service-account.json`
4. **Update `.env`** with your project ID

### 4. Canvas LMS Setup

1. **Generate API Token:**
   - Canvas: Account → Settings → Approved Integrations
   - Create new access token
2. **Update `.env`** with your token

### 5. Run the Application

```bash
# Start the development server
python run.py
```

The application will be available at `http://localhost:5000`

---

## 🔧 Configuration Details

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | None | Flask session secret key (generate randomly) |
| `CANVAS_API_TOKEN` | ✅ | None | Canvas LMS API access token |
| `CANVAS_BASE_URL` | ❌ | `https://canvas.instructure.com/api/v1` | Canvas API base URL |
| `CANVAS_TEST_COURSE_ID` | ❌ | None | Course ID for testing Canvas integration |
| `GOOGLE_CLOUD_PROJECT` | ✅ | None | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | ❌ | `us-central1` | GCP region for Vertex AI |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ | `service-account.json` | Path to GCP service account key |
| `FLASK_ENV` | ❌ | `production` | Flask environment (development/production) |
| `FLASK_DEBUG` | ❌ | `False` | Enable Flask debug mode |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### File Structure Requirements

```
canvas-ta-bot/
├── .env                    # Environment variables (not in git)
├── service-account.json    # GCP credentials (not in git)
├── requirements.txt        # Python dependencies
├── run.py                 # Application entry point
├── check_env.py           # Environment verification
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── routes.py          # API endpoints
│   ├── services/          # Business logic services
│   ├── templates/         # HTML templates
│   └── static/            # CSS/JS assets
└── README.md
```

### Service Dependencies

#### Canvas Service
- **API Endpoint**: Configurable via `CANVAS_BASE_URL`
- **Authentication**: Bearer token via `CANVAS_API_TOKEN`
- **Rate Limits**: Respects Canvas API rate limits with backoff
- **Pagination**: Handles paginated responses automatically

#### GCP Services
- **Vertex AI**: Used for RAG corpus creation and querying
- **Firestore**: Document database for course state and metadata
- **Authentication**: Service account key file specified in `GOOGLE_APPLICATION_CREDENTIALS`

#### Flask Application
- **Session Management**: Uses `SECRET_KEY` for secure sessions
- **CORS**: Configured for cross-origin requests from frontend
- **Error Handling**: Comprehensive error responses with appropriate HTTP codes

### Development vs Production

#### Development Mode (`FLASK_ENV=development`)
- Debug mode enabled
- Detailed error pages
- Auto-reload on code changes
- Verbose logging

#### Production Mode (`FLASK_ENV=production`)
- Debug disabled
- Minimal error pages
- Optimized performance
- Configurable log levels

### Troubleshooting

#### Common Issues

1. **Environment Variables Not Loading**
   ```bash
   # Check if .env exists and has correct format
   python check_env.py
   ```

2. **GCP Authentication Errors**
   - Verify `service-account.json` exists and has correct permissions
   - Check `GOOGLE_CLOUD_PROJECT` matches your GCP project
   - Ensure Vertex AI and Firestore APIs are enabled

3. **Canvas API Errors**
   - Verify `CANVAS_API_TOKEN` is valid and not expired
   - Check `CANVAS_BASE_URL` matches your Canvas instance
   - Ensure token has necessary permissions for course access

4. **Port Already in Use**
   ```bash
   # Find process using port 5000
   netstat -ano | findstr :5000
   # Kill the process or change port in run.py
   ```

#### Debug Commands

```bash
# Test environment loading
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('SECRET_KEY:', os.getenv('SECRET_KEY'))"

# Test Flask app startup
python -c "from app import create_app; app = create_app(); print('App created successfully')"

# Check GCP credentials
python -c "import os; from google.cloud import firestore; db = firestore.Client(); print('GCP connection successful')"
```

---

## 🧪 Testing & Validation

### Environment Validation

Before running the application, always validate your environment setup:

```bash
python check_env.py
```

### Unit Testing

Run the test suite to validate individual components:

```bash
# Run all tests
python -m pytest

# Run specific service tests
python -m pytest tests/test_canvas_service.py
python -m pytest tests/test_rag_service.py
```

### Integration Testing

Test the full application workflow:

1. **Canvas Integration Test**
   ```bash
   python -c "
   from app.services.canvas_service import CanvasService
   service = CanvasService()
   files = service.get_course_files(os.getenv('CANVAS_TEST_COURSE_ID'))
   print(f'Found {len(files)} files')
   "
   ```

2. **GCP Integration Test**
   ```bash
   python -c "
   from google.cloud import firestore
   db = firestore.Client()
   print('Firestore connection successful')
   "
   ```

### API Testing

Test API endpoints using curl or Postman:

```bash
# Test course initialization
curl -X POST http://localhost:5000/api/initialize-course \
  -H "Content-Type: application/json" \
  -d '{"course_id": "123", "topics": "machine learning"}'

# Test chat endpoint
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"course_id": "123", "query": "What is supervised learning?"}'
```

### Performance Testing

Monitor application performance:

```bash
# Check memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

### Logging

Monitor application logs for errors and performance:

```bash
# View application logs
tail -f logs/app.log

# Check for errors
grep ERROR logs/app.log
```

---

## 📚 Additional Resources

- [Canvas LMS API Documentation](https://canvas.instructure.com/doc/api/)
- [Google Cloud Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)

---

*For questions or issues, please check the troubleshooting section or create an issue in the repository.*
