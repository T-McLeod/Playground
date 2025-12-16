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

logger = logging.getLogger(__name__)

llm_service = get_llm_service()


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


def add_topic_to_graph(topic_name: str, corpus_id: str, existing_nodes: list, existing_edges: list, existing_data: dict, custom_summary: str = None) -> tuple[str, str, str]:
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
    logger.info(f"Adding new topic to graph: {topic_name}")
    
    # Find the next topic ID number
    existing_topic_ids = [node['id'] for node in existing_nodes if node.get('group') == 'topic' and node['id'].startswith('topic_')]
    topic_numbers = [int(tid.split('_')[1]) for tid in existing_topic_ids if '_' in tid and tid.split('_')[1].isdigit()]
    next_number = max(topic_numbers) + 1 if topic_numbers else 1
    new_topic_id = f"topic_{next_number}"
    
    # Create topic node
    new_topic_node = {
        'id': new_topic_id,
        'label': topic_name,
        'group': 'topic'
    }
    
    # Create a mapping of file names to file IDs
    file_name_to_id = {}
    for node in existing_nodes:
        if node.get('group') in ['file_pdf', 'file']:
            file_name_to_id[node.get('label')] = node.get('id')
    
    # Query RAG corpus for this topic (or use custom summary)
    try:
        if custom_summary:
            # Use the provided custom summary
            summary = custom_summary
            source_names = []
            source_files = []
            logger.info(f"Using custom summary for topic '{topic_name}'")
        else:
            summary, source_names = llm_service.generate_answer(
                query=SUMMARY_QUERY_TEMPLATE.format(topic=topic_name),
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
        topic_data = {
            'summary': summary,
            'sources': source_names
        }
        
        # Create edges from topic to relevant files
        new_edges = []
        for file_id in source_files:
            edge = {
                'from': new_topic_id,
                'to': file_id
            }
            new_edges.append(edge)
        
        logger.info(f"Created topic '{topic_name}' with {len(source_files)} connected sources")
        
    except Exception as e:
        logger.error(f"Error querying RAG for topic {topic_name}: {e}")
        # If RAG query fails, still create the topic node but with empty data
        topic_data = {
            'summary': f"Error retrieving information for {topic_name}.",
            'sources': []
        }
        new_edges = []
    
    # Update the graph structures
    updated_nodes = existing_nodes + [new_topic_node]
    updated_edges = existing_edges + new_edges
    updated_data = {**existing_data, new_topic_id: topic_data}
    
    # Serialize to JSON strings
    nodes_json = json.dumps(updated_nodes)
    edges_json = json.dumps(updated_edges)
    data_json = json.dumps(updated_data)
    
    logger.info(f"Successfully added topic '{topic_name}' (ID: {new_topic_id})")
    
    return (nodes_json, edges_json, data_json)


def remove_topic_from_graph(topic_id: str, existing_nodes: list, existing_edges: list, existing_data: dict) -> tuple[str, str, str]:
    """
    Removes a topic from an existing knowledge graph.
    
    Args:
        topic_id: ID of the topic to remove (e.g., 'topic_1')
        existing_nodes: Current list of graph nodes
        existing_edges: Current list of graph edges
        existing_data: Current kg_data dictionary
        
    Returns:
        Tuple of (updated_nodes_json, updated_edges_json, updated_data_json)
    """
    logger.info(f"Removing topic from graph: {topic_id}")
    
    # Find and verify the topic exists
    topic_node = None
    for node in existing_nodes:
        if node.get('id') == topic_id:
            if node.get('group') != 'topic':
                raise ValueError(f"Node {topic_id} is not a topic node (group: {node.get('group')})")
            topic_node = node
            break
    
    if not topic_node:
        raise ValueError(f"Topic {topic_id} not found in graph")
    
    logger.info(f"Found topic to remove: {topic_node.get('label')}")
    
    # Remove the topic node
    updated_nodes = [node for node in existing_nodes if node.get('id') != topic_id]
    
    # Remove all edges connected to this topic (both incoming and outgoing)
    updated_edges = [
        edge for edge in existing_edges 
        if edge.get('from') != topic_id and edge.get('to') != topic_id
    ]
    
    # Remove the topic data
    updated_data = {k: v for k, v in existing_data.items() if k != topic_id}
    
    # Calculate what was removed
    nodes_removed = len(existing_nodes) - len(updated_nodes)
    edges_removed = len(existing_edges) - len(updated_edges)
    
    logger.info(f"Removed {nodes_removed} node(s) and {edges_removed} edge(s)")
    
    # Serialize to JSON strings
    nodes_json = json.dumps(updated_nodes)
    edges_json = json.dumps(updated_edges)
    data_json = json.dumps(updated_data)
    
    logger.info(f"Successfully removed topic '{topic_node.get('label')}' (ID: {topic_id})")
    
    return (nodes_json, edges_json, data_json)


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
            summary, source_names = llm_service.generate_answer(
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


if __name__ == "__main__":
    # Test topic extraction for Canvas course
    from dotenv import load_dotenv
    import vertexai
    
    # Load environment variables
    env_path = os.path.join(root_dir, '.env')
    load_dotenv(env_path)
    
    # Initialize Vertex AI
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    location = os.environ.get('GOOGLE_CLOUD_LOCATION')
    
    if project_id:
        vertexai.init(project=project_id, location=location)
    
    print(f"Loaded environment from: {env_path}")
    print(f"GOOGLE_CLOUD_PROJECT: {project_id}")
    print(f"GOOGLE_CLOUD_LOCATION: {location}")
    
    if not project_id:
        print("\n⚠️  Please set GOOGLE_CLOUD_PROJECT in .env")
        import sys
        sys.exit(1)
    
    try:
        # Import firestore service to get course data
        from app.services.firestore_service import get_course_data
        
        # Get course data for 13299557
        course_id = "13299557"
        print("\n" + "=" * 80)
        print(f"TOPIC EXTRACTION TEST - Course {course_id}")
        print("=" * 80)
        
        course_doc = get_course_data(course_id)
        if not course_doc.exists:
            print(f"\n❌ Course {course_id} not found in Firestore")
            import sys
            sys.exit(1)
        
        course_data = course_doc.to_dict()
        corpus_id = course_data.get('corpus_id')
        
        print(f"\n📚 Course Info:")
        print(f"   Corpus ID: {corpus_id}")
        
        # Get file summaries from the corpus
        print(f"\n📄 Generating file summaries...")
        from app.services.rag_service import retrieve_context
        
        # Create queries to get comprehensive content from each major topic area
        summary_queries = [
            "What are the main topics covered in these materials?",
            "What mathematical concepts and theorems are taught?",
            "What problem-solving techniques are discussed?",
            "What are the key learning objectives?"
        ]
        
        all_contexts = []
        for query in summary_queries:
            contexts, _ = retrieve_context(corpus_id, query, top_k=15, threshold=0.5)
            all_contexts.extend(contexts)
        
        print(f"   Retrieved {len(all_contexts)} context chunks")
        
        # Use the contexts as "summaries" for topic extraction
        summaries = all_contexts[:30]  # Use first 30 chunks to avoid token limits
        
        print(f"\n🔍 Testing topic extraction with different NUM_TOPICS values...")
        print("=" * 80)
        
        # Test different values of NUM_TOPICS
        test_values = [4, 6, 8, 10, 12]
        
        results = {}
        original_num = NUM_TOPICS  # Save original value
        
        for num in test_values:
            print(f"\n{'─' * 80}")
            print(f"Testing NUM_TOPICS = {num}")
            print(f"{'─' * 80}")
            
            # Temporarily modify the module-level variable
            import app.services.kg_service as kg_module
            kg_module.NUM_TOPICS = num
            
            try:
                topics = extract_topics_from_summaries(summaries, num_topics=num)
                
                print(f"\n✅ Extracted {len(topics)} topics:")
                for i, topic in enumerate(topics, 1):
                    print(f"   {i}. {topic}")
                
                results[num] = topics
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Restore original value
                kg_module.NUM_TOPICS = original_num
        
        # Summary comparison
        print("\n" + "=" * 80)
        print("SUMMARY COMPARISON")
        print("=" * 80)
        
        for num, topics in results.items():
            print(f"\nNUM_TOPICS = {num} ({len(topics)} topics generated):")
            for i, topic in enumerate(topics, 1):
                print(f"  {i}. {topic}")
        
        print("\n" + "=" * 80)
        print("🎉 Topic Extraction Test Complete!")
        print("=" * 80)
        
        print("\n💡 Analysis:")
        print("   • Compare the topics generated with different NUM_TOPICS values")
        print("   • Look for the right balance between comprehensiveness and granularity")
        print("   • Topics should be broad enough to group related content")
        print("   • Topics should be specific enough to be meaningful")
        print("   • Optimal value depends on course content and structure")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()