import datetime
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
    playground_id = firestore_service.create_playground_doc(f"Canvas Course {course_id}", course_id)
    logger.info(f"Firestore document created for course {course_id}")

    logger.debug("Step 2: Provisioning RAG corpus...")
    corpus_id = rag_service.create_and_provision_corpus(playground_id)
    logger.info(f"RAG corpus provisioned for course {course_id}")

    firestore_service.add_corpus_id(playground_id, corpus_id)

    try:
        files = _intake_files_from_canvas(playground_id, course_id, corpus_id)
    except Exception as e:
        logger.error(f"Failed to intake files from Canvas: {str(e)}")
        raise

    # Step 6: Summarize all files included:
    files = _summarize_files(course_id, files)
    summaries = [file.get("summary", "") for file in files]

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
    kg_service.build_knowledge_graph(
        playground_id=playground_id,
        topic_list=topics,
        corpus_id=corpus_id,
    )
    logger.info("Knowledge graph built successfully")
    
    # Step 9: Finalize Firestore document with all data
    logger.info("Step 9: Finalizing Firestore document...")
    firestore_service.finalize_course_doc(playground_id, {})
    
    logger.info(f"Course {course_id} initialization complete!")
    
    return {
        "status": "complete",
        "corpus_id": corpus_id,
        "files_count": len(files),
    }


def upload_file(playground_id: str, file: dict) -> list[dict]:
    """
    Uploads additional files to an existing RAG corpus and updates the knowledge graph.
    
    Args:
        playground_id: The Playground document ID
        files: List of file objects with 'gcs_uri' property
    Returns:
        List of file objects with summaries added
    """
    file_id = file.get('file_id')
    filename = file.get('filename')
    content_type = file.get('content_type', 'application/octet-stream')
    size = file.get('size', 0)
    gcs_uri = file.get('gcs_uri')
    
    # Verify the file actually exists in GCS
    if not gcs_service.verify_blob_exists(gcs_uri):
        raise ValueError(f"File does not exist in GCS: {gcs_uri}")
    
    # Update blob metadata with display name
    gcs_service.update_blob_metadata(gcs_uri, filename, content_type)
    
    # Create Firestore document for the file
    file_doc = {
        'id': file_id,
        'name': filename,
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

    logger.info(f"Uploading 1 file to playground {playground_id}")
    corpus_id = firestore_service.get_corpus_id(playground_id)
    if not corpus_id:
        raise ValueError(f"No corpus ID found for playground {playground_id}")

    # Step 1: Import files to RAG corpus
    rag_service.add_files_to_corpus(
        corpus_id=corpus_id,
        files=[file],
    )
    logger.info(f"Imported 1 file to RAG corpus {corpus_id}")

    return file


def remove_files(playground_id: str, file_ids: list[str]):
    """
    Removes a file from the RAG corpus and Firestore.
    
    Args:
        playground_id: The Playground document ID
        file_id: The identifier of the file to remove
    """
    corpus_id = firestore_service.get_corpus_id(playground_id)
    if not corpus_id:
        raise ValueError(f"No corpus ID found for playground {playground_id}")

    # Step 1: Remove file from RAG corpus
    rag_service.remove_files_from_corpus(
        corpus_id=corpus_id,
        file_ids=file_ids,
    )
    logger.info(f"Removed files {file_ids} from RAG corpus {corpus_id}")

    # Step 2: delete the file from GCS
    for file_id in file_ids:
        gcs_uri = firestore_service.get_file_by_id(playground_id, file_id)['gcs_uri']
        gcs_service.delete_file(gcs_uri)

    # Step 3: Remove file document from Firestore
    for file_id in file_ids:
        firestore_service.delete_file_document(playground_id, file_id)
        logger.info(f"Removed file document {file_id} from Firestore for playground {playground_id}")


def get_canvas_file_statuses(playground_id: str) -> list[dict]:
    """
    Retrieves the files from the playground's canvas course and checks whether they're up to date.
    
    Args:
        playground_id: The Playground document ID
    Returns:
        list[dict]: Mapping of file IDs to their status, e.g.
        [
            {
                'id': '123456',
                'canvas_id': '67890',
                'name': 'Lecture Notes.pdf',
                'last_updated': '2023-10-01T12:34:56Z',
                'status': 'up_to_date'|'out_of_date'|'missing'
            },
            ...
        ]
    """
    # get course ID from playground
    course_id = firestore_service.get_canvas_course_id(playground_id)

    canvas_source_files = canvas_service.get_course_files(
        course_id=course_id,
        token=CANVAS_TOKEN,
        download=False
    )

    internal_files = firestore_service.get_file_map(playground_id)
    internal_file_map = {f['source']['canvas_file_id']: f for f in internal_files.values() if f.get('source') and f['source'].get('type') == 'canvas'}

    status_files = []

    for canvas_file in canvas_source_files:
        source = canvas_file['source']
        file_id = source['canvas_file_id']
        internal_file = internal_file_map.get(file_id)

        #  string (in ISO 8601 format) -> datetime
        source_date = datetime.datetime.fromisoformat(source.get('updated_at'))
        internal_date = datetime.datetime.fromisoformat(internal_file['source'].get('updated_at')) if internal_file else None

        if not internal_file:
            status = 'missing'
        elif source_date > internal_date:
            status = 'out_of_date'
        else:
            status = 'up_to_date'

        status_files.append({
            'id': internal_file.get('id') if internal_file else None,
            'canvas_id': file_id,
            'name': canvas_file.get('name'),
            'last_updated': source.get('updated_at'),
            'status': status
        })

    return status_files


def refresh_canvas_file(playground_id: str, file_id: str) -> None:
    """
    Refreshes a single Canvas file by re-downloading, uploading to GCS, updating RAG corpus,
    and re-summarizing the file.
    
    Args:
        playground_id: The Playground document ID
        file_id: The Canvas file ID to refresh
    """
    course_id = firestore_service.get_canvas_course_id(playground_id)
    file = firestore_service.get_file_by_id(playground_id, file_id)

    if file is None:
        raise ValueError(f"File with ID {file_id} not found in playground {playground_id}")
    source = file.get("source")
    canvas_file_id = source.get("canvas_file_id")
    if not canvas_file_id:
        raise ValueError(f"File with ID {file_id} is not a Canvas file")

    canvas_file = canvas_service.get_course_file(course_id, canvas_file_id, token=CANVAS_TOKEN)

    remove_files(playground_id, [file_id])
    canvas_file['id'] = file_id 
    uploaded_files = gcs_service.stream_files_to_gcs([canvas_file], playground_id)
    firestore_service.add_files(playground_id, uploaded_files)

    corpus_id = firestore_service.get_corpus_id(playground_id)
    rag_service.add_files_to_corpus(
        corpus_id=corpus_id,
        files=uploaded_files,
    )

def add_canvas_file(playground_id: str, canvas_file_id: str) -> None:
    """
    Adds a new Canvas file to the RAG corpus and Firestore.
    
    Args:
        playground_id: The Playground document ID
        canvas_file_id: The Canvas file ID to add
    """
    course_id = firestore_service.get_canvas_course_id(playground_id)
    canvas_file = canvas_service.get_course_file(course_id, canvas_file_id, token=CANVAS_TOKEN)
    canvas_file['id'] = firestore_service.initialize_file(playground_id)

    uploaded_files = gcs_service.stream_files_to_gcs([canvas_file], playground_id)
    firestore_service.add_files(playground_id, uploaded_files)

    corpus_id = firestore_service.get_corpus_id(playground_id)
    rag_service.add_files_to_corpus(
        corpus_id=corpus_id,
        files=uploaded_files,
    )


def _intake_files_from_canvas(playground_id: str, course_id: str, corpus_id: str) -> list[dict]:
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

    for file in files:
        file['id'] = firestore_service.initialize_file(playground_id)

    logger.debug("Step 4: Uploading files to GCS...")
    files = gcs_service.stream_files_to_gcs(files, playground_id)
    logger.info(f"Uploaded {len(files)} files to GCS")

    firestore_service.add_files(playground_id, files)
    
    logger.debug("Step 5: Importing files from GCS to RAG corpus...")
    rag_service.add_files_to_corpus(
        corpus_id=corpus_id,
        files=files,
    )
    logger.info(f"Uploaded files to corpus: {corpus_id}")

    return files


def _summarize_files(course_id: str, files: list[dict]) -> list[dict]:
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