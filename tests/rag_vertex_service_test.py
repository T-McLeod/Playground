import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from app.services.rag_services.vertex_service.vertex_service import VertexRAGService

class TestVertexRAGService(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_LOCATION": "us-central1"
        })
        self.env_patcher.start()
        self.service = VertexRAGService()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('app.services.rag_services.vertex_service.vertex_service.rag')
    def test_create_and_provision_corpus(self, mock_rag):
        mock_corpus = MagicMock()
        mock_corpus.name = "projects/123/locations/us-central1/ragCorpora/456"
        mock_rag.create_corpus.return_value = mock_corpus
        
        files = [
            {'gcs_uri': 'gs://bucket/file1.pdf', 'display_name': 'file1.pdf', 'id': '1'},
            {'gcs_uri': 'gs://bucket/file2.pdf', 'display_name': 'file2.pdf', 'id': '2'}
        ]
        
        corpus_name = self.service.create_and_provision_corpus(files, "test-suffix")
        
        
        self.assertEqual(corpus_name, "projects/123/locations/us-central1/ragCorpora/456")
        mock_rag.create_corpus.assert_called_once()
        
        call_args = mock_rag.create_corpus.call_args
        self.assertIn("test-suffix", call_args.kwargs['display_name'])
        
        mock_rag.import_files.assert_called_with(
            corpus_name="projects/123/locations/us-central1/ragCorpora/456",
            paths=['gs://bucket/file2.pdf'], chunk_size=512, chunk_overlap=100
        )
        self.assertEqual(mock_rag.import_files.call_count, 2)

    @patch('app.services.rag_services.vertex_service.vertex_service.rag')
    def test_retrieve_context(self, mock_rag):
        mock_response = MagicMock()
        
        context1 = MagicMock()
        context1.text = "Context 1"
        context1.source_uri = "gs://bucket/file1.pdf"
        context1.distance = 0.1
        
        context2 = MagicMock()
        context2.text = "Context 2"
        context2.source_uri = "gs://bucket/file2.pdf"
        context2.distance = 0.2
        
        mock_response.contexts.contexts = [context1, context2]
        mock_rag.retrieval_query.return_value = mock_response
        
        contexts, sources = self.service.retrieve_context("corpus_id", "query")
        
        self.assertEqual(contexts, ["Context 1", "Context 2"])
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]['filename'], 'file1.pdf')
        self.assertEqual(sources[1]['filename'], 'file2.pdf')
        
        mock_rag.retrieval_query.assert_called_once()

    @patch('app.services.rag_services.vertex_service.vertex_service.rag')
    def test_delete_corpus(self, mock_rag):
        self.service.delete_corpus("corpus_id")
        
        mock_rag.delete_corpus.assert_called_once_with(corpus_name="corpus_id")

if __name__ == '__main__':
    unittest.main()
