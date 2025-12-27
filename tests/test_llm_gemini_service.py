import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
print(sys.path[0])
from app.services.llm_services.gemini_service.gemini_service import GeminiService

class TestGeminiService(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_LOCATION": "us-central1",
            "GEMINI_LLM_MODEL": "gemini-pro-test"
        })
        self.env_patcher.start()
        
        # We use the real PromptManager to test template integration
        self.service = GeminiService()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('app.services.llm_services.gemini_service.gemini_service.GenerativeModel')
    def test_generate_text(self, mock_gen_model_cls):
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated Answer"
        mock_model.generate_content.return_value = mock_response
        mock_gen_model_cls.return_value = mock_model

        # Execute
        result = self.service.generate_text("Test Prompt")

        # Verify
        self.assertEqual(result, "Generated Answer")
        mock_gen_model_cls.assert_called()
        mock_model.generate_content.assert_called_with("Test Prompt")

    @patch('app.services.llm_services.gemini_service.gemini_service.GenerativeModel')
    def test_prompt_rendering(self, mock_gen_model_cls):
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Model Answer"
        mock_model.generate_content.return_value = mock_response
        mock_gen_model_cls.return_value = mock_model

        query = ["What is X?"] 
        context_texts = ["Context about X"]
        source_names = ["source1.pdf"]
        context = (context_texts, source_names)

        # Execute
        answer, sources = self.service.generate_answer(query, context)

        # Verify return values
        self.assertEqual(answer, "Model Answer")
        self.assertEqual(sources, source_names)
        
        # Verify model generation called with a prompt containing our data
        # This implicitly tests that PromptManager loaded and rendered the template correctly
        mock_model.generate_content.assert_called()
        generated_prompt = mock_model.generate_content.call_args[0][0]
        
        # Check that the real template actually included the context and query
        self.assertIn("Context about X", generated_prompt)
        self.assertIn("What is X?", generated_prompt)
        self.assertIn("source1.pdf", generated_prompt)

    @patch('app.services.llm_services.gemini_service.gemini_service.GenerativeModel')
    @patch('builtins.open', new_callable=mock_open, read_data=b"file_content")
    def test_summarize_file(self, mock_file, mock_gen_model_cls):
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_model.generate_content.return_value = mock_response
        mock_gen_model_cls.return_value = mock_model

        # Execute
        summary = self.service.summarize_file("test.txt")

        # Verify
        self.assertEqual(summary, "Summary")
        mock_file.assert_called_with("test.txt", "rb")
        mock_model.generate_content.assert_called()

if __name__ == '__main__':
    unittest.main()
