"""
Unit tests for kg_service.py
Tests the knowledge graph building functionality with mocked external dependencies.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import kg_service


class TestKnowledgeGraphService(unittest.TestCase):
    """Test suite for build_knowledge_graph function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_files = [
            {'id': '101', 'name': 'Chapter 3.pdf', 'display_name': 'Chapter 3.pdf'},
            {'id': '102', 'name': 'Lecture 5.pdf', 'display_name': 'Lecture 5.pdf'},
            {'id': '103', 'name': 'Lab Manual.pdf', 'display_name': 'Lab Manual.pdf'},
        ]
        
        self.sample_topics = ['Cell Mitosis', 'DNA Replication', 'Protein Synthesis']
        self.corpus_id = 'projects/test-project/locations/us-central1/ragCorpora/12345'
    
    def test_topic_list_parsing_string(self):
        """Test that newline-separated string topics are parsed correctly."""
        topics_str = "Cell Mitosis\nDNA Replication\nProtein Synthesis"
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            # Mock RAG to return empty contexts
            mock_rag.return_value = []
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                topics_str, self.corpus_id, []
            )
            
            nodes = json.loads(nodes_json)
            topic_nodes = [n for n in nodes if n['group'] == 'topic']
            
            self.assertEqual(len(topic_nodes), 3)
            self.assertEqual(topic_nodes[0]['label'], 'Cell Mitosis')
            self.assertEqual(topic_nodes[1]['label'], 'DNA Replication')
            self.assertEqual(topic_nodes[2]['label'], 'Protein Synthesis')
    
    def test_topic_list_parsing_list(self):
        """Test that list of topics is handled correctly."""
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = []
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                self.sample_topics, self.corpus_id, []
            )
            
            nodes = json.loads(nodes_json)
            topic_nodes = [n for n in nodes if n['group'] == 'topic']
            
            self.assertEqual(len(topic_nodes), 3)
            self.assertEqual(topic_nodes[0]['id'], 'topic_1')
            self.assertEqual(topic_nodes[1]['id'], 'topic_2')
            self.assertEqual(topic_nodes[2]['id'], 'topic_3')
    
    def test_file_node_creation_dict(self):
        """Test file node creation from dictionary file objects."""
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = []
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                [], self.corpus_id, self.sample_files
            )
            
            nodes = json.loads(nodes_json)
            file_nodes = [n for n in nodes if n['group'] == 'file_pdf']
            
            self.assertEqual(len(file_nodes), 3)
            self.assertEqual(file_nodes[0]['id'], '101')
            self.assertEqual(file_nodes[0]['label'], 'Chapter 3.pdf')
            self.assertEqual(file_nodes[0]['group'], 'file_pdf')
    
    def test_file_node_creation_object(self):
        """Test file node creation from object file objects."""
        class FileObj:
            def __init__(self, id, name):
                self.id = id
                self.name = name
        
        file_objects = [
            FileObj('201', 'Assignment 1.pdf'),
            FileObj('202', 'Assignment 2.pdf'),
        ]
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = []
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                [], self.corpus_id, file_objects
            )
            
            nodes = json.loads(nodes_json)
            file_nodes = [n for n in nodes if n['group'] == 'file_pdf']
            
            self.assertEqual(len(file_nodes), 2)
            self.assertEqual(file_nodes[0]['id'], '201')
            self.assertEqual(file_nodes[0]['label'], 'Assignment 1.pdf')
    
    def test_file_node_skips_empty_id(self):
        """Test that files with empty IDs are skipped."""
        files_with_empty = [
            {'id': '101', 'name': 'Valid File.pdf'},
            {'id': '', 'name': 'Invalid File.pdf'},  # Empty ID
            {'id': '103', 'name': 'Another Valid.pdf'},
        ]
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = []
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                [], self.corpus_id, files_with_empty
            )
            
            nodes = json.loads(nodes_json)
            file_nodes = [n for n in nodes if n['group'] == 'file_pdf']
            
            # Should only have 2 files (empty ID skipped)
            self.assertEqual(len(file_nodes), 2)
            self.assertNotIn('', [n['id'] for n in file_nodes])
    
    def test_topic_file_connections_with_file_id(self):
        """Test edge creation when RAG contexts have file_id attribute."""
        # Mock context with file_id
        mock_context1 = Mock()
        mock_context1.file_id = '101'
        mock_context1.source_display_name = 'Chapter 3.pdf'
        mock_context1.text = 'Context about mitosis'
        
        mock_context2 = Mock()
        mock_context2.file_id = '102'
        mock_context2.source_display_name = 'Lecture 5.pdf'
        mock_context2.text = 'More context about mitosis'
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            # Mock RAG to return contexts with file_id
            mock_rag.return_value = [mock_context1, mock_context2]
            
            # Mock Gemini response
            mock_response = Mock()
            mock_response.text = 'Mitosis is the process of cell division.'
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['Cell Mitosis'], self.corpus_id, self.sample_files
            )
            
            edges = json.loads(edges_json)
            
            # Should have edges from topic_1 to file 101 and 102
            self.assertEqual(len(edges), 2)
            self.assertEqual(edges[0]['from'], 'topic_1')
            self.assertIn(edges[0]['to'], ['101', '102'])
            self.assertEqual(edges[1]['from'], 'topic_1')
            self.assertIn(edges[1]['to'], ['101', '102'])
    
    def test_topic_file_connections_name_matching(self):
        """Test edge creation using name matching when file_id is not available."""
        # Mock context without file_id (fallback to name matching)
        # Use spec to control which attributes exist
        mock_context = Mock(spec=['source_display_name', 'text', 'source'])
        mock_context.source_display_name = 'Chapter 3.pdf'
        mock_context.text = 'Context about DNA replication'
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = [mock_context]
            
            mock_response = Mock()
            mock_response.text = 'DNA replication is the process of copying DNA.'
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['DNA Replication'], self.corpus_id, self.sample_files
            )
            
            edges = json.loads(edges_json)
            
            # Should match 'Chapter 3.pdf' to file ID '101'
            self.assertEqual(len(edges), 1)
            self.assertEqual(edges[0]['from'], 'topic_1')
            self.assertEqual(edges[0]['to'], '101')
    
    def test_summary_generation(self):
        """Test that topic summaries are generated using Gemini."""
        mock_context = Mock()
        mock_context.file_id = '101'
        mock_context.source_display_name = 'Chapter 3.pdf'
        mock_context.text = 'Detailed context about protein synthesis'
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = [mock_context]
            
            mock_response = Mock()
            mock_response.text = 'Protein synthesis is the process by which cells build proteins.'
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['Protein Synthesis'], self.corpus_id, self.sample_files
            )
            
            data = json.loads(data_json)
            
            # Check that summary was generated
            self.assertIn('topic_1', data)
            self.assertIn('summary', data['topic_1'])
            self.assertEqual(data['topic_1']['summary'], 'Protein synthesis is the process by which cells build proteins.')
            self.assertIn('sources', data['topic_1'])
            self.assertIn('Chapter 3.pdf', data['topic_1']['sources'])
    
    def test_summary_fallback_on_gemini_error(self):
        """Test that fallback summary is used when Gemini fails."""
        mock_context = Mock()
        mock_context.file_id = '101'
        mock_context.source_display_name = 'Chapter 3.pdf'
        mock_context.text = 'Context text'
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = [mock_context]
            
            # Mock Gemini to raise an exception
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception('API Error')
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['Test Topic'], self.corpus_id, self.sample_files
            )
            
            data = json.loads(data_json)
            
            # Should have fallback summary
            self.assertIn('topic_1', data)
            self.assertIn('summary', data['topic_1'])
            self.assertIn('Summary for Test Topic based on course materials', data['topic_1']['summary'])
    
    def test_rag_query_error_handling(self):
        """Test that topic nodes are still created even if RAG query fails."""
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            # Mock RAG to raise an exception
            mock_rag.side_effect = Exception('RAG API Error')
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['Cell Mitosis'], self.corpus_id, self.sample_files
            )
            
            nodes = json.loads(nodes_json)
            edges = json.loads(edges_json)
            data = json.loads(data_json)
            
            # Topic node should still be created
            topic_nodes = [n for n in nodes if n['group'] == 'topic']
            self.assertEqual(len(topic_nodes), 1)
            self.assertEqual(topic_nodes[0]['label'], 'Cell Mitosis')
            
            # But no edges should be created
            self.assertEqual(len(edges), 0)
            
            # Error message should be in summary
            self.assertIn('Error retrieving information', data['topic_1']['summary'])
            self.assertEqual(data['topic_1']['sources'], [])
    
    def test_json_serialization(self):
        """Test that output is properly serialized to JSON strings."""
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = []
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['Topic 1'], self.corpus_id, [{'id': '101', 'name': 'File1.pdf'}]
            )
            
            # Should return strings
            self.assertIsInstance(nodes_json, str)
            self.assertIsInstance(edges_json, str)
            self.assertIsInstance(data_json, str)
            
            # Should be valid JSON
            nodes = json.loads(nodes_json)
            edges = json.loads(edges_json)
            data = json.loads(data_json)
            
            self.assertIsInstance(nodes, list)
            self.assertIsInstance(edges, list)
            self.assertIsInstance(data, dict)
    
    def test_multiple_topics_multiple_files(self):
        """Test complete graph with multiple topics and files."""
        mock_context1 = Mock()
        mock_context1.file_id = '101'
        mock_context1.source_display_name = 'Chapter 3.pdf'
        mock_context1.text = 'Mitosis context'
        
        mock_context2 = Mock()
        mock_context2.file_id = '102'
        mock_context2.source_display_name = 'Lecture 5.pdf'
        mock_context2.text = 'DNA context'
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            # Different contexts for different topics
            def rag_side_effect(parent, query, similarity_top_k):
                if 'Mitosis' in query:
                    return [mock_context1]
                elif 'DNA' in query:
                    return [mock_context2]
                return []
            
            mock_rag.side_effect = rag_side_effect
            
            mock_response = Mock()
            mock_response.text = 'Test summary'
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['Cell Mitosis', 'DNA Replication'],
                self.corpus_id,
                self.sample_files
            )
            
            nodes = json.loads(nodes_json)
            edges = json.loads(edges_json)
            data = json.loads(data_json)
            
            # Should have 2 topics + 3 files = 5 nodes
            self.assertEqual(len(nodes), 5)
            
            # Should have edges
            self.assertGreater(len(edges), 0)
            
            # Should have data for both topics
            self.assertIn('topic_1', data)
            self.assertIn('topic_2', data)
    
    def test_duplicate_source_names_removed(self):
        """Test that duplicate source names are removed from sources list."""
        mock_context1 = Mock()
        mock_context1.file_id = '101'
        mock_context1.source_display_name = 'Chapter 3.pdf'
        mock_context1.text = 'Context 1'
        
        mock_context2 = Mock()
        mock_context2.file_id = '101'  # Same file
        mock_context2.source_display_name = 'Chapter 3.pdf'  # Same name
        mock_context2.text = 'Context 2'
        
        with patch('app.services.kg_service.rag.retrieve_contexts', create=True) as mock_rag, \
             patch('app.services.kg_service.GenerativeModel') as mock_gemini:
            
            mock_rag.return_value = [mock_context1, mock_context2]
            
            mock_response = Mock()
            mock_response.text = 'Summary'
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_model
            
            nodes_json, edges_json, data_json = kg_service.build_knowledge_graph(
                ['Test Topic'], self.corpus_id, self.sample_files
            )
            
            data = json.loads(data_json)
            
            # Should only have one source name (duplicates removed)
            self.assertEqual(len(data['topic_1']['sources']), 1)
            self.assertEqual(data['topic_1']['sources'][0], 'Chapter 3.pdf')


if __name__ == '__main__':
    unittest.main()

