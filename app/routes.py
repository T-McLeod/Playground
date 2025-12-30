"""
Flask API Routes (ROLE 2: The "API Router")
Handles all HTTP endpoints and connects frontend to core services.
"""
from flask import request, render_template, jsonify, session, current_app as app

from app.models.canvas_models import Quiz_Answer, Quiz_Question
from .services.llm_services import get_llm_service
from .services.rag_services import get_rag_service
from .services.orchestration import initialize_course_from_canvas
from .services import firestore_service, kg_service, canvas_service, gcs_service, analytics_logging_service
from .services.llm_services import dukegpt_service
import os
import logging
import shutil
import json

logger = logging.getLogger(__name__)

# Get Canvas API token from environment
CANVAS_TOKEN = os.environ.get('CANVAS_API_TOKEN')


llm_service = get_llm_service()
rag_service = get_rag_service()

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for container orchestration.
    Returns 200 OK if the application is running.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'canvas-ta-bot'
    }), 200


@app.route('/launch', methods=['GET', 'POST'])
def launch():
    """
    Main LTI entry point from Canvas.
    Determines app state and renders the appropriate UI.
    """
    # Extract LTI parameters
    course_id = request.args.get('course_id')
    playground_id = request.args.get('playground_id')
    user_id = request.args.get('user_id')
    role = request.args.get('role')

    session["couse_id"] = course_id
    session["user_id"] = user_id
    session["role"] = role
    
    # Determine application state
    if not playground_id:
        playground_id = firestore_service.get_playground_id_for_course(course_id)
    state = firestore_service.get_course_state(playground_id)
    
    # When course is ACTIVE, route based on role
    if state == 'ACTIVE':
        # Route based on role
        if role:
            role_lower = role.lower()
            # Students get the student exploration interface
            if 'student' in role_lower:
                return render_template(
                    'student_view.html',
                    playground_id=playground_id,
                    user_id=user_id,
                    role=role
                )
            # Teachers get the teacher view
            elif 'teacher' in role_lower or 'instructor' in role_lower or 'professor' in role_lower:
                return render_template(
                    'teacher_view.html',
                    playground_id=playground_id,
                    user_id=user_id,
                    role=role
                )
        
        # Default fallback: Professors/instructors get the editor
        return render_template(
            'editor.html',
            playground_id=playground_id,
            user_roles=role,
            user_id=user_id,
            app_state=state
        )
    
    # Otherwise render the single-page app with injected state (needs course_id for initialization)
    return render_template(
        'index.html',
        course_id=course_id,
        user_roles=role,
        user_id=user_id,
        app_state=state
    )


@app.route('/analytics/<playground_id>', methods=['GET'])
def analytics_dashboard(playground_id):
    """
    Analytics Dashboard - Professor-only page to view course analytics.
    
    This page shows:
    - Cluster analysis of student queries
    - Topic distribution charts (pie and bar)
    - Sample queries for each cluster
    - Ability to regenerate reports
    """
    
    # Render the analytics dashboard
    return render_template(
        'analytics.html',
        playground_id=playground_id,
    )


@app.route('/student/<playground_id>', methods=['GET'])
def student_view(playground_id):
    """
    Student View - Interactive knowledge graph exploration interface.
    
    Provides a fun, engaging UI for students to:
    - Browse topics in a card-based grid layout
    - Click topics to see detailed summaries in a modal
    - Chat with the AI assistant about course content
    - Access related resources for each topic
    
    This route should be used when the course is ACTIVE and the user is a student.
    """
    # Get user info from session
    user_id = session.get('user_id', 'unknown')
    role = session.get('role', 'student')
    
    # Verify playground is active
    state = firestore_service.get_course_state(playground_id)
    
    if state != 'ACTIVE':
        # Redirect to main launch if not active
        # Note: We don't have course_id here, so redirect to a generic error or use session
        course_id = session.get('course_id')
        return render_template(
            'index.html',
            course_id=course_id,
            user_roles=role,
            user_id=user_id,
            app_state=state
        )
    
    # Render the student view
    return render_template(
        'student_view.html',
        playground_id=playground_id,
        user_id=user_id,
        role=role
    )


@app.route('/api/initialize-course', methods=['POST'])
def initialize_course():
    """
    Kicks off the entire RAG + KG pipeline.
    This is a long-running request triggered by the professor.
    
    Pipeline:
    1. Create Firestore doc with status: GENERATING
    2. Download files from Canvas to local storage
    3. Upload files to Google Cloud Storage (GCS)
    4. Create RAG corpus and import files from GCS
    5. Build knowledge graph using RAG context
    6. Clean up local and GCS files
    7. Finalize Firestore doc with status: ACTIVE
    
    Returns:
        JSON response with status and corpus info
    """
    course_id = None
    try:
        data = request.json
        course_id = data.get('course_id')
        topics = data.get('topics')  # Optional now
        
        return jsonify(initialize_course_from_canvas(course_id, topics))
    except Exception as e:
        logger.error(f"Error initializing course {course_id or 'unknown'}: {str(e)}", exc_info=True)
        
        
        # Try to update Firestore with error status
        try:
            firestore_service.db.collection(firestore_service.COURSES_COLLECTION).document(course_id).update({
                'status': 'ERROR',
                'error_message': str(e)
            })
        except:
            pass
        
        return jsonify({
            "error": "Failed to initialize course",
            "message": str(e)
        }), 500


CITE_THRESHOLD = 0.4
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles student questions using the RAG-powered TA bot.
    """
    try:
        data = request.json
        playground_id = data.get('playground_id')
        query = data.get('query')

        playground_data = firestore_service.get_playground_data(playground_id)
        
        # Convert DocumentSnapshot to dict
        data_dict = playground_data.to_dict()
        corpus_id = data_dict.get('corpus_id')
        
        context = rag_service.retrieve_context(
            corpus_id=corpus_id,
            query=query
        )

        answer, sources  = llm_service.generate_answer(
            query=query,
            context=context
        )
    except Exception as e:
        print(f"[CHAT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "response": f"Sorry, an error occurred: {str(e)}"
        }), 500

    logger.info(f"Logging chat query for playground {playground_id}: {query[:50]}...")
    doc_id = analytics_logging_service.log_chat_query(
        playground_id=playground_id,
        query_text=query,
        answer_text=answer,
        sources=sources
    )

    return jsonify({
        "answer": answer,
        "sources": sorted([source for source in sources if source['distance'] <= CITE_THRESHOLD], key=lambda x: x['distance']),
        "log_doc_id": doc_id,
    })


@app.route('/api/get-graph', methods=['GET'])
def get_graph():
    """
    Fetches the knowledge graph data for visualization.
    """
    playground_id = request.args.get('playground_id')
    if not playground_id:
        return jsonify({"error": "playground_id is required"}), 400
    files_map = firestore_service.get_file_map(playground_id)
    kg_nodes, kg_edges, kg_data = kg_service.render_knowledge_graph(playground_id, files_map)

    return jsonify({
        "nodes": kg_nodes,
        "edges": kg_edges,
        "data": kg_data,
        "indexed_files": files_map
    })


@app.route('/api/init-logs/<course_id>', methods=['GET'])
def get_init_logs(course_id):
    """
    Retrieves initialization logs for a course.
    Used for real-time log display during course initialization.
    """
    try:
        logs = firestore_service.get_init_logs(course_id)
        return jsonify({"logs": logs})
    except Exception as e:
        logger.error(f"Failed to retrieve init logs: {e}")
        return jsonify({"error": str(e), "logs": []}), 500


@app.route('/api/download-source', methods=['GET'])
def download_source():
    """
    Generates a signed URL for downloading a file from GCS.
    """
    gcs_uri = request.args.get('gcs_uri')
    
    if not gcs_uri or not gcs_uri.startswith('gs://'):
        return jsonify({"error": "Invalid GCS URI"}), 400
    
    try:
        # Generate a signed URL that expires in 1 hour
        signed_url = gcs_service.generate_signed_url(gcs_uri, expiration_minutes=60)
        return jsonify({"download_url": signed_url})
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/rate-answer', methods=['POST'])
def rate_answer():
    """
    Allows students to rate (like/dislike) an answer.
    
    Request body:
        {
            "log_doc_id": "abc123",
            "rating": "helpful" | "not_helpful"
        }
    """
    data = request.json
    log_doc_id = data.get('log_doc_id')
    rating = data.get('rating')
    
    if not log_doc_id or not rating:
        return jsonify({
            "error": "Missing required fields: log_doc_id and rating"
        }), 400
    
    if rating not in ['helpful', 'not_helpful']:
        return jsonify({
            "error": "Invalid rating. Must be 'helpful' or 'not_helpful'"
        }), 400
    
    try:
        analytics_logging_service.rate_answer(log_doc_id, rating)
        
        return jsonify({
            "success": True,
            "message": "Rating recorded successfully"
        })
    except Exception as e:
        logger.error(f"Failed to rate answer: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to rate answer",
            "message": str(e)
        }), 500
    

@app.route('/api/generate-quiz-questions', methods=['POST'])
def generate_quiz():
    """
    Generates a quiz based on the provided topic and number of questions.
    Request body:
        {
            "question_groups": [
                {
                    "topic": "abc123",
                    "num_questions": 1,
                    "file_gcs_uris": ["gs://bucket/file1.pdf", "gs://bucket/file2.pdf"],
                    "special_instructions": "optional instructions",
                },
            ]
        }
    """
    data = request.json
    question_groups = data.get('question_groups')
    if not question_groups:
        return jsonify({
            "error": "Missing required field: question_groups"
        }), 400
    
    generated_question_groups = [] 
    for group in question_groups:
        topic = group.get('topic')
        num_questions = group.get('num_questions')
        files = group.get('file_gcs_uris', None)
        special_instructions = group.get('special_instructions', "")
        file_objs = []
        for file_uri in files:
            file_obj = gcs_service.get_file_obj(file_uri)
            file_objs.append(file_obj)

        if not topic or not num_questions or not files:
            return jsonify({
                "error": "Missing required fields: topic, num_questions, and files"
            }), 400
        
        try:
            quiz_data = dukegpt_service.generate_quiz_questions(topic, num_questions, special_instructions, file_objs)
        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}", exc_info=True)
            return jsonify({
                "error": "Failed to generate quiz",
                "message": str(e)
            }), 500
        quiz_data['topic'] = topic
        quiz_data['num_questions'] = num_questions
        quiz_data['special_instructions'] = special_instructions

        generated_question_groups.append(quiz_data)

    return jsonify({
        "question_groups": generated_question_groups
    })


@app.route('/api/create-quiz', methods=['POST'])
def create_quiz():
    """
    Creates a quiz in Canvas based on the provided quiz data.
    
    NOTE: This endpoint requires course_id (not playground_id) because it 
    interfaces directly with the Canvas API which requires the Canvas course ID.
    TODO: Consider adding get_course_id_for_playground() if we need to call this
    from a playground-based context.
    
    Request body:
        {
            "course_id": "12345",  # Canvas course ID required for Canvas API
            "quiz_title": "Sample Quiz",
            "question_groups": {
                // Quiz data structure from /generate-quiz-questions
            }
        }
    """
    data = request.json
    course_id = data.get('course_id')
    quiz_title = data.get('quiz_title')
    question_groups = data.get('question_groups')

    if not course_id or not quiz_title or not question_groups:
        return jsonify({
            "error": "Missing required fields: course_id, quiz_title, and question_groups"
        }), 400

    quiz_questions = []
    for question_group in question_groups:
        questions = question_group.get('questions', [])
        for question in questions:
            quiz_question = Quiz_Question(
                question_type="multiple_choice_question",
                question_text=question.get('question'),
                points_possible=1.0,
                answers=[
                    Quiz_Answer(
                        text=option,
                        weight=100 if idx == question.get('correct_answer') else 0
                    ) for idx, option in enumerate(question.get('options', []))
                ]
            )
            quiz_questions.append(quiz_question)

    
    try:
        quiz_info = canvas_service.create_quiz_draft(
            course_id=course_id,
            title=quiz_title,
            questions=quiz_questions,
            token=CANVAS_TOKEN
        )
        
        return jsonify({
            "success": True,
            "quiz_info": quiz_info
        })
    except Exception as e:
        logger.error(f"Failed to create Canvas quiz: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to create Canvas quiz",
            "message": str(e)
        }), 500

@app.route('/api/remove-topic', methods=['POST'])
def remove_topic():
    """
    Removes a topic from an existing playground knowledge graph.
    
    Request body:
        {
            "playground_id": "abc123",
            "topic_id": "topic_1"
        }
    
    Returns:
        JSON response with updated graph data
    """
    try:
        data = request.json
        playground_id = data.get('playground_id')
        topic_id = data.get('topic_id')
        
        if not playground_id or not topic_id:
            return jsonify({
                "error": "Missing required fields: playground_id and topic_id"
            }), 400

        kg_service.remove_topic_from_graph(
            playground_id=playground_id,
            topic_id=topic_id
        )
        
        return jsonify({
            "status": "success",
            "message": f"Topic '{topic_id}' removed successfully",
        })
        
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return jsonify({
            "error": "Invalid request",
            "message": str(ve)
        }), 400
    except Exception as e:
        logger.error(f"Failed to remove topic: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to remove topic",
            "message": str(e)
        }), 500


@app.route('/api/log-node-click', methods=['POST'])
def log_node_click():
    """
    Logs when a student clicks on a knowledge graph node.
    
    Request body:
        {
            "playground_id": "abc123",
            "node_id": "topic_1",
            "node_label": "Machine Learning",
            "node_type": "topic" | "file"
        }
    """
    data = request.json
    playground_id = data.get('playground_id')
    node_id = data.get('node_id')
    node_label = data.get('node_label')
    node_type = data.get('node_type')
    
    if not playground_id or not node_id or not node_label:
        return jsonify({
            "error": "Missing required fields: playground_id, node_id, node_label"
        }), 400
    
    try:
        doc_id = analytics_logging_service.log_kg_node_click(
            playground_id=playground_id,
            node_id=node_id,
            node_label=node_label,
            node_type=node_type
        )
        
        return jsonify({
            "success": True,
            "log_doc_id": doc_id
        })
    except Exception as e:
        logger.error(f"Failed to log node click: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to log node click",
            "message": str(e)
        }), 500


@app.route('/api/analytics/<playground_id>', methods=['GET'])
def get_analytics(playground_id):
    """
    Retrieves the latest analytics report for a playground.
    
    Returns cluster analysis and insights for professors.
    """
    try:
        from .services import analytics_reporting_service
        
        report = analytics_reporting_service.get_analytics_report(playground_id)
        
        if not report:
            return jsonify({
                "message": "No analytics report available yet. Run analytics first."
            }), 404
        
        return jsonify(report)
    except Exception as e:
        logger.error(f"Failed to get analytics report: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to retrieve analytics report",
            "message": str(e)
        }), 500


@app.route('/api/analytics/run', methods=['POST'])
def run_analytics():
    """
    Triggers analytics processing for a playground (professor-only).
    
    Request body:
        {
            "playground_id": "abc123",
            "n_clusters": 5  // optional, uses elbow method if not specified
        }
    """
    data = request.json
    playground_id = data.get('playground_id')
    n_clusters = data.get('n_clusters')
    
    if not playground_id:
        return jsonify({
            "error": "Missing required field: playground_id"
        }), 400
    
    try:
        from .services import analytics_reporting_service
        
        # Run analytics with auto-detection or specified clusters
        if n_clusters:
            report = analytics_reporting_service.run_daily_analytics(
                playground_id, 
                n_clusters=n_clusters, 
                auto_detect_clusters=False
            )
        else:
            report = analytics_reporting_service.run_daily_analytics(
                playground_id, 
                auto_detect_clusters=True
            )
        
        return jsonify(report)
    except Exception as e:
        logger.error(f"Failed to run analytics: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to run analytics",
            "message": str(e)
        }), 500


@app.route('/api/add-topic', methods=['POST'])
def add_topic():
    """
    Adds a new topic to an existing course knowledge graph.
    
    Request body:
        {
            "playground_id": "abc123",
            "topic_name": "New Topic Name",
            "summary": "Optional custom summary" (optional)
        }
    
    Returns:
        JSON response with updated graph data
    """
    try:
        data = request.json
        playground_id = data.get('playground_id')
        topic_name = data.get('topic_name')
        custom_summary = data.get('summary')  # Optional
        if not playground_id or not topic_name:
            return jsonify({
                "error": "Missing required fields: playground_id and topic_name"
            }), 400
        
        kg_service.add_topic_to_graph(
            playground_id=playground_id,
            topic_name=topic_name,
            summary=custom_summary
        )
        
        return jsonify({
            "status": "success",
            "message": f"Topic '{topic_name}' added successfully"
        })
    except Exception as e:
        logger.error(f"Failed to add topic: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to add topic",
            "message": str(e)
        }), 500


@app.route('/api/playgrounds/<playground_id>/generate-upload-url', methods=['POST'])
def generate_upload_url(playground_id):
    """
    Generates a signed URL for direct-to-GCS file upload.
    This bypasses Cloud Run memory limits by allowing the browser to upload directly.
    
    Request body:
        {
            "filename": "lecture_notes.pdf",
            "content_type": "application/pdf",
            "size": 15000000  // optional, for validation
        }
    
    Returns:
        {
            "file_id": "uuid-generated-id",
            "upload_url": "https://storage.googleapis.com/...",
            "gcs_uri": "gs://bucket/playgrounds/.../uploads/file_id",
            "expires_in": 900  // seconds
        }
    """
    try:
        data = request.json or {}
        filename = data.get('filename', 'unnamed_file')
        content_type = data.get('content_type', 'application/octet-stream')

        # Validate content type against allowed whitelist
        # NOTE: Keep this in sync with the frontend `acceptedFiles` configuration.
        allowed_content_types = {
            "application/pdf",
            "text/plain",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "image/png",
            "image/jpeg",
        }
        if content_type not in allowed_content_types:
            return jsonify({
                "error": "Unsupported content type",
                "message": "The provided content type is not allowed for uploads."
            }), 400
        
        # Validate playground exists
        playground_data = firestore_service.get_playground_data(playground_id)
        if not playground_data.exists:
            return jsonify({
                "error": "Playground not found"
            }), 404
        
        # Generate unique file ID
        file_id = firestore_service.initialize_file(playground_id)
        
        # Generate signed upload URL (15 min expiration)
        result = gcs_service.generate_signed_upload_url(
            playground_id=playground_id,
            file_id=file_id,
            content_type=content_type,
            expiration_minutes=15
        )
        
        return jsonify({
            "file_id": file_id,
            "upload_url": result['upload_url'],
            "gcs_uri": result['gcs_uri'],
            "expires_in": 900,  # 15 minutes in seconds
            "original_filename": filename,
            "content_type": content_type
        })
        
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to generate upload URL",
            "message": str(e)
        }), 500


@app.route('/api/playgrounds/<playground_id>/files/register', methods=['POST'])
def register_uploaded_file(playground_id):
    """
    Registers a file in Firestore after successful GCS upload.
    Called by the frontend after receiving 200 OK from GCS.
    
    Request body:
        {
            "file_id": "uuid-from-generate-url",
            "filename": "original_filename.pdf",
            "content_type": "application/pdf",
            "size": 15000000,
            "gcs_uri": "gs://bucket/playgrounds/.../uploads/file_id"
        }
    
    Returns:
        {
            "success": true,
            "file_id": "firestore-doc-id",
            "status": "uploaded"
        }
    """
    try:
        data = request.json
        file_id = data.get('file_id')
        filename = data.get('filename')
        content_type = data.get('content_type', 'application/octet-stream')
        size = data.get('size', 0)
        gcs_uri = data.get('gcs_uri')
        
        if not file_id or not filename or not gcs_uri:
            return jsonify({
                "error": "Missing required fields: file_id, filename, gcs_uri"
            }), 400
        
        # Verify the file actually exists in GCS
        if not gcs_service.verify_blob_exists(gcs_uri):
            return jsonify({
                "error": "File not found in GCS. Upload may have failed."
            }), 400
        
        # Update blob metadata with display name
        gcs_service.update_blob_metadata(gcs_uri, filename, content_type)
        
        # Create Firestore document for the file
        file_doc = {
            'id': file_id,
            'name': filename,
            'display_name': filename,
            'size': size,
            'content_type': content_type,
            'gcs_uri': gcs_uri,
            'source': {
                'type': 'local_upload',
                'uploaded_at': firestore_service.firestore.SERVER_TIMESTAMP
            },
        }
        
        # Add to Firestore
        firestore_service.register_uploaded_file(playground_id, file_id, file_doc)
        
        logger.info(f"Registered uploaded file: {filename} ({file_id}) for playground {playground_id}")
        
        return jsonify({
            "success": True,
            "file_id": file_id,
            "status": "uploaded",
            "message": f"File '{filename}' registered successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to register uploaded file: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to register file",
            "message": str(e)
        }), 500


@app.route('/api/playgrounds/<playground_id>/files', methods=['GET'])
def list_playground_files(playground_id):
    """
    Lists all files in a playground.
    
    Returns:
        {
            "files": [
                {
                    "id": "file_id",
                    "name": "filename.pdf",
                    "status": "uploaded" | "indexed",
                    ...
                }
            ]
        }
    """
    try:
        files = firestore_service.get_playground_files(playground_id)
        return jsonify({
            "files": files
        })
    except Exception as e:
        logger.error(f"Failed to list playground files: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to list files",
            "message": str(e)
        }), 500