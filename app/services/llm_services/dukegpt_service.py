from io import BytesIO
import os
from typing import List
from flask import json
from openai import OpenAI
from pypdf import PdfReader
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.gcs_service import get_file_obj


MODEL_ID = os.getenv("DUKE_GPT_MODEL_ID")
DUKE_GPT_TOKEN = os.getenv("DUKE_GPT_TOKEN")
DUKE_GPT_API_BASE_URL = os.getenv("DUKE_GPT_API_BASE_URL")

# Initialize OpenAI client with appropriate credentials
client = OpenAI(
    api_key=DUKE_GPT_TOKEN,
    base_url=DUKE_GPT_API_BASE_URL,
)

def parse_file_content(file_content: BytesIO) -> List[str]:
    """
    Parses the content of a file and splits it into manageable chunks.
    """
    file_content.seek(0)
    reader = PdfReader(file_content)
    
    full_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)
    text = "\n".join(full_text)
    return text

QUIZ_SYSTEM_MESSAGE = """
You are a helpful assistant that creates quiz questions.
You will be provided a topic and some content to base the questions on. Students should be able to answer the questions using only the provided content.
Given the provided content, generate quiz questions in the following JSON format:
{
  "questions": [
    {
      "question": "What is the capital of France?",
      "options": ["London", "Berlin", "Paris", "Madrid"],
      "correct_answer": 2
    }
  ]
}
Each question should have four options, and the correct_answer should be the index (0-based) of the correct option.
You should only provide the JSON response without any additional text.
"""
def generate_quiz_questions(topic: str, num_questions: int, special_instructions: str = "", files: List[bytes] = []) -> str:
    """
    Generates quiz questions based on the provided instruction.
    """
    files_content = []
    for file_content in files:
        files_content.append(parse_file_content(file_content))

    prompt = f"Generate {num_questions} quiz questions for the topic {topic} based on the following content:\n" + "--NEW FILE--\n".join(files_content)
    
    resp = get_llm_response(
        req=prompt,
        system_msg=QUIZ_SYSTEM_MESSAGE,
        temperature=0.5
    )

    try:
        json_output = json.loads(resp)
    except Exception as e:
        return f"Error parsing JSON response: {e}\nResponse was: {resp}"

    return json_output


def get_llm_response(req: str, system_msg: str = "", temperature: float = 0.7) -> str:
    """
    Chat using LLM proxy. Uses the Responses API.
    """

    resp = client.responses.create(
        model=MODEL_ID,
        instructions=system_msg,
        input=req,
        temperature=temperature,
    )

    try:
        return resp.output[0].content[0].text
    except Exception as e:
        return f"Error extracting reply: {e}"
    


if __name__ == "__main__":    # Example usage
    topic = "Combinatorics"
    num_questions = 3
    files = [get_file_obj("gs://canvas_files-1/courses/13299557/Lec 1.pdf")]

    quiz_questions = generate_quiz_questions(topic, num_questions, files=files)
    print(quiz_questions)