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
    threshold: float = 0.5,
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
    # Test the Gemini service
    from dotenv import load_dotenv
    
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
        # Test 1: Direct query
        print("\n" + "=" * 70)
        print("TEST 1: Direct Query (No RAG)")
        print("=" * 70)
        
        query = "What is machine learning?"
        print(f"\nQuery: {query}")
        
        answer = generate_answer(query)
        print(f"\n✅ Answer:\n{answer}")
        
        # Test 2: Suggested questions
        print("\n" + "=" * 70)
        print("TEST 2: Suggested Questions")
        print("=" * 70)
        
        topic = "Supervised Learning"
        print(f"\nTopic: {topic}")
        
        questions = generate_suggested_questions(topic)
        print(f"\n✅ Generated {len(questions)} questions:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
        
        # Test 3: RAG-enhanced query (requires corpus)
        print("\n" + "=" * 70)
        print("TEST 3: RAG-Enhanced Query")
        print("=" * 70)
        corpus_id = "<CORPUS_ID>"
        query = "What is the addition rule?"
        answer, sources = generate_answer_with_context(query, corpus_id)
        print(f"\n✅ Answer:\n{answer}")
        print(f"\n✅ Sources:\n{sources}")
        print("\n🎉 Gemini service tests complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
