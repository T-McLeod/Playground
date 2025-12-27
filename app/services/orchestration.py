from typing import Dict
from .llm_services import get_llm_service
from .rag_services import get_rag_service
from . import firestore_service, kg_service, canvas_service, gcs_service
import os
import logging

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
    2. Create RAG corpus
    3. Fetch files from Canvas to download url
    4. Upload files to Google Cloud Storage (GCS)
    5. Import files from GCS to RAG corpus
    6. Summarize each file using LLM
    7. Extract topics from summaries (if not provided)
    8. Build knowledge graph using RAG context
    9. Finalize Firestore doc with status: ACTIVE
    
    Returns:
        JSON response with status and corpus info
    """
    logger.info(f"Starting initialization for course {course_id}")
    rollback_actions = []

    # Step 1: Create Firestore doc with status: GENERATING
    logger.debug("Step 1: Creating Firestore document...")
    firestore_service.create_course_doc(course_id)
    logger.info(f"Firestore document created for course {course_id}")

    logger.debug("Step 2: Provisioning RAG corpus...")
    corpus_id = rag_service.create_and_provision_corpus(course_id)
    logger.info(f"RAG corpus provisioned for course {course_id}")

    firestore_service.add_corpus_id(course_id, corpus_id)

    try:
        files = _intake_files_from_canvas(course_id, corpus_id)
    except Exception as e:
        logger.error(f"Failed to intake files from Canvas: {str(e)}")
        raise

    # Step 6: Summarize all files included:
    files = _summarize_files(course_id, list(files.values()))
    summaries = [file.get("summary", "") for file in files]
    firestore_service.add_files(course_id, files)

    # Step 7: Extract Topics from summaries, autogenerate topics if not provided:
    logger.info(f"topics: {topics}")
    if not topics or not any(t.strip() for t in topics.split(",")):
        logger.info("No topics provided, auto-extracting generating topics from files")
        topics = kg_service.extract_topics_from_summaries(summaries)
        logger.info(f"Auto-extracted topics: {topics}")
    else:
        topics = topics.split(",")
    
    # Step 8: Build knowledge graph
    logger.info("Step 8: Building knowledge graph...")
    kg_nodes, kg_edges, kg_data = kg_service.build_knowledge_graph(
        topic_list=topics,
        corpus_id=corpus_id,
        files=files
    )
    logger.info("Knowledge graph built successfully")
    
    # Step 9: Finalize Firestore document with all data
    logger.info("Step 9: Finalizing Firestore document...")
    update_payload = {
        'corpus_id': corpus_id,
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
        "kg_nodes": kg_nodes,
        "kg_edges": kg_edges,
        "kg_data": kg_data
    }
    

def _intake_files_from_canvas(course_id: str, corpus_id: str) -> Dict[str, Dict]:
    """
    Intake files from Canvas, upload to GCS, and return a mapping of file identifiers
    to updated file objects with GCS URIs.
    
    Args:
        course_id: The Canvas course ID.
        corpus_id: The RAG corpus ID to which the files will be added.

    Returns:
        Dict[str, Dict]: Mapping of file identifiers to file metadata dictionaries with
        the 'gcs_uri' property added.
    """
    logger.debug("Step 3: Fetching course files from Canvas...")
    files = canvas_service.get_course_files(
        course_id=course_id,
        token=CANVAS_TOKEN,
        download=False
    )
    logger.info(f"Retrieved {len(files)} files from Canvas")

    logger.debug("Step 4: Uploading files to GCS...")
    files = gcs_service.stream_files_to_gcs(files, course_id)
    logger.info(f"Uploaded {len(files)} files to GCS")
    
    logger.debug("Step 5: Importing files from GCS to RAG corpus...")
    rag_service.add_files_to_corpus(
        corpus_id=corpus_id,
        files=files,
    )
    logger.info(f"Uploaded files to corpus: {corpus_id}")

    firestore_service.add_files(course_id, files)
    return files


def _summarize_files(course_id: str, files: list[dict]) -> dict:
    """
    Summarizes a list of files using the LLM service.
    
    Args:
        files: List of file objects with a 'gcs_uri' property pointing to the file in GCS

    Returns:
        List of file objects with a 'summary' field added for each file
    """
    for file in files:
        display_name = file.get("display_name") or f"file_{file.get('id')}"
        gcs_uri = file.get("gcs_uri")

        summary = llm_service.summarize_file(
            file_path=gcs_uri,
        )

        file["summary"] = summary
        logger.debug(f"File Name: {display_name}\nSummary: {summary}")

    return files