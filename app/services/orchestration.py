from app.models.canvas_models import Quiz_Answer, Quiz_Question
from .llm_services import get_llm_service
from .rag_services import get_rag_service
from . import firestore_service, kg_service, canvas_service, gcs_service, analytics_logging_service, analytics_reporting_service
import os
import logging
import shutil
import json

CANVAS_TOKEN = os.environ.get('CANVAS_API_TOKEN')
llm_service = get_llm_service()
rag_service = get_rag_service()

logger = logging.getLogger(__name__)

def initialize_course_from_canvas(course_id: str, topics: list[str] = []) -> dict:
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
    logger.info(f"Starting initialization for course {course_id}")
    # Step 1: Create Firestore doc with status: GENERATING
    logger.debug("Step 1: Creating Firestore document...")
    firestore_service.create_course_doc(course_id)
    logger.info(f"Firestore document created for course {course_id}")
    
    # Step 2: Download course files from Canvas (downloads to local storage)
    logger.debug("Step 2: Fetching course files from Canvas...")
    files, indexed_files_map = canvas_service.get_course_files(
        course_id=course_id,
        token=CANVAS_TOKEN,
        download=True  # Downloads files locally and adds local_path
    )
    logger.info(f"Retrieved {len(files)} files from Canvas")
    
    # Step 3: Upload files to Google Cloud Storage (GCS)
    logger.debug("Step 3: Uploading files to Google Cloud Storage...")
    files = gcs_service.upload_course_files(files, course_id)
    for file in files:
        file_id = str(file.get('id'))
        if file_id in indexed_files_map and file.get('gcs_uri'):
            indexed_files_map[file_id]['gcs_uri'] = file.get('gcs_uri')
            indexed_files_map[file_id]['display_name'] = file.get('display_name')
    # Count successful uploads
    successful_uploads = sum(1 for f in files if f.get('gcs_uri'))
    logger.info(f"Uploaded {successful_uploads}/{len(files)} files to GCS")
    
    # Step 4: Create RAG corpus and import files from GCS
    logger.debug("Step 4: Creating RAG corpus and importing files...")
    corpus_id = rag_service.create_and_provision_corpus(
        files=files,
        corpus_name_suffix=f"Course_{course_id}"
    )
    logger.info(f"Created corpus: {corpus_id}")

    # Step 4.3: Summarize all files included:
    file_to_summary = {}
    files_processed = 0

    for file in files:
        local_path = file.get("local_path")
        display_name = file.get("display_name") or f"file_{file.get('id')}"

        # Skip if no local path
        if not local_path:
            logger.info(f"Could not locate file path for {display_name}")
            continue

        summary = llm_service.summarize_file(
            file_path=local_path,
        )

        file_to_summary[display_name] = summary
        files_processed += 1
        logger.info(f"File Name: {display_name}\nSummary: {summary}")


    # Step 4.5: Extract Topics from summaries, autogenerate topics if not provided:
    summaries = file_to_summary.values()
    logger.info(f"topics: {topics}")
    if not topics or not any(t.strip() for t in topics.split(",")):
        logger.info("No topics provided, auto-extracting generating topics from files")
        topics = kg_service.extract_topics_from_summaries(summaries)
        logger.info(f"Auto-extracted topics: {topics}")
    else:
        topics = topics.split(",")
    
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
        shutil.rmtree(local_dir)
        logger.info(f"Deleted local directory: {local_dir}")
    
    # Step 7: Keep GCS files for future use (no cleanup)
    logger.info("Step 7: GCS files retained for source downloads")
    
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
    
    return {
        "status": "complete",
        "corpus_id": corpus_id,
        "files_count": len(files),
        "uploaded_count": successful_uploads,
        "kg_nodes": kg_nodes,
        "kg_edges": kg_edges,
        "kg_data": kg_data
    }

    