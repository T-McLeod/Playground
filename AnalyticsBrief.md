Briefing 1: firestore_service.py Developer (Expanded Role)
Mission: Your role as the "Database Specialist" is being expanded. A new analytics_service will be your "customer." You are responsible for adding new functions to app/services/firestore_service.py to handle all database operations for this new feature. Your service is the only service that should talk directly to Firestore.

New Firestore Collections to Manage:

course_analytics: This collection will store every single log event (each chat query, each KG click) as a separate document.

analytics_reports: This collection will store the final, generated report for each course, with the course_id as the document ID.

Core Tasks: New Functions to Add
You must add the following functions to app/services/firestore_service.py for the analytics_service to consume.

1. Function for Logging Events:

Signature: log_analytics_event(db, data: dict)

Logic:

This is a simple write function. It receives a pre-formatted data dictionary from the analytics_service.

It must create a new document (with an auto-generated ID) in the course_analytics collection.

Returns: The doc_id of the newly created log document (this is crucial for the "rating" stretch goal).

2. Function to Fetch Vectors for Clustering:

Signature: get_all_analytics_vectors(db, course_id: str) -> list[dict]

Logic:

Query the course_analytics collection.

Filter by where("course_id", "==", course_id) and where("type", "==", "chat").

Return a list of dictionaries. Each dictionary must contain the Firestore document ID (e.g., doc.id) and the vector (e.g., doc.get('query_vector')).

Example return: [ {"doc_id": "xyz", "vector": [0.1, ...]}, {"doc_id": "abc", "vector": [0.4, ...]} ]

3. Function to Fetch Text for Labeling:

Signature: get_query_text_for_cluster(db, doc_ids: list[str]) -> list[str]

Logic:

This function will be called after clustering is complete.

It receives a list of document IDs.

Efficiently fetch all these documents (e.g., using db.collection('course_analytics').where('__name__', 'in', doc_ids).stream()).

Return a list of just the query_text strings from those documents.

4. Functions for Managing Reports:

Signature: save_analytics_report(db, course_id: str, report_data: dict)

Logic:

This function will set (overwrite) the analytics report for the given course.

Use db.collection('analytics_reports').document(course_id).set(report_data).

Signature: get_analytics_report(db, course_id: str) -> dict

Logic:

Fetches and returns the latest report document from analytics_reports for the professor's dashboard.

return db.collection('analytics_reports').document(course_id).get().to_dict()

Stretch Goal Task:
1. Function to Rate an Answer:

Signature: rate_analytics_event(db, doc_id: str, rating: str)

Logic:

Find the specific log document in course_analytics using its doc_id.

Update that single document's rating field (e.g., from null to "good" or "bad").

Briefing 2: analytics_service.py Developer (New Role)
Mission: You are the "Data Scientist" for this project. Your job is to build the new app/services/analytics_service.py file from scratch. You will create the logic to generate valuable insights for professors.

You are an orchestrator. You will not interact directly with Firestore or Vertex AI. Your service will only import and call functions from:

app.services.firestore_service.py (to read/write data)

app.services.gemini_service.py (to get embeddings and labels)

Core Tasks: Functions to Build
You will build the internal logic and the functions that the API Router (routes.py) will call.

1. Functions for Real-time Logging:

Signature (Internal): log_chat_query(course_id: str, query_text: str) -> str

Logic:

Call the gemini_service to get the embedding: query_vector = gemini_service.get_embedding(text=query_text, model="text-embedding-004", task_type="RETRIEVAL_QUERY")

Prepare the data packet: log_data = {"type": "chat", "course_id": course_id, ... "query_vector": query_vector, "rating": None}

Call the firestore_service to save it: doc_id = firestore_service.log_analytics_event(data=log_data)

Return the doc_id (so the API Router can pass it to the frontend for the stretch goal).

Signature (Internal): log_kg_node_click(course_id: str, node_id: str, node_label: str)

Logic:

Prepare the data packet: log_data = {"type": "kg_click", "course_id": course_id, ...}

Call firestore_service.log_analytics_event(data=log_data).

2. The Main Batch Analytics Function:

Signature (Internal): run_daily_analytics(course_id: str)

Logic:

Fetch: Get all vectors from the database: vector_data = firestore_service.get_all_analytics_vectors(course_id)

Cluster:

Load vectors into a numpy array (e.g., vectors = [item['vector'] for item in vector_data]).

Initialize MiniBatchKMeans(n_clusters=5) and fit it on the vectors array.

Get the labels_ (cluster assignments) for each vector.

Label:

Loop through each cluster (e.g., cluster 0 to 4).

Create a list of doc_ids that belong to that cluster.

Get the raw text for those docs: query_texts = firestore_service.get_query_text_for_cluster(doc_ids)

Get a human-readable label from the AI: cluster_label = gemini_service.get_cluster_label(query_texts)

Store the results in a report dict (e.g., report[cluster_label] = len(doc_ids)).

Save: Save the final report to the database: firestore_service.save_analytics_report(course_id, report_data=report)

3. Function to Serve the Report:

Signature (Internal): get_analytics_report(course_id: str) -> dict

Logic: This is a simple passthrough:

return firestore_service.get_analytics_report(course_id)

Your Contract (What You Provide to the API Router):
The API Router will import and call these functions from your service:

Python

# --- app.services.analytics_service.py ---

# Called by POST /api/chat. Returns the log document ID.
def log_chat_query(course_id: str, query_text: str) -> str: ...

# Called by a new POST /api/log-click
def log_kg_node_click(course_id: str, node_id: str, node_label: str): ...

# Called by a new admin POST /api/run-analytics
def run_daily_analytics(course_id: str): ...

# Called by a new GET /api/get-analytics
def get_analytics_report(course_id: str) -> dict: ...

# (Stretch Goal) Called by a new POST /api/rate-answer
def rate_answer(doc_id: str, rating: str):
    # This is a passthrough to the firestore_service
    firestore_service.rate_analytics_event(doc_id, rating)