"""
Flask API Routes (ROLE 2: The "API Router")
Handles all HTTP endpoints and connects frontend to core services.
"""
from flask import request, render_template, jsonify, session, current_app as app
from .services import firestore_service, rag_service, kg_service, canvas_service


@app.route('/launch', methods=['GET', 'POST'])
def launch():
    """
    Main LTI entry point from Canvas.
    Determines app state and renders the appropriate UI.
    """
    # Extract LTI parameters
    course_id = request.args.get('course_id')
    user_id = request.args.get('user_id')
    role = request.args.get('role')

    session["couse_id"] = course_id
    session["user_id"] = user_id
    session["role"] = role
    
    # Determine application state
    state = firestore_service.get_course_state(course_id)
    
    # Render the single-page app with injected state
    return render_template(
        'index.html',
        course_id=course_id,
        user_roles=role,
        user_id = user_id,
        app_state=state
    )


@app.route('/api/initialize-course', methods=['POST'])
def initialize_course():
    """
    Kicks off the entire RAG + KG pipeline.
    This is a long-running request triggered by the professor.
    """
    data = request.json
    course_id = data.get('course_id')
    topics = data.get('topics', '')
    
    # TODO: Implement the full pipeline
    # 1. Create Firestore doc with status: GENERATING
    # 2. Create RAG corpus and upload files
    # 3. Build knowledge graph
    # 4. Finalize Firestore doc with status: ACTIVE
    
    return jsonify({"status": "complete"})


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles student questions using the RAG-powered TA bot.
    """
    data = request.json
    course_id = data.get('course_id')
    query = data.get('query')
    
    # TODO: Implement chat logic
    # 1. Get corpus_id from Firestore
    # 2. Query RAG corpus
    # 3. Return answer with citations
    
    return jsonify({
        "answer": "This is a placeholder response.",
        "sources": []
    })


@app.route('/api/get-graph', methods=['GET'])
def get_graph():
    """
    Fetches the knowledge graph data for visualization.
    """
    course_id = request.args.get('course_id')
    
    # TODO: Implement graph retrieval
    # 1. Get course doc from Firestore
    # 2. Return serialized graph data
    
    return jsonify({
        "nodes": "[]",
        "edges": "[]",
        "data": "{}"
    })
