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
from app.services.llm_services import get_llm_service
from app.services.rag_services import get_rag_service
from app.services import firestore_service

logger = logging.getLogger(__name__)

llm_service = get_llm_service()
rag_service = get_rag_service()

SUMMARY_QUERY_TEMPLATE = (
    "Write a 1-paragraph summary for the topic. Make clear what likely are the learning objectives and what student should focus on during the course: {topic}. Go straight to the summary, no intro or outro."
)

NUM_TOPICS = 9
def extract_topics_from_summaries(summaries: List[str], num_topics=NUM_TOPICS) -> List[str]:
    """
    Uses Gemini to extract main course topics from syllabus text.
    
    Args:
        syllabus_text: The syllabus content
        count: Number of topics to extract (default 8)
        
    Returns:
        List of topic strings
    """
    all_summaries= "\n".join(summaries)
    prompt = f"""
    Analyze these document summaries and group the topics discussed into {num_topics} most important topics covered. Do not create more than necessary. Also, only include taught topics, not course policies or syllabi. The course topcics generated should be suitable for creating a knowledge graph for student learning. They should cover broad themes of the entire course. Each course content (lecture, assignment, reading) should be represented in at least one topic. Topics should be only a few words long.
Return ONLY a comma-separated list of topics in order of importance, nothing else.
You should do do {num_topics} topics. Give or take one. You should not exceed {num_topics} by more than one.

Example output: Machine Learning, Neural Networks, Data Processing, Model Evaluation

Summaries: {all_summaries}"""
    
    try:
        topics_text = llm_service.generate_text(prompt)
        topics = [t.strip() for t in topics_text.split(',') if t.strip()]
        return topics[:num_topics]
    except Exception as e:
        logger.error(f"Failed to extract topics from syllabus: {e}")
        raise


def add_topic_to_graph(playground_id: str, topic_name: str, summary: str = "", files: list = []) -> None:
    """
    Adds a new topic to an existing knowledge graph.
    
    Args:
        topic_name: Name of the new topic to add
        corpus_id: The RAG corpus ID to query for topic summary and sources
        existing_nodes: Current list of graph nodes
        existing_edges: Current list of graph edges
        existing_data: Current kg_data dictionary
        custom_summary: Optional custom summary to use instead of generating one via RAG
        
    Returns:
        Tuple of (updated_nodes_json, updated_edges_json, updated_data_json)
    """
    for file in files:
        if 'id' not in file or 'name' not in file:
            raise ValueError("Each file must have 'id' and 'name' fields")
    
    create_node(playground_id, {
        "topic": topic_name,
        "summary": summary,
        "sources": files
    })


def remove_topic_from_graph(playground_id: str, topic_id: str) -> None:
    """
    Removes a topic and its associated edges from the knowledge graph.
    
    Args:
        playground_id: The playground document ID
        topic_id: The ID of the topic node to remove
    """
    node_collection = firestore_service.get_node_collection(playground_id)
    topic_doc = node_collection.document(topic_id)
    if topic_doc.get().exists:
        topic_doc.delete()
        logger.info(f"Removed topic {topic_id} from knowledge graph in playground {playground_id}")
    else:
        logger.warning(f"Topic {topic_id} not found in playground {playground_id}")
    

SUMMARY_QUERY_TEMPLATE = (
    "Write a 1-paragraph summary for the topic. Make clear what likely are the learning objectives and what student should focus on during the course: {topic}. Go straight to the summary, no intro or outro."
)
def build_knowledge_graph(playground_id: str, topic_list: list[str], corpus_id: str) -> list[dict]:
    """
    Builds a knowledge graph using the provided topics and files.
    
    Args:
        topic_list: List of topics to include in the knowledge graph.
        corpus_id: The RAG corpus ID to use for context retrieval.
    Returns:
        Tuple containing:
        - List of knowledge graph nodes
    """
    nodes = []
    for topic in topic_list:
        logger.info(f"Processing topic for KG: {topic}")
        query = SUMMARY_QUERY_TEMPLATE.format(topic=topic)
        context_texts, sources = rag_service.retrieve_context(
            corpus_id=corpus_id,
            query=query,
        )
        summary = llm_service.summarize_topic(
            topic=topic,
            context=context_texts,
        )
        nodes.append({
            "topic": topic,
            "summary": summary,
            "files": [source['file_id'] for source in sources]
        })

    update_nodes(playground_id=playground_id, kg_nodes=nodes)

    return nodes


def initialize_nodes(playground_id: str, nodes: list) -> None:
    """
    Initializes the knowledge graph portion of a course/playground document.
    
    Args:
        playground_id: The playground document ID
        nodes: List of node dicts to initialize the knowledge graph
    """
    node_collection = firestore_service.get_node_collection(playground_id)
    
    for node in nodes:
        node['id'] = node_collection.document().id
        node_doc = node_collection.document(node['id'])
        node_doc.set(node)
    logger.info(f"Initialized knowledge graph for playground {playground_id} with {len(nodes)} nodes.")


def update_nodes(playground_id: str, kg_nodes: list) -> None:
    """
    Updates only the knowledge graph portion of a course/playground document.
    Does NOT overwrite corpus_id, indexed_files, or status.

    Args:
        playground_id: The playground document ID (preferred)
        kg_nodes: Updated list of node dicts
    """
    
    node_collection = firestore_service.get_node_collection(playground_id)
    
    for node in kg_nodes:
        node_id = node.get('id')
        if not node_id:
            node_id = node_collection.document().id
            node['id'] = node_id
        node_doc = node_collection.document(node_id)
        node_doc.set(node)

    logger.info(f"Updated knowledge graph for playground {playground_id}")


def fetch_raw_nodes(playground_id: str) -> list:
    """
    Retrieves the knowledge graph nodes for a given playground.
    
    Args:
        playground_id: The playground document ID
        
    Returns:
        List of node dictionaries
    """
    node_collection = firestore_service.get_node_collection(playground_id)
    nodes = []
    
    docs = node_collection.stream()
    for doc in docs:
        node_data = doc.to_dict()
        nodes.append(node_data)
    
    logger.info(f"Retrieved {len(nodes)} knowledge graph nodes for playground {playground_id}")
    return nodes

def create_node(playground_id: str, node: dict) -> str:
    """
    Initializes the knowledge graph portion of a course/playground document.
    
    Args:
        playground_id: The playground document ID
        node: node dict to initialize the knowledge graph
    """
    node_collection = firestore_service.get_node_collection(playground_id)
    
    node['id'] = node_collection.document().id
    node_collection.document(node['id']).set(node)
    return node['id']


def render_knowledge_graph(playground_id: str, files_map: dict) -> tuple[list, list, dict]:
    """
    Renders the knowledge graph as a networkx DiGraph for visualization.
    
    Args:
        playground_id: The playground document ID
        files_map: Mapping of file IDs to file metadata dicts
    Returns:
        kg_nodes: List of knowledge graph nodes
        kg_edges: List of knowledge graph edges
        kg_data: Additional knowledge graph data
    EX:
        kg_nodes = [{"id": "abc123", "label": "Lec 1.pdf", "group": "file_pdf"}, {"id": "def456", "label": "Pigeon Hole", "group": "topic"}]
        kg_edges = [{"from": "abc123", "to": "def456"}]
        kg_data = {"topic_1": {"summary": "*summary*", "sources": [abc123]}}
    """
    nodes = fetch_raw_nodes(playground_id)
    kg_nodes = []
    kg_edges = []
    kg_data = {}
    files_added = set()

    for node in nodes:
        kg_nodes.append({
            "id": node['id'],
            "label": node['topic'],
            "group": "topic"
        })
        kg_data[node['id']] = {
            "summary": node.get('summary', ''),
            "sources": node.get('files', [])
        }
        for source_file_id in node.get('files', []):
            if source_file_id in files_map and source_file_id not in files_added:
                kg_nodes.append({
                    "id": source_file_id,
                    "label": files_map[source_file_id].get('display_name', 'Unnamed File'),
                    "group": "file_pdf"
                })
                files_added.add(source_file_id)

            if source_file_id in files_map:
                kg_edges.append({
                        "from": source_file_id,
                        "to": node['id']
                    })
            else:
                logger.warning(f"Source file ID {source_file_id} not found in files_map")

    return kg_nodes, kg_edges, kg_data