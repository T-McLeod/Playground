import vertexai
from vertexai.preview import rag
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import os
import logging
from typing import List, Tuple, Dict
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.interfaces.rag_interface import RAGInterface


logger = logging.getLogger(__name__)

# Initialize Vertex AI with environment variables
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
location = os.environ.get('GOOGLE_CLOUD_LOCATION')

if project_id:
    vertexai.init(project=project_id, location=location)
    logger.info(f"Vertex AI initialized: project={project_id}, location={location}")
else:
    logger.warning("GOOGLE_CLOUD_PROJECT not set - Vertex AI not initialized")

class VertexRAGService(RAGInterface):
    """
    Service for managing RAG corpora and retrieving context using Vertex AI.
    """
    def create_and_provision_corpus(self, corpus_name_suffix):
        try:
            # Create a new RAG corpus
            logger.info("Creating new RAG corpus...")
            corpus_display_name = f"Canvas Course Corpus {corpus_name_suffix}"
            if corpus_name_suffix:
                corpus_display_name += f" ({corpus_name_suffix})"
            
            corpus = rag.create_corpus(display_name=corpus_display_name)
            corpus_name = corpus.name
            logger.info(f"Created corpus: {corpus_name}")
        except Exception as e:
            logger.error(f"Failed to create and provision corpus: {str(e)}")
            raise

        return corpus_name
    

    def retrieve_context(self, corpus_id: str, query: str, top_k: int = 10, threshold: float = 0.5) -> Tuple[List[str], List[Dict]]:
        """
        Retrieves relevant context chunks from the RAG corpus using vector similarity search.
        Does NOT generate answers - only returns raw context for use by other services.
        
        Args:
            corpus_id: The RAG corpus resource name
            query: The search query text
            top_k: Number of most relevant chunks to retrieve (default: 10)
            threshold: Similarity threshold for filtering results (default: 0.5)"""
        logger.info(f"Retrieving context from RAG corpus: {query[:100]}...")
        try:
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
        except Exception as e:
            logger.error(f"Failed to retrieve context from RAG corpus: {str(e)}")
            raise
        
        # Extract unique source files from source URI
        source_ids = set()
        sources = []
        for context in contexts:
            if hasattr(context, 'source_uri') and context.source_uri:
                source_path = context.source_uri
                file_id = source_path.split('/')[-1] if '/' in source_path else source_path
                if file_id and file_id not in source_ids:
                    source_ids.add(file_id)
                    sources.append({
                        'file_id': file_id,
                        'source_uri': context.source_uri,
                        'distance': context.distance
                    })
            else:
                logger.warning("Context chunk missing source_uri attribute")
        
        logger.info(f"Retrieved {len(context_texts)} context chunks from {len(sources)} sources")
        
        return (context_texts, sources)
    

    # Initialize the embedding model
    embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    def get_query_embedding(self, text: str) -> list:
        """
        Generates a query retrieval embedding vector for text using Vertex AI's text-embedding model.
        
        Args:
            text: The text to embed
            model_name: The embedding model to use (default: text-embedding-004)
            
        Returns:
            List of floats representing the embedding vector (768 dimensions for text-embedding-004)
        """
        try:
            logger.info(f"Generating embedding for text: {text[:50]}...")
            
            # Create embedding input with task type
            embedding_input = TextEmbeddingInput(
                text=text,
                task_type="RETRIEVAL_QUERY"
            )
            
            embeddings = self.embedding_model.get_embeddings([embedding_input])
            vector = embeddings[0].values
            
            logger.info(f"Generated embedding vector with {len(vector)} dimensions")
            return vector
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            raise

    def add_files_to_corpus(self, corpus_id: str, files: List[Dict]):
        valid_uris = []
        for file in files:
            gcs_uri = file.get('gcs_uri', None)
            display_name = file.get('display_name', 'unknown')
            
            # Skip files that weren't uploaded to GCS
            if not gcs_uri or not gcs_uri.startswith('gs://'):
                logger.warning(f"Invalid GCS URI for file {display_name}: {gcs_uri}, skipping")
                continue
            
            valid_uris.append(gcs_uri)
            logger.info(f"Queueing file for import: {display_name} (URI: {gcs_uri})")

        if not valid_uris:
            logger.warning("No valid GCS URIs found to import.")
            return corpus_id

        try:
            logger.info(f"Starting import of {len(valid_uris)} files to corpus {corpus_id}...")

            response = rag.import_files(
                corpus_name=corpus_id,
                paths=valid_uris,
                chunk_size=512,  # Optimal chunk size for retrieval
                chunk_overlap=100,  # Overlap for context continuity
            )
            
            logger.info(f"Import operation complete. Response: {response}")
            
            if response.failed_rag_files_count > 0:
                logger.error(f"Failed to import {response.failed_rag_files_count} files. Check Vertex AI Service Agent permissions on GCS bucket.")

            logger.info(f"Corpus provisioning complete: {corpus_id} ({len(valid_uris)} files processed)")
            
        except Exception as e:
            logger.error(f"Failed to import files to corpus {corpus_id}: {str(e)}")
            raise

        return corpus_id

    def remove_files_from_corpus(self, corpus_id: str, file_ids: List[str]):
        raise NotImplementedError("RAGInterface.remove_files_from_corpus is not implemented in VertexRAGService.")  #TODO: Implement if needed
    

    def delete_corpus(self, corpus_id: str):
        """
        Deletes the specified RAG corpus.
        
        Args:
            corpus_id: The RAG corpus resource name to delete
        """
        try:
            rag.delete_corpus(corpus_name=corpus_id)
            logger.info(f"Deleted RAG corpus: {corpus_id}")
        except Exception as e:
            logger.error(f"Failed to delete RAG corpus {corpus_id}: {str(e)}")
            raise