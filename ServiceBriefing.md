Backend Task Briefing: The Core Services (The "Engine")

Welcome to the team. Your role is the most critical: you are building the "engine" of the entire application. You will be responsible for all the heavy lifting, complex logic, and external API interactions.
You will work almost exclusively in the app/services/ directory, building a set of pure Python functions.
Your job is not to write Flask routes or worry about HTTP. Your job is to:
Write functions that perform specific, complex tasks (e.g., "create a RAG corpus," "build a knowledge graph").
Interact directly with all external SDKs: Google Cloud (Firestore, Vertex AI), networkx, and the Canvas API (requests).
Fulfill the "Python Internal API" contract (listed below) so the API Router (Role 2) can simply call your functions.
You will work in parallel with the rest of the team. You can and should write your functions and test them independently (e.g., in a simple test.py script) before the API Router is ready.

1. Core Tasks (Your To-Do List)

Your work is divided into four main service files.

firestore_service.py (State Management)

Goal: Create functions to manage the "Course Document" in Firestore.
Functions to Build:
get_course_state(db, course_id: str) -> str:
Fetch the doc: doc = db.collection('courses').document(course_id).get().
If not doc.exists: return 'NEEDS_INIT' (if we assume professor-only access for now, or you can add role checking later).
If doc.get('status') == 'GENERATING': return 'GENERATING'.
If doc.get('status') == 'ACTIVE': return 'ACTIVE'.
(This logic will be called by the POST /launch route).
get_course_data(db, course_id: str) -> dict:
Fetch the doc and return its data: return db.collection('courses').document(course_id).get().to_dict().
create_course_doc(db, course_id: str):
Creates the initial document: db.collection('courses').document(course_id).set({'status': 'GENERATING'}).
finalize_course_doc(db, course_id: str, data: dict):
Updates the document with all the final data and sets status to active.
db.collection('courses').document(course_id).update(data)
db.collection('courses').document(course_id).update({'status': 'ACTIVE'})

canvas_service.py (Data Retrieval)

Goal: Fetch all necessary data from the Canvas LMS API.
Functions to Build:
get_course_files(course_id: str, token: str) -> (list, dict):
Use requests to hit GET /api/v1/courses/:course_id/files.
Handle API pagination (looping through Link headers).
Filter for allowed file types (e.g., .pdf).
Return two things:
A list of file objects (containing at least id, display_name, url for downloading, and md5 or etag for hash).
An indexed_files map (e.g., {"file_id_123": {"hash": "abc...", "url": "..."}}) for the Firestore doc.
get_syllabus(course_id: str, token: str) -> str:
Hit GET /api/v1/courses/:course_id and get the syllabus_body.
Return the raw text/HTML.

rag_service.py (The RAG Engine)

Goal: Interface with the Vertex AI RAG Engine SDK.
Functions to Build:
create_and_provision_corpus(files: list, canvas_token: str) -> str:
Initialize the Vertex AI client.
Call rag.create_corpus(...) to create a new corpus. Get its corpus.name.
Loop through the files list. For each file:
Use requests to download the file content from its file.url into an io.BytesIO object (in-memory).
Call rag.import_files(corpus.name, [file_bytes], metadata={'file_id': file.id, 'display_name': file.name, 'canvas_url': file.html_url}).
Crucially, Vertex AI handles the PDF parsing automatically.
Return the corpus.name (e.g., projects/.../ragCorpora/...).
query_rag_corpus(corpus_id: str, query: str) -> (str, list):
Call contexts = rag.retrieve_contexts(corpus_id, query).
Extract the text chunks: context_text = [c.text for c in contexts].
Extract the citations: citations = list(set([c.metadata['display_name'] for c in contexts])).
Call the Gemini model: response = gemini_model.generate_content("Prompt: ... Context: [context_text] ... Query: [query] ... Sources: [citations]").
Return (response.text, citations).

kg_service.py (The Knowledge Graph Engine)

Goal: Build and summarize the entire knowledge graph.
Functions to Build:
build_knowledge_graph(topic_list: list, corpus_id: str, files: list) -> (str, str, str):
Initialize G = networkx.Graph(), kg_data = {}, kg_nodes = [], kg_edges = [].
Create Topic Nodes: Loop through topic_list, add each as a node to G and kg_nodes (e.g., {'id': 'topic_1', 'label': 'Cell Mitosis', 'group': 'topic'}).
Create File Nodes: Loop through files list, add each as a node to G and kg_nodes (e.g., {'id': 'file_123', 'label': 'Chapter 3.pdf', 'group': 'file_pdf'}).
Create Edges & Summaries: Loop through each topic in topic_list:
Call contexts = rag.retrieve_contexts(corpus_id, topic).
Call Gemini: summary = gemini_model.generate_content("Summarize [topic] using this context: [contexts]").
Extract source_files = [{'name': c.metadata['display_name'], 'url': c.metadata['canvas_url']} for c in contexts].
Extract source_file_ids = list(set([c.metadata['file_id'] for c in contexts])).
Store summary & sources: kg_data[topic_id] = {'summary': summary.text, 'sources': source_files}.
Add Edges to graph: For each file_id in source_file_ids, call G.add_edge(topic_id, file_id).
Data-Driven Sizing: Calculate node sizes: for node in G.nodes(): G.nodes[node]['value'] = G.degree(node).
Serialize:
nodes_json = json.dumps(networkx.node_link_data(G)['nodes'])
edges_json = json.dumps(networkx.node_link_data(G)['links'])
data_json = json.dumps(kg_data)
Return (nodes_json, edges_json, data_json).

2. Tools & Technologies

Google Cloud SDKs: google-cloud-firestore, google-cloud-aiplatform (for Vertex AI RAG and Gemini).
networkx: For graph creation, manipulation, and serialization.
requests: For calling the Canvas API.
pypdf: (REMOVED) Vertex AI handles PDF parsing.
Authentication: You will use a service-account.json file for all Google Cloud auth. Assume the Canvas API token is passed in as a string.

3. Your Contract (What the API Router expects from you)

You must provide these functions. The API Router (Role 2) is building their code assuming these exact inputs and outputs.

Python


# --- app.services.firestore_service ---
def get_course_state(db, course_id: str) -> str: ...
def get_course_data(db, course_id: str) -> dict: ...
def create_course_doc(db, course_id: str): ...
def finalize_course_doc(db, course_id: str, data: dict): ...

# --- app.services.canvas_service ---
# Returns: (list_of_file_objects, dict_of_indexed_files_map)
def get_course_files(course_id: str, token: str) -> (list, dict): ...
def get_syllabus(course_id: str, token: str) -> str: ...

# --- app.services.rag_service ---
# Returns: new_corpus_id (str)
def create_and_provision_corpus(files: list, canvas_token: str) -> str: ...
# Returns: (answer_text, list_of_source_names)
def query_rag_corpus(corpus_id: str, query: str) -> (str, list): ...

# --- app.services.kg_service ---
# Returns: (nodes_json_str, edges_json_str, data_json_str)
def build_knowledge_graph(topic_list: list, corpus_id: str, files: list) -> (str, str, str): ...



4. Stretch Goals (Your Task)

If you complete the MVP, you will add the following functions for the API Router to call.
Conversational Memory:
Modify query_rag_corpus or create query_rag_with_history(corpus_id: str, history: list) -> (str, list):
This function will take the full chat history.
The RAG query will be based on the last user message (history[-1]).
The Gemini generate_content call will receive the entire history list for conversational context.
File Node Summaries:
Create summarize_file(corpus_id: str, file_id: str) -> str:
This is tricky. You'll need to query the RAG corpus by metadata to retrieve all chunks where metadata.file_id == file_id.
Concatenate these chunks and send them to Gemini for summarization.
AI-Generated Questions:
Create get_suggested_questions(topic: str) -> list:
This is a simple passthrough. Call Gemini with a prompt like "Generate 3 good follow-up questions a student might have about [topic]."
Parse the response and return a list of question strings.
