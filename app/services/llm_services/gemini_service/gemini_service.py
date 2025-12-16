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
from vertexai.generative_models import GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import mimetypes
import os
import logging
from typing import List, Tuple
import vertexai
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.interfaces.llm_interface import LLMInterface
from app.services.rag_service import retrieve_context
from app.prompt_loader import PromptManager

logger = logging.getLogger(__name__)
prompts = PromptManager(__file__)

# Initialize Vertex AI with environment variables
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
location = os.environ.get('GOOGLE_CLOUD_LOCATION')
DEFAULT_MODEL = os.environ.get('GEMINI_LLM_MODEL', 'gemini-2.5-flash-lite')


class GeminiService(LLMInterface):
    def generate_text(self, prompt: str, model_name: str = DEFAULT_MODEL) -> str:
        try:
            logger.info(f"Generating direct answer for: {prompt[:100]}...")
            
            model = GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            answer_text = response.text
            
            return answer_text
        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}")
            raise

    def generate_answer(self, query: list, context: Tuple[List[str], List[str]] = ([], []), model_name: str = DEFAULT_MODEL) -> Tuple[str, List[str]]:
        try:
            logger.info(f"Generating RAG-enhanced answer for: {query[:100]}...") 

            context_texts, source_names = context

            prompt = prompts.render(
                "rag_answer",
                context=context_texts,
                query=query
            )

            model = GenerativeModel(model_name)
            response = model.generate_content(prompt)
            answer_text = response.text
            
            logger.info(f"Generated answer with {len(source_names)} citations")
            
            return (answer_text, source_names)
            
        except Exception as e:
            logger.error(f"Failed to generate RAG-enhanced answer: {str(e)}")
            raise


    def summarize_file(self, file_path: str, model_name: str = "") -> str:
        """
        Summarize a local file using Gemini.

        Args:
            file_path: Local file path
            model_name: Gemini model to use

        Returns:
            Summary text
        """

        # Determine MIME type (e.g. application/pdf)
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream" # default to binary if unknown

        # Load file bytes
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Create a Gemini Part
        file_part = Part.from_data(data=file_bytes, mime_type=mime_type)

        prompt = prompts.render("summarize_file")

        try:
            model = GenerativeModel(model_name)

            response = model.generate_content(
                [file_part, prompt]
            )

            return response.text

        except Exception as e:
            logger.error(f"Failed to summarize {file_path}: {str(e)}")
            raise

    def generate_suggested_questions(self, topic: str, count: int = 3, model_name: str = "") -> list:
        raise NotImplementedError()