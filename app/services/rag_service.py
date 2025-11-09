"""
RAG Service
Handles Vertex AI RAG Engine operations for context retrieval.

This service provides functions to:
1. Create and provision RAG corpus from GCS files
2. Retrieve relevant context chunks using vector similarity search
3. Extract source citations from retrieved context

Note: This service does NOT generate answers. It only retrieves context.
Answer generation should be handled by a separate LLM service.
"""
import vertexai
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel
import os
import logging
import re
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

# Initialize Vertex AI with environment variables
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
location = os.environ.get('GOOGLE_CLOUD_LOCATION')

if project_id:
    vertexai.init(project=project_id, location=location)
    logger.info(f"Vertex AI initialized: project={project_id}, location={location}")
else:
    logger.warning("GOOGLE_CLOUD_PROJECT not set - Vertex AI not initialized")


def create_and_provision_corpus(files: List[Dict], corpus_name_suffix: str = "") -> str:
    """
    Creates a new RAG corpus and uploads files from Google Cloud Storage.
    
    Args:
        files: List of file objects from Canvas service (each with 'gcs_uri' key)
               e.g., [{'id': '456', 'display_name': 'file.pdf', 'gcs_uri': 'gs://bucket/courses/123/file.pdf'}, ...]
        corpus_name_suffix: Optional suffix for corpus display name
        
    Returns:
        The corpus resource name (string) e.g., "projects/.../ragCorpora/..."
        
    Raises:
        Exception: If corpus creation or file upload fails
        
    Example:
        # Step 1: Get files from Canvas (downloads locally)
        files, _ = canvas_service.get_course_files(course_id, token)
        
        # Step 2: Upload to GCS
        files = gcs_service.upload_course_files(files, course_id)
        
        # Step 3: Create RAG corpus from GCS files
        corpus_name = create_and_provision_corpus(files, f"Course {course_id}")
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    try:
        # Create a new RAG corpus
        logger.info("Creating new RAG corpus...")
        corpus_display_name = f"Canvas Course Corpus - {len(files)} files"
        if corpus_name_suffix:
            corpus_display_name += f" ({corpus_name_suffix})"
        
        corpus = rag.create_corpus(display_name=corpus_display_name)
        corpus_name = corpus.name
        logger.info(f"Created corpus: {corpus_name}")
        
        # Upload each file to the corpus from GCS
        upload_count = 0
        for file in files:
            try:
                gcs_uri = file.get('gcs_uri')
                file_id = file.get('id')
                display_name = file.get('display_name', 'unknown')
                
                # Skip files that weren't uploaded to GCS
                if not gcs_uri:
                    logger.warning(f"No GCS URI for file: {display_name} (ID: {file_id}), skipping")
                    continue
                
                # Validate GCS URI format
                if not gcs_uri.startswith('gs://'):
                    logger.warning(f"Invalid GCS URI for file {display_name}: {gcs_uri}, skipping")
                    continue
                
                logger.info(f"Importing file from GCS: {display_name} (ID: {file_id})")
                logger.info(f"  GCS URI: {gcs_uri}")
                
                # Import file to RAG corpus from GCS
                # Note: Vertex AI RAG automatically indexes the content
                rag.import_files(
                    corpus_name=corpus_name,
                    paths=[gcs_uri],  # Use GCS URI instead of local path
                    chunk_size=512,  # Optimal chunk size for retrieval
                    chunk_overlap=100  # Overlap for context continuity
                )
                
                upload_count += 1
                logger.info(f"✅ Successfully imported: {display_name}")
                
            except Exception as e:
                logger.error(f"Failed to import file {file.get('display_name')}: {str(e)}")
                # Continue with other files even if one fails
                continue
        
        logger.info(f"Corpus provisioning complete: {corpus_name} ({upload_count}/{len(files)} files uploaded)")
        return corpus_name
        
    except Exception as e:
        logger.error(f"Failed to create and provision corpus: {str(e)}")
        raise


def retrieve_context(corpus_id: str, query: str, top_k: int = 10, threshold: float = 0.5) -> Tuple[List[str], Dict]:
    """
    Retrieves relevant context chunks from the RAG corpus using vector similarity search.
    Does NOT generate answers - only returns raw context for use by other services.
    
    Args:
        corpus_id: The RAG corpus resource name
        query: The search query text
        top_k: Number of most relevant chunks to retrieve (default: 10)
        threshold: Similarity threshold for filtering results (default: 0.5)
        
    Returns:
        Tuple of (context_texts, source_names):
        - context_texts: List of relevant text chunks from the corpus
        - source_names: List of unique source file names
        
    Raises:
        Exception: If retrieval fails
        
    Example:
        contexts, sources = retrieve_context(corpus_name, "What is machine learning?")
        # contexts = ["Machine learning is...", "ML involves..."]
        # sources = ["Chapter1.pdf", "Lecture2.pdf"]
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    try:
        logger.info(f"Retrieving context from RAG corpus: {query[:100]}...")
        
        # Retrieve relevant contexts from the corpus using vector search
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus_id,
                )
            ],
            text=query,
            similarity_top_k=top_k,
            vector_distance_threshold=threshold,
        )
        
        # Extract context text chunks
        contexts = response.contexts.contexts
        context_texts = [context.text for context in contexts]
        
        # Extract unique source files from source URI
        source_names = set()
        sources = []
        for context in contexts:
            if hasattr(context, 'source_uri') and context.source_uri:
                # Source is in format like "gs://bucket/corpus/file.pdf"
                source_path = context.source_uri
                filename = source_path.split('/')[-1] if '/' in source_path else source_path
                if filename and filename not in source_names:
                    source_names.add(filename)
                    sources.append({
                        'filename': filename,
                        'source_uri': context.source_uri,
                        'distance': context.distance
                    })
        
        logger.info(f"Retrieved {len(context_texts)} context chunks from {len(sources)} sources")
        
        return (context_texts, sources)
        
    except Exception as e:
        logger.error(f"Failed to retrieve context from RAG corpus: {str(e)}")
        raise


if __name__ == "__main__":
    # Load environment variables from root .env file
    from dotenv import load_dotenv
    
    # Get the root directory (2 levels up from this file)
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(root_dir, '.env')
    
    # Load environment variables from root .env
    load_dotenv(env_path)

    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    location = os.environ.get('GOOGLE_CLOUD_LOCATION')

    logger.info(f"GOOGLE_CLOUD_LOCATION: {location}")

    vertexai.init(project=project_id, location=location)

    # Example usage - test context retrieval
    try:
        mock_file = {
            'id': '319580865',
            'display_name': 'Lec 1.pdf',
            'filename': 'Lec+1.pdf',
            'url': 'https://canvas.instructure.com/files/319580865/download?download_frd=1&verifier=hPXvy0owVxSkEZ7paw1TVZLD5mrXWcTBvGF4KK1A',
            'html_url': 'https://canvas.instructure.com/files/319580865/download?download_frd=1&verifier=hPXvy0owVxSkEZ7paw1TVZLD5mrXWcTBvGF4KK1A',
            'content_type': 'application/pdf',
            'size': 153935,
            'created_at': '2025-11-07T05:39:33Z',
            'updated_at': '2025-11-07T05:39:33Z',
            'local_path': os.path.join(root_dir, 'app', 'data', 'courses', '13299557', 'Lec 1.pdf'),
            'gcs_uri': 'gs://gen-lang-client-0696883642-canvas-files/courses/13299557/Lec 1.pdf'
        }

        print(f"Expected GCS URI: {mock_file['gcs_uri']}")
        
        # Test corpus creation
        # Create and provision a new corpus for testing. This may take some time and incur costs.
        corpus_name = create_and_provision_corpus([mock_file], "Test Corpus")
        print(f"\n✅ Corpus created: {corpus_name}")

        # Test context retrieval (no answer generation)
        test_query = "What is the product rule?"
        print(f"\nRetrieving context for: {test_query}")
        
        contexts, sources = retrieve_context(corpus_name, test_query)
        
        print(f"\n✅ Retrieved {len(contexts)} context chunks from {len(sources)} sources")
        print(f"\nSources: {', '.join(sources)}")
        print(f"\nFirst context chunk (preview):")
        for ctx in contexts[:1]:
            print(f"{ctx}...")  # Print first 500 characters of first context
        
        print("\n📝 Note: This service only retrieves context.")
        print("   Answer generation should be handled by a separate LLM service.")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()