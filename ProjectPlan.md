📝 Hackathon Project Plan (v5): The Canvas TA-Bot


1. Project Goal & Core Architecture

Goal: A Canvas-integrated LTI app. When a professor activates it, the app indexes all course text files (PDFs) into a Vertex AI RAG Engine. It also generates an interactive Knowledge Graph (KG) connecting professor-defined Topics to the Source Files they are derived from. Students can then use a chat interface to ask the RAG-powered TA bot questions (with citations) and use the KG as a visual, data-driven "gateway" to the course content.

2. Technology Stack

Component
Technology
Role & Rationale
Backend
Flask (Python)
Lightweight, fast to set up, and perfect for handling the Canvas LTI POST launch and providing API endpoints.
Frontend
HTML, CSS, JavaScript
A single index.html (rendered by Flask) with embedded JS/CSS. We'll use Vis.js for graph visualization.
Persistence
Cloud Firestore
Serverless NoSQL database. We'll use one document per course to store all state, RAG IDs, and KG data.
RAG Engine
Vertex AI RAG Engine
Managed service for corpus creation, file ingestion (handles PDF parsing automatically), and retrieval.
LLM
Gemini (via Vertex AI)
Used for 1) The RAG chat agent, 2) Summarizing KG topics, and 3) (Optional) Extracting topics from a syllabus.
KG Logic
networkx
Python library to build the graph (nodes/edges) in memory before serializing it to JSON for storage.


💾 3. Data Structure: The "Course Document"

To maximize speed, we will use a single Firestore document for each course. The LTI context_id will be the document ID.
Collection: courses
Document ID: [course_id_from_canvas] (e.g., "12345")
Fields:
Field Name
Type
Description
status
String
Tracks the app's state for this course: GENERATING or ACTIVE.
corpus_id
String
The unique ID for this course's RAG Corpus, provided by Vertex AI.
indexed_files
Map
A "receipt book" mapping file IDs to their content hash and direct Canvas URL. (e.g., {"file_456": {"hash": "abc", "url": "..."}})
kg_nodes
String
JSON string of all nodes (Topics & Files) for Vis.js. Includes group, value (for sizing), and label.
kg_edges
String
JSON string of all edges (Topic $\rightarrow$ File).
kg_data
String
JSON string mapping topic node IDs to their rich data. (e.g., {"topic_1": {"summary": "...", "sources": [...]}})


🌊 4. User Flow & UI States (The "Gateway")

The entire app is one page that shows different content based on the user's role and the course status.
User Clicks App in Canvas.
Canvas sends POST to our /launch route.
Flask backend checks user's roles and context_id (the course ID).
Flask checks Firestore for a document with that context_id.
Flask renders index.html and injects a STATE variable.
UI State
div to Show
Who Sees It?
What it Does
STATE_NEEDS_INIT
div#init-page
Professor (if doc doesn't exist)
Shows the "Initialize Course" page with the text area for topics.
STATE_NOT_READY
div#not-ready-page
Student (if doc doesn't exist)
Shows a polite message: "This tool is not yet enabled for your course."
STATE_GENERATING
div#loading-page
Everyone
Shows a loading spinner and status: "Hold on, we're building the knowledge base..."
STATE_ACTIVE
div#app-page
Everyone
Shows the main application: The KG visualization, the RAG chat bot, and the UI toggles.


⚙️ 5. API Endpoints (Flask)


POST /launch (The LTI Handler)

Purpose: The main entry point from Canvas.
Logic:
Handles the LTI 1.1 POST request.
Extract context_id (the course ID) and roles from request.form.
Check Firestore: doc = db.collection('courses').document(context_id).get().
Determine STATE (as per the table above).
return render_template('index.html', course_id=context_id, user_roles=roles, app_state=STATE)

POST /api/initialize-course (The "Big One")

Purpose: Kicks off the entire data pipeline. Called by the professor from the STATE_NEEDS_INIT page. This will be a long-running request.
Body: { "course_id": "...", "topics": "Topic 1\nTopic 2\n..." }
Logic:
Set Status: Create the Firestore doc: db.collection('courses').document(course_id).set({'status': 'GENERATING'})
RAG Pipeline (Files):
Create a RAG Corpus: corpus = rag.create_corpus(...)
Get all files from Canvas API (GET /api/v1/courses/:course_id/files).
Initialize indexed_files = {}, file_nodes = [].
Loop through files:
Download raw PDF content into server memory (io.BytesIO).
Upload raw file to RAG Corpus: rag.import_files(corpus.name, [raw_file_bytes], metadata={...}). Vertex AI handles PDF parsing.
Store file info: indexed_files[file.id] = {"hash": file.hash, "url": file.html_url}.
Add to graph: file_nodes.append({"id": file.id, "label": file.name, "group": "file_pdf", ...}).
KG Pipeline (Topics):
Get topic_list from request.json.get('topics').
(AI Option): If topics is empty, get the syllabus, send to Gemini, and parse the topic_list.
Initialize networkx graph, kg_data = {}, topic_nodes = [], edges = [].
For each topic in topic_list:
Add to graph: topic_nodes.append({"id": topic_id, "label": topic, "group": "topic", ...}).
Query RAG corpus: contexts = rag.retrieve_contexts(corpus.name, topic).
Call Gemini: "Using this context: [contexts], write a 1-paragraph summary for the topic: [topic]."
Store summary and sources in kg_data.
Create Edges: For each source in contexts, add an edge: edges.append({"from": topic_id, "to": source.file_id}).
Finalize:
Serialize all graph data (kg_nodes + file_nodes, edges, kg_data) to JSON strings.
Update the Firestore doc with all fields and set status = 'ACTIVE'.
return {"status": "complete"}.

POST /api/chat (The TA Bot - MVP)

Purpose: Handles a student's question.
Body: { "course_id": "...", "query": "..." }
Logic:
Get doc from Firestore using course_id. Get corpus_id.
Query RAG corpus: contexts = rag.retrieve_contexts(corpus.name, query).
Extract source names: citations = [c.source_display_name for c in contexts].
Call Gemini: "You are a helpful TA. Answer the user's question: [query] based only on this context: [contexts]. Cite the sources you use from this list: [citations]."
return {"answer": gemini_response.text, "sources": citations}.

GET /api/get-graph (The KG Data)

Purpose: Fetches the graph data for the UI.
Query Params: ?course_id=...
Logic:
Get doc from Firestore.
return {"nodes": doc.kg_nodes, "edges": doc.kg_edges, "data": doc.kg_data} (These are already JSON strings).
The frontend JS will parse these strings and feed them to Vis.js.

✨ 6. Stretch Goals (In Order of Priority)
Conversational Memory: Allow the AI TA to remember previous messages and answer follow-up questions (e.g., "What is mitosis?" followed by "What is the first phase of it?").
Backend: The Flask route will pass the entire history array to the Gemini API, which natively supports conversational context. The RAG query will be performed using the last user message in the array.
File Node Summaries (Your Goal): When a file node is clicked, show a "See More" button that links to the file.url.
Stretch: Create a new POST /api/summarize-file endpoint. When a file node is clicked, the UI calls this endpoint. The backend retrieves all text for that one file from the RAG corpus and asks Gemini to summarize it, showing the summary above the "See More" button.
AI-Generated Question Starters: Add a POST /api/get-suggested-questions route that hits Gemini ("Generate 3 questions about [topic]"). The UI calls this when a topic node is clicked.
Dynamic RAG-to-Graph Highlighting: When the /api/chat response returns sources, the frontend JS will find those nodes in the Vis.js graph and highlight or "pulse" them to visually connect the chat to the map.
