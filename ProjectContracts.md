We should structure this based on three distinct components that can be built in parallel:
The Frontend (UI): A single index.html file with JavaScript that handles all UI states, Vis.js rendering, and API calls.
The Backend (API/Routes): The Flask routes.py file that handles the LTI launch and all HTTP API endpoints. This is the "plumbing" or "glue."
The Backend (Core Services): The heavy-lifting Python logic. All the calls to Vertex AI, Firestore, Canvas, and networkx. This is the "engine."
Here’s the complete breakdown of the repo, roles, and communication contracts.

📂 1. Repo Structure

A simple monorepo is best for a hackathon. Here is the proposed structure, which separates our three components.



/canvas-ta-bot/
|
|-- /app                   <-- Our main Flask application package
|   |
|   |-- /static/           <-- For CSS, JS, and libraries
|   |   |-- style.css
|   |   |-- app.js         <-- (ROLE 1) All frontend JS logic here
|   |   |-- vis-network.min.js
|   |
|   |-- /templates/        <-- Flask's folder for HTML
|   |   |-- index.html     <-- (ROLE 1) The one and only UI file
|   |
|   |-- /services/         <-- (ROLE 3) The "engine" / core logic
|   |   |-- __init__.py
|   |   |-- rag_service.py   <-- All Vertex AI RAG SDK calls
|   |   |-- kg_service.py    <-- All networkx, graph, & summary logic
|   |   |-- firestore_service.py <-- All Firestore get/set logic
|   |   |-- canvas_service.py  <-- All Canvas API call logic
|   |
|   |-- __init__.py        <-- Initializes the Flask app
|   |-- routes.py          <-- (ROLE 2) All Flask API routes
|
|-- requirements.txt       <-- All Python packages (flask, google-cloud-vertexai, etc.)
|-- service-account.json   <-- (ASSUMPTION) Our GCP auth key
|-- .gitignore
|-- README.md              <-- We will copy the API contracts here



👥 2. Delegation & Team Roles

This structure allows for a clean 3-way split of work.

Role 1: Frontend Developer (The "UI")

Files: app/templates/index.html and app/static/app.js
Mission:
Build the 4 UI states (NEEDS_INIT, NOT_READY, GENERATING, ACTIVE).
Create the Vis.js graph rendering and click-event logic (e.g., showTopicInfo(...)).
Create the chat bot interface.
Create the "Show Course Files" toggle.
Key Assumption: This developer does not wait for the backend. They work off mock data. They assume the API endpoints exist and will return the JSON defined in the contract below.

Role 2: Backend Developer (The "API Router")

File: app/routes.py
Mission:
Write all the Flask routes (@app.route(...)).
Handle the POST /launch LTI logic to determine the STATE and render the index.html template.
Write the API endpoints (/api/initialize-course, /api/chat, /api/get-graph).
This role only writes "plumbing" logic. It handles HTTP requests/responses and calls the "Core Services" functions to do the real work.

Role 3: Backend Developer (The "Core Services")

Files: Everything in app/services/
Mission:
Write the actual business logic for the entire app.
Write the Python function to create and provision the Vertex AI RAG corpus (rag_service.py).
Write the function to build the networkx graph, create summaries, and link sources (kg_service.py).
Write the helper functions to get/set data from Firestore (firestore_service.py).
Write the helper to get files from the Canvas API (canvas_service.py).
Key Assumption: This developer does not care about HTTP or Flask. They just write and test pure Python functions.

🤝 3. Communication Contracts (The API)

This is the most important part. These are the "assumptions" everyone must agree on.

Contract 1: Frontend <-> Backend (The HTTP API)

The Frontend (Role 1) uses this API. The API Router (Role 2) builds it.
Endpoint
Method
Request Body (JSON)
Response Body (JSON)
/api/initialize-course
POST
{ "course_id": "str", "topics": "str" }
{ "status": "complete" }
/api/chat
POST
{ "course_id": "str", "query": "str" }
{ "answer": "str", "sources": ["str", "str"] }
/api/get-graph
GET
(Uses query param) ?course_id=str
{ "nodes": "json-str", "edges": "json-str", "data": "json-str" }


Contract 2: Backend <-> Backend (The Python "Internal API")

The API Router (Role 2) uses these functions. The Core Services (Role 3) builds them.
From firestore_service.py:
get_course_state(course_id: str) -> str: Returns the STATE (e.g., NEEDS_INIT, ACTIVE).
create_course_doc(course_id: str): Creates the initial doc with status: GENERATING.
get_course_data(course_id: str) -> DocumentSnapshot: Fetches the whole course doc.
finalize_course_doc(course_id: str, data: dict): Updates the doc with all RAG/KG data and sets status: ACTIVE.
From rag_service.py:
create_and_provision_corpus(files: list) -> str: Takes a list of file objects, creates a new corpus, uploads the files, and returns the corpus_id.
query_rag_corpus(corpus_id: str, query: str) -> (str, list): Takes a query, hits RAG, and returns (answer_text, [source_names_list]).
From kg_service.py:
build_knowledge_graph(topic_list: list, corpus_id: str, files: list) -> (str, str, str): The "big one." Takes the topics/files, does the RAG lookups, builds the networkx graph, and returns the three serialized JSON strings: (nodes_json, edges_json, data_json).
From canvas_service.py:
get_course_files(course_id: str, token: str) -> list: Fetches all file objects from Canvas.
get_syllabus(course_id: str, token: str) -> str: Fetches the syllabus text (for the AI topic option).
By defining these roles and contracts, everyone can start coding immediately. Role 1 builds the UI with mock JSON. Role 3 writes Python functions and tests them. Role 2 connects them together.
