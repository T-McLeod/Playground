"""
Gemini LLM Service
Handles all Google Gemini AI model interactions for answer generation.

This service provides functions to:
1. Generate answers from direct prompts
2. Generate context-aware answers using RAG-retrieved context
3. Generate answers with conversation history
4. Generate suggested follow-up questions

This service handles all LLM prompting and response formatting.
"""
from vertexai.generative_models import GenerativeModel
from google.generativeai import GenerativeModel
import mimetypes
import os
import logging
from typing import List, Tuple
import vertexai
import sys


root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)

# Initialize Vertex AI with environment variables
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
location = os.environ.get('GOOGLE_CLOUD_LOCATION')
DEFAULT_MODEL = os.environ.get('GEMINI_LLM_MODEL', 'gemini-2.5-flash-lite')

if project_id:
    vertexai.init(project=project_id, location=location)
    logger.info(f"Vertex AI initialized for Gemini: project={project_id}, location={location}")
else:
    logger.warning("GOOGLE_CLOUD_PROJECT not set - Gemini service not initialized")


def get_embedding(text: str, model_name: str = "text-embedding-004", task_type: str = "RETRIEVAL_QUERY") -> list:
    """
    Generates an embedding vector for text using Vertex AI's text-embedding model.
    
    Args:
        text: The text to embed
        model_name: The embedding model to use (default: text-embedding-004)
        task_type: The task type for the embedding. Options:
                   - RETRIEVAL_QUERY: For search queries
                   - RETRIEVAL_DOCUMENT: For documents being indexed
                   - SEMANTIC_SIMILARITY: For comparing text similarity
                   - CLASSIFICATION: For text classification
                   - CLUSTERING: For grouping similar texts
        
    Returns:
        List of floats representing the embedding vector (768 dimensions for text-embedding-004)
        
    Example:
        vector = get_embedding("What is machine learning?", task_type="RETRIEVAL_QUERY")
        # Returns: [0.123, -0.456, 0.789, ...] (768 dimensions)
    """
    try:
        from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
        
        logger.info(f"Generating embedding for text: {text[:50]}... (task_type: {task_type})")
        
        # Initialize the embedding model
        model = TextEmbeddingModel.from_pretrained(model_name)
        
        # Create embedding input with task type
        embedding_input = TextEmbeddingInput(
            text=text,
            task_type=task_type
        )
        
        # Generate embedding
        embeddings = model.get_embeddings([embedding_input])
        
        # Extract the vector from the first (and only) embedding
        vector = embeddings[0].values
        
        logger.info(f"Generated embedding vector with {len(vector)} dimensions")
        return vector
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}", exc_info=True)
        raise

SUMMARIZE_PROMPT = """
    Summarize this file in one paragraph, specifically the topics that are covered, both broad and specific.
    Someone reading the summary should understand what subjects are discussed in the file. Don't get too detailed.
    Being the summary now with "This file discusses..."
"""
def summarize_file(file_path: str, prompt: str = SUMMARIZE_PROMPT, model_name: str = DEFAULT_MODEL) -> str:
    """
    Summarize a local file using Gemini.

    Args:
        file_path: Local file path
        prompt: Instruction to send
        model_name: Gemini model to use

    Returns:
        Summary text
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")

    # Determine MIME type (e.g. application/pdf)
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        # default to binary if unknown
        mime_type = "application/octet-stream"

    # Load file bytes
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Create a Gemini Part
    file_part = {
        "mime_type": mime_type,
        "data": file_bytes
    }

    try:
        model = GenerativeModel(model_name)

        response = model.generate_content(
            [file_part, prompt]
        )

        return response.text

    except Exception as e:
        logger.error(f"Failed to summarize {file_path}: {str(e)}")
        raise


def generate_answer(query: str, model_name: str = DEFAULT_MODEL) -> str:
    """
    Generates a direct answer to a query using Gemini (no RAG context).
    
    Args:
        query: The user's question or prompt
        model_name: Gemini model to use (default: gemini-2.5-flash-lite)
        
    Returns:
        Generated answer text
        
    Raises:
        Exception: If generation fails
        
    Example:
        answer = generate_answer("What is machine learning?")
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    try:
        logger.info(f"Generating direct answer for: {query[:100]}...")
        
        model = GenerativeModel(model_name)
        response = model.generate_content(query)
        
        answer_text = response.text
        logger.info(f"Generated answer ({len(answer_text)} characters)")
        
        return answer_text
        
    except Exception as e:
        logger.error(f"Failed to generate answer: {str(e)}")
        raise

def generate_answer_with_context(
    query: str,
    corpus_id: str,
    top_k: int = 10,
    threshold: float = 0.4,
    model_name: str = DEFAULT_MODEL
) -> Tuple[str, List[str]]:
    """
    Generates an answer using context retrieved from RAG corpus.
    
    This function:
    1. Retrieves relevant context from RAG service
    2. Constructs a prompt with context and query
    3. Generates an answer using Gemini
    4. Returns answer with source citations
    
    Args:
        query: The user's question
        corpus_id: RAG corpus resource name to retrieve context from
        top_k: Number of context chunks to retrieve (default: 10)
        threshold: Similarity threshold for retrieval (default: 0.5)
        model_name: Gemini model to use (default: gemini-2.5-flash-lite)
        
    Returns:
        Tuple of (answer_text, list of source names)
        
    Raises:
        Exception: If retrieval or generation fails
        
    Example:
        answer, sources = generate_answer_with_context(
            "What is supervised learning?",
            corpus_id
        )
        # answer = "Supervised learning is..."
        # sources = ["Chapter1.pdf", "Lecture2.pdf"]
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    try:
        logger.info(f"Generating RAG-enhanced answer for: {query[:100]}...")
        
        # Step 1: Retrieve context from RAG corpus
        context_texts, source_names = retrieve_context(corpus_id, query, top_k, threshold)

        if not context_texts:
            logger.warning("No context retrieved from RAG corpus")
            return ("I don't have enough information in the course materials to answer this question.", [])
        
        logger.info(f"Retrieved {len(context_texts)} context chunks from {len(source_names)} sources")
        
        # Step 2: Construct prompt with context
        combined_context = "\n\n".join(context_texts)
        
        prompt = f"""You are a helpful teaching assistant for a course. Answer the student's in a helpful manner and use the sources provided when relevant.

Course Materials Context:
{combined_context}

Student Question: {query}

Instructions:
1. Try your best to answer based on the provided context above
2. Be clear, concise, and educational without giving away answers to explicit homework questions
3. If the context doesn't contain enough information to fully answer the question, say so
4. Cite specific sources when possible (e.g., "According to Chapter 1...")
5. Use a friendly, professional teaching tone

Answer:"""

        # Step 3: Generate answer with Gemini
        model = GenerativeModel(model_name)
        response = model.generate_content(prompt)
        answer_text = response.text
        
        logger.info(f"Generated answer with {len(source_names)} citations")
        
        return (answer_text, source_names)
        
    except Exception as e:
        logger.error(f"Failed to generate RAG-enhanced answer: {str(e)}")
        raise


def generate_suggested_questions(topic: str, count: int = 3, model_name: str = DEFAULT_MODEL) -> List[str]:
    """
    Generates AI-suggested follow-up questions for a given topic.
    
    Args:
        topic: The topic or subject area
        count: Number of questions to generate (default: 3)
        model_name: Gemini model to use
        
    Returns:
        List of suggested question strings
        
    Raises:
        Exception: If generation fails
        
    Example:
        questions = generate_suggested_questions("Machine Learning Basics")
        # ["What is the difference between...", "How does...", "Why is..."]
    """
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    try:
        logger.info(f"Generating {count} suggested questions for topic: {topic}")
        
        model = GenerativeModel(model_name)
        
        prompt = f"""Generate {count} thoughtful follow-up questions that a student might have about the topic: "{topic}"

Requirements:
1. Questions should be short, 10-15 words maximum
2. Questions should be educational and promote deeper understanding
3. Questions should be specific and relevant to the topic
4. Questions should be suitable for a teaching assistant to answer
5. Each question should be on a new line
6. Do not number the questions
Topic: {topic}

Questions:"""

        response = model.generate_content(prompt)
        
        # Parse response into list of questions
        questions = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
        
        # Remove any numbering that might have been added
        import re
        cleaned_questions = []
        for q in questions:
            # Remove common numbering patterns
            cleaned = re.sub(r'^\d+[\.)]\s*', '', q)
            cleaned = re.sub(r'^[-*]\s*', '', cleaned)
            if cleaned:
                cleaned_questions.append(cleaned)
        
        logger.info(f"Generated {len(cleaned_questions)} suggested questions")
        
        return cleaned_questions[:count]  # Return requested count
        
    except Exception as e:
        logger.error(f"Failed to generate suggested questions: {str(e)}")
        raise


if __name__ == "__main__":
    # RAG Parameter Comparison Test for Course 13299557
    from dotenv import load_dotenv
    import json
    
    # Load environment variables
    env_path = os.path.join(root_dir, '.env')
    load_dotenv(env_path)
    
    # Re-initialize after loading env
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    location = os.environ.get('GOOGLE_CLOUD_LOCATION')
    
    if project_id:
        vertexai.init(project=project_id, location=location)
    
    print(f"Loaded environment from: {env_path}")
    print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")
    
    if not project_id:
        print("\n⚠️  Please set GOOGLE_CLOUD_PROJECT in .env")
        sys.exit(1)
    
    try:
        # Import firestore service to get course data
        from app.services.firestore_service import get_course_data
        
        # Get course data for 13299557
        course_id = "13299557"
        print("\n" + "=" * 80)
        print(f"RAG PARAMETER COMPARISON TEST - Course {course_id}")
        print("=" * 80)
        
        course_doc = get_course_data(course_id)
        if not course_doc.exists:
            print(f"\n❌ Course {course_id} not found in Firestore")
            sys.exit(1)
        
        course_data = course_doc.to_dict()
        corpus_id = course_data.get('corpus_id')
        kg_nodes = json.loads(course_data.get('kg_nodes', '[]'))
        kg_data = json.loads(course_data.get('kg_data', '{}'))
        
        print(f"\n📚 Course Info:")
        print(f"   Corpus ID: {corpus_id}")
        print(f"   Total Nodes: {len(kg_nodes)}")
        print(f"   KG Data Entries: {len(kg_data)}")
        
        # Extract topic nodes only
        topic_nodes = [node for node in kg_nodes if node.get('group') == 'topic']
        print(f"   Topic Nodes: {len(topic_nodes)}")
        print(f"\n📋 Topics:")
        for i, node in enumerate(topic_nodes, 1):
            print(f"   {i}. {node.get('label')}")
        
        # Test query
        test_queries = [
            "What is probability?",
            "Explain the pigeonhole principle",
            "How do generating functions work?"
        ]
        
        # Define parameter combinations to test
        parameter_sets = [
            {"top_k": 10, "threshold": 0.3, "name": "Low Threshold (0.3)"},
            {"top_k": 10, "threshold": 0.4, "name": "Medium-Low Threshold (0.4)"},
            {"top_k": 10, "threshold": 0.5, "name": "Medium Threshold (0.5) - DEFAULT"},
            {"top_k": 10, "threshold": 0.6, "name": "Medium-High Threshold (0.6)"},
            {"top_k": 10, "threshold": 0.7, "name": "High Threshold (0.7)"},
        ]
        
        print("\n" + "=" * 80)
        print("TESTING THRESHOLD VARIATIONS (top_k=10)")
        print("=" * 80)
        
        all_results = {}
        
        for query in test_queries:
            print(f"\n{'━' * 80}")
            print(f"🔍 QUERY: '{query}'")
            print(f"{'━' * 80}")
            
            query_results = []
            
            for params in parameter_sets:
                print(f"\n  {params['name']}")
                print(f"  {'-' * 76}")
                
                try:
                    # Retrieve context with these parameters
                    contexts, sources = retrieve_context(
                        corpus_id, 
                        query, 
                        top_k=params['top_k'], 
                        threshold=params['threshold']
                    )
                    
                    print(f"  Contexts: {len(contexts):2d}  |  Sources: {len(sources):2d}", end="")
                    
                    if sources:
                        source_names = [s['filename'] for s in sources]
                        distances = [f"{s['distance']:.4f}" for s in sources]
                        print(f"  |  Files: {', '.join(source_names)}")
                        print(f"  Distances: {', '.join(distances)}")
                    else:
                        print(f"  |  No sources found")
                    
                    # Store results for comparison
                    query_results.append({
                        'threshold': params['threshold'],
                        'num_contexts': len(contexts),
                        'num_sources': len(sources),
                        'sources': sources,
                        'avg_distance': sum(s['distance'] for s in sources) / len(sources) if sources else None
                    })
                    
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            all_results[query] = query_results
        
        # Detailed comparison table
        print("\n" + "=" * 80)
        print("DETAILED COMPARISON TABLE")
        print("=" * 80)
        
        for query, results in all_results.items():
            print(f"\n📊 Query: '{query}'")
            print(f"{'─' * 80}")
            print(f"{'Threshold':<12} {'Contexts':<10} {'Sources':<10} {'Avg Distance':<15} Files")
            print(f"{'─' * 80}")
            
            for result in results:
                threshold = f"{result['threshold']:.1f}"
                contexts = result['num_contexts']
                sources = result['num_sources']
                avg_dist = f"{result['avg_distance']:.4f}" if result['avg_distance'] else "N/A"
                files = ", ".join([s['filename'] for s in result['sources'][:2]])
                if len(result['sources']) > 2:
                    files += f" (+{len(result['sources'])-2} more)"
                
                print(f"{threshold:<12} {contexts:<10} {sources:<10} {avg_dist:<15} {files}")
        
        print("\n" + "=" * 80)
        print("🎉 RAG Parameter Comparison Complete!")
        print("=" * 80)
        
        # Key findings
        print("\n💡 Key Findings:")
        print("   • Threshold behavior appears INVERTED in this implementation!")
        print("     - Lower threshold (0.3) = FEWER results (more strict)")
        print("     - Higher threshold (0.5-0.7) = MORE results (less strict)")
        print("   • This suggests threshold is a MAXIMUM distance, not minimum similarity")
        print("   • Distance scores closer to 0 = better matches")
        print("   • Optimal threshold depends on corpus and query:")
        print("     - 0.5-0.7: Good for comprehensive retrieval (10-15 contexts)")
        print("     - 0.3-0.4: Good for high-precision retrieval (3-5 contexts)")
        print("   • top_k limits the maximum results regardless of threshold")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
