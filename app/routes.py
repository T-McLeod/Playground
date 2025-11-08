"""
Flask API Routes (ROLE 2: The "API Router")
Handles all HTTP endpoints and connects frontend to core services.
"""
from flask import request, render_template, jsonify, current_app as app
from .services import firestore_service, rag_service, kg_service, canvas_service, gcs_service
import os
import logging

logger = logging.getLogger(__name__)

# Get Canvas API token from environment
CANVAS_TOKEN = os.environ.get('CANVAS_API_TOKEN')


@app.route('/launch', methods=['POST'])
def launch():
    """
    Main LTI entry point from Canvas.
    Determines app state and renders the appropriate UI.
    """
    # Extract LTI parameters
    context_id = request.form.get('context_id')
    roles = request.form.get('roles', '')
    
    # Determine application state
    state = firestore_service.get_course_state(context_id)
    
    # Render the single-page app with injected state
    return render_template(
        'index.html',
        course_id=context_id,
        user_roles=roles,
        app_state=state
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
    try:
        data = request.json
        course_id = data.get('course_id')
        topics = data.get('topics')
        if not topics or not any(t.strip() for t in topics.split(",")):
            return jsonify({"error": "topics is required"}), 400
        topics = topics.split(",")
        
        if not course_id:
            return jsonify({"error": "course_id is required"}), 400
        
        logger.info(f"Starting initialization for course {course_id}")
        
        # Step 1: Create Firestore doc with status: GENERATING
        logger.info("Step 1: Creating Firestore document...")
        firestore_service.create_course_doc(course_id)
        
        # Step 2: Download course files from Canvas (downloads to local storage)
        logger.info("Step 2: Fetching course files from Canvas...")
        files, indexed_files_map = canvas_service.get_course_files(
            course_id=course_id,
            token=CANVAS_TOKEN,
            download=True  # Downloads files locally and adds local_path
        )
        
        if not files:
            logger.warning(f"No files found for course {course_id}")
            return jsonify({"error": "No course files found"}), 404
        
        logger.info(f"Retrieved {len(files)} files from Canvas")
        
        # Step 3: Upload files to Google Cloud Storage (GCS)
        logger.info("Step 3: Uploading files to Google Cloud Storage...")
        files = gcs_service.upload_course_files(files, course_id)
        
        # Count successful uploads
        successful_uploads = sum(1 for f in files if f.get('gcs_uri'))
        logger.info(f"Uploaded {successful_uploads}/{len(files)} files to GCS")
        
        # Step 4: Create RAG corpus and import files from GCS
        logger.info("Step 4: Creating RAG corpus and importing files...")
        corpus_id = rag_service.create_and_provision_corpus(
            files=files,
            corpus_name_suffix=f"Course {course_id}"
        )
        logger.info(f"Created corpus: {corpus_id}")
        
        # Step 5: Build knowledge graph
        logger.info("Step 5: Building knowledge graph...")
        kg_nodes, kg_edges, kg_data = kg_service.build_knowledge_graph(
            topic_list=topics,
            corpus_id=corpus_id,
            files=files
        )
        logger.info("Knowledge graph built successfully")
        
        # Step 6: Clean up local files
        logger.info("Step 6: Cleaning up local files...")
        local_dir = os.path.join('app', 'data', 'courses', course_id)
        if os.path.exists(local_dir):
            import shutil
            shutil.rmtree(local_dir)
            logger.info(f"Deleted local directory: {local_dir}")
        
        # Step 7: Clean up GCS files (optional - comment out if you want to keep them)
        logger.info("Step 7: Cleaning up GCS files...")
        gcs_service.delete_course_files(course_id)
        logger.info("GCS files deleted")
        
        # Step 8: Finalize Firestore document with all data
        logger.info("Step 8: Finalizing Firestore document...")
        update_payload = {
            'corpus_id': corpus_id,
            'indexed_files': indexed_files_map,
            'kg_nodes': kg_nodes,
            'kg_edges': kg_edges,
            'kg_data': kg_data
        }
        firestore_service.finalize_course_doc(course_id, update_payload)
        
        logger.info(f"Course {course_id} initialization complete!")
        
        return jsonify({
            "status": "complete",
            "corpus_id": corpus_id,
            "files_count": len(files),
            "uploaded_count": successful_uploads
        })
        
    except Exception as e:
        logger.error(f"Error initializing course {course_id}: {str(e)}", exc_info=True)
        
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
