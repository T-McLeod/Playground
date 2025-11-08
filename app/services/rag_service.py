"""
RAG Service
Handles all Vertex AI RAG Engine operations.
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


def query_rag_corpus(corpus_id: str, query: str) -> Tuple[str, List[str]]:
    """
    Queries the RAG corpus and returns an answer with sources.
    
    Args:
        corpus_id: The RAG corpus resource name
        query: The user's question
        
    Returns:
        Tuple of (answer_text, list of source names)
        
    Raises:
        Exception: If query fails
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    try:
        logger.info(f"Querying RAG corpus: {query[:100]}...")
        
        # Retrieve relevant contexts from the corpus
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus_id,
                )
            ],
            text=query,
            similarity_top_k=10,  # Retrieve top 10 relevant chunks
            vector_distance_threshold=0.5,  # Similarity threshold
        )
        
        # Extract context text and citations
        contexts = response.contexts.contexts
        context_texts = [context.text for context in contexts]
        
        # Extract unique source files from source URI
        # Vertex AI RAG stores file names in the source attribute
        citations = []
        for context in contexts:
            # Try to extract filename from source
            if hasattr(context, 'source') and context.source:
                # Source might be in format like "gs://bucket/corpus/file.pdf"
                source_path = context.source.uri if hasattr(context.source, 'uri') else str(context.source)
                filename = source_path.split('/')[-1] if '/' in source_path else source_path
                if filename and filename not in citations:
                    citations.append(filename)
        
        logger.info(f"Retrieved {len(contexts)} context chunks from {len(citations)} sources")
        
        # Generate answer using Gemini with retrieved contexts
        model = GenerativeModel("gemini-1.5-flash")
        
        # Construct prompt with context and query
        combined_context = "\n\n".join(context_texts)
        prompt = f"""You are a helpful teaching assistant for a course. Answer the student's question using ONLY the provided course materials.

Course Materials Context:
{combined_context}

Student Question: {query}

Instructions:
1. Answer based ONLY on the provided context
2. Be clear, concise, and educational
3. If the context doesn't contain enough information, say so
4. Cite specific sources when possible

Answer:"""

        response = model.generate_content(prompt)
        answer_text = response.text
        
        logger.info(f"Generated answer with {len(citations)} citations")
        
        return (answer_text, citations)
        
    except Exception as e:
        logger.error(f"Failed to query RAG corpus: {str(e)}")
        raise


def query_rag_with_history(corpus_id: str, history: List[Dict[str, str]]) -> Tuple[str, List[str]]:
    """
    Queries the RAG corpus with conversational history for context-aware answers.
    
    Args:
        corpus_id: The RAG corpus resource name
        history: List of message dicts with 'role' and 'content' keys
                 e.g., [{'role': 'user', 'content': 'What is...?'}, 
                        {'role': 'assistant', 'content': 'Answer...'}]
        
    Returns:
        Tuple of (answer_text, list of source names)
        
    Raises:
        Exception: If query fails
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    if not history:
        raise ValueError("History cannot be empty")
    
    try:
        # Get the last user message for RAG retrieval
        last_user_message = None
        for msg in reversed(history):
            if msg.get('role') == 'user':
                last_user_message = msg.get('content')
                break
        
        if not last_user_message:
            raise ValueError("No user message found in history")
        
        logger.info(f"Querying with history context: {last_user_message[:100]}...")
        
        # Retrieve relevant contexts based on latest query
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus_id,
                )
            ],
            text=last_user_message,
            similarity_top_k=10,
            vector_distance_threshold=0.5,
        )
        
        # Extract context text and citations
        contexts = response.contexts.contexts
        context_texts = [context.text for context in contexts]
        
        # Extract unique source files from source URI
        citations = []
        for context in contexts:
            # Try to extract filename from source
            if hasattr(context, 'source') and context.source:
                source_path = context.source.uri if hasattr(context.source, 'uri') else str(context.source)
                filename = source_path.split('/')[-1] if '/' in source_path else source_path
                if filename and filename not in citations:
                    citations.append(filename)
        
        logger.info(f"Retrieved {len(contexts)} context chunks from {len(citations)} sources")
        
        # Generate answer using Gemini with full conversation history
        model = GenerativeModel("gemini-1.5-flash")
        
        # Construct prompt with history and context
        combined_context = "\n\n".join(context_texts)
        
        # Build conversation history string
        history_str = ""
        for msg in history[:-1]:  # All messages except the last
            role = "Student" if msg.get('role') == 'user' else "Assistant"
            history_str += f"{role}: {msg.get('content')}\n\n"
        
        prompt = f"""You are a helpful teaching assistant for a course. Answer the student's question using the provided course materials and conversation history.

Course Materials Context:
{combined_context}

Previous Conversation:
{history_str}

Current Student Question: {last_user_message}

Instructions:
1. Consider the conversation history for context
2. Answer based on the provided course materials
3. Be clear, concise, and educational
4. Maintain conversational flow from previous messages
5. If you need to refer back to previous answers, do so naturally

Answer:"""

        response = model.generate_content(prompt)
        answer_text = response.text
        
        logger.info(f"Generated conversational answer with {len(citations)} citations")
        
        return (answer_text, citations)
        
    except Exception as e:
        logger.error(f"Failed to query RAG corpus with history: {str(e)}")
        raise


def get_suggested_questions(topic: str) -> List[str]:
    """
    Generates AI-suggested follow-up questions for a given topic.
    
    Args:
        topic: The topic or subject area
        
    Returns:
        List of suggested question strings
        
    Raises:
        Exception: If question generation fails
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    try:
        logger.info(f"Generating suggested questions for topic: {topic}")
        
        model = GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""Generate 3 thoughtful follow-up questions that a student might have about the topic: "{topic}"

Requirements:
1. Questions should be educational and promote deeper understanding
2. Questions should be specific and relevant to the topic
3. Questions should be suitable for a teaching assistant to answer
4. Each question should be on a new line
5. Do not number the questions

Topic: {topic}

Questions:"""

        response = model.generate_content(prompt)
        
        # Parse response into list of questions
        questions = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
        
        # Remove any numbering that might have been added
        cleaned_questions = []
        for q in questions:
            # Remove common numbering patterns
            cleaned = re.sub(r'^\d+[\.)]\s*', '', q)
            cleaned = re.sub(r'^[-*]\s*', '', cleaned)
            if cleaned:
                cleaned_questions.append(cleaned)
        
        logger.info(f"Generated {len(cleaned_questions)} suggested questions")
        
        return cleaned_questions[:3]  # Return max 3 questions
        
    except Exception as e:
        logger.error(f"Failed to generate suggested questions: {str(e)}")
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

    # Example usage - test with GCS URI
    try:
        mock_file = {
            'id': '319580865',
            'display_name': 'Lec 1.pdf',
            'filename': 'Lec+1.pdf',
            'url': 'https://canvas.instructure.com/files/319580865/download',
            'gcs_uri': 'gs://your-bucket-name/courses/13299557/Lec 1.pdf'  # GCS URI required!
        }

        print("\n⚠️  Note: This test requires the file to exist in GCS first!")
        print(f"Expected GCS URI: {mock_file['gcs_uri']}")
        print("\nTo upload files to GCS, use:")
        print("  from app.services import gcs_service")
        print("  files = gcs_service.upload_course_files(files, course_id)")
        
        # Uncomment to test (requires file in GCS):
        # corpus_name = create_and_provision_corpus([mock_file], "Test Corpus")
        # print(f"\n✅ Corpus created: {corpus_name}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()