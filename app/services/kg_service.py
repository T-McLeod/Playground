"""
Knowledge Graph Service
Handles all networkx graph construction and topic summarization.
"""
import sys
import networkx as nx
import json
import logging
import os
from typing import List

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
from app.services import gemini_service

logger = logging.getLogger(__name__)


SUMMARY_QUERY_TEMPLATE = (
    "Write a 1-paragraph summary for the topic: {topic}."
)

def extract_topics_from_summaries(summaries: List[str]) -> List[str]:
    """
    Uses Gemini to extract main course topics from syllabus text.
    
    Args:
        syllabus_text: The syllabus content
        count: Number of topics to extract (default 8)
        
    Returns:
        List of topic strings
    """
    all_summaries= "\n".join(summaries)
    prompt = f"""Analyze these document summaries and group the topics discuessed into 4 to 8 most important topics covered. Do not create more than necessary. Also, only include taught topics, not course policies or syllabi
Return ONLY a comma-separated list of topics in order of importance, nothing else.

Example output: Machine Learning, Neural Networks, Data Processing, Model Evaluation

Summaries: {all_summaries}"""
    
    try:
        topics_text = gemini_service.generate_answer(prompt)
        topics = [t.strip() for t in topics_text.split(',') if t.strip()]
        return topics[:8]
    except Exception as e:
        logger.error(f"Failed to extract topics from syllabus: {e}")
        raise

def build_knowledge_graph(topic_list: list, corpus_id: str, files: list) -> tuple[str, str, str]:
    """
    Builds the complete knowledge graph with topics, files, and connections.
    
    Args:
        topic_list: List of topic strings from professor input (or newline-separated string)
        corpus_id: The RAG corpus ID to query for topic summaries
        files: List of file objects from Canvas
        
    Returns:
        Tuple of (nodes_json, edges_json, data_json) as serialized JSON strings
    """
    # Initialize networkx graph
    G = nx.Graph()
    
    # Initialize data structures
    nodes = []
    edges = []
    kg_data = {}
    
    # Parse topic_list - handle both list and newline-separated string
    if isinstance(topic_list, str):
        topics = [t.strip() for t in topic_list.split('\n') if t.strip()]
    else:
        topics = [str(t).strip() for t in topic_list if str(t).strip()]
    print("TOPICS: ", topics)

    
    
    # Create a mapping of file names to file IDs for edge creation
    file_name_to_id = {}
    
    # Step 1: Create File Nodes
    for file_obj in files:
        # Extract file information (handle both dict and object attributes)
        if isinstance(file_obj, dict):
            file_id = str(file_obj.get('id', ''))
            file_name = file_obj.get('name') or file_obj.get('display_name', 'Unknown File')
        else:
            file_id = str(getattr(file_obj, 'id', ''))
            file_name = getattr(file_obj, 'name', None) or getattr(file_obj, 'display_name', 'Unknown File')
        
        if not file_id:
            continue
        
        # Create file node
        file_node = {
            'id': file_id,
            'label': file_name,
            'group': 'file_pdf'
        }
        
        # Add to networkx graph
        G.add_node(file_id, **file_node)
        nodes.append(file_node)
        
        # Store mapping for edge creation
        file_name_to_id[file_name] = file_id
    
    # Step 2: Create Topic Nodes and Query RAG
    # Use RAG service to retrieve context for each topic
    
    for i, topic in enumerate(topics):
        topic_id = f"topic_{i+1}"
        
        logger.info(f"Processing topic {i+1}/{len(topics)}: {topic}")
        
        # Create topic node
        topic_node = {
            'id': topic_id,
            'label': topic,
            'group': 'topic'
        }
        
        # Add to networkx graph
        G.add_node(topic_id, **topic_node)
        nodes.append(topic_node)
        
        # Query RAG corpus for this topic using rag_service
        try:
            # Use rag_service to retrieve context
            summary, source_names = gemini_service.generate_answer_with_context(
                query=SUMMARY_QUERY_TEMPLATE.format(topic=topic),
                corpus_id=corpus_id,
            )
            
            # Extract unique source file IDs
            source_files = []
            for source in source_names:
                # Handle both old string format and new dict format
                if isinstance(source, dict):
                    source_name = source.get('filename', '')
                else:
                    source_name = source
                
                # Match source name to file IDs
                for file_name, fid in file_name_to_id.items():
                    if file_name in source_name or source_name in file_name:
                        if fid not in source_files:
                            source_files.append(fid)
                        break
            
            # Store topic data
            kg_data[topic_id] = {
                'summary': summary,
                'sources': source_names  # Keep the full source objects (with filename and source_uri)
            }
            
            # Create edges from topic to relevant files
            for file_id in source_files:
                edge = {
                    'from': topic_id,
                    'to': file_id
                }
                # Add to networkx graph
                G.add_edge(topic_id, file_id)
                edges.append(edge)
                
        except Exception as e:
            logger.error(f"Error processing topic {topic}: {e}")
            # If RAG query fails, still create the topic node but with empty data
            kg_data[topic_id] = {
                'summary': f"Error retrieving information for {topic}.",
                'sources': []
            }
    
    # Step 3: Serialize to JSON strings
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    data_json = json.dumps(kg_data)

    print("NODES: ", nodes)
    print("EDGES: ", edges)
    print("DATA: ", kg_data)

    
    return (nodes_json, edges_json, data_json)