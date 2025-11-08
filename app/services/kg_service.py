"""
Knowledge Graph Service
Handles all networkx graph construction and topic summarization.
"""
import networkx as nx
import json
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel

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
    # Use corpus_id directly as corpus resource name (should be full resource path from rag_service)
    # Per ProjectPlan: contexts = rag.retrieve_contexts(corpus.name, topic)
    corpus_resource = corpus_id
    
    # Initialize Gemini model for summaries
    model = GenerativeModel("gemini-pro")
    
    for i, topic in enumerate(topics):
        topic_id = f"topic_{i+1}"
        
        # Create topic node
        topic_node = {
            'id': topic_id,
            'label': topic,
            'group': 'topic'
        }
        
        # Add to networkx graph
        G.add_node(topic_id, **topic_node)
        nodes.append(topic_node)
        
        # Query RAG corpus for this topic
        try:
            # Retrieve contexts from RAG corpus
            # Per ProjectPlan line 126: contexts = rag.retrieve_contexts(corpus.name, topic)
            contexts = rag.retrieve_contexts(
                parent=corpus_resource,
                query=topic,
                similarity_top_k=10  # Get top 10 relevant chunks
            )
            
            # Extract source file information
            source_files = []
            source_names = []
            context_texts = []
            
            for context in contexts:
                # Extract source display name (per ProjectPlan line 142)
                source_name = getattr(context, 'source_display_name', None) or getattr(context, 'source', 'Unknown')
                source_names.append(source_name)
                
                # Per ProjectPlan line 129: use source.file_id directly if available
                # Fallback to name matching if file_id is not present
                file_id = None
                if hasattr(context, 'file_id'):
                    # Direct file_id from context (preferred method per ProjectPlan)
                    file_id = str(getattr(context, 'file_id'))
                else:
                    # Fallback: match by source name to file name
                    for file_name, fid in file_name_to_id.items():
                        if file_name in source_name or source_name in file_name:
                            file_id = fid
                            break
                
                if file_id and file_id not in source_files:
                    source_files.append(file_id)
                
                # Collect context text for summary
                context_text = getattr(context, 'text', None) or getattr(context, 'content', '')
                if context_text:
                    context_texts.append(context_text)
            
            # Generate summary using Gemini
            # Per ProjectPlan line 127: "Using this context: [contexts], write a 1-paragraph summary for the topic: [topic]."
            summary = ""
            if context_texts:
                # Combine contexts for summary generation
                combined_context = "\n\n".join(context_texts[:5])  # Use top 5 contexts
                prompt = f"Using this context: {combined_context}, write a 1-paragraph summary for the topic: {topic}."
                
                try:
                    response = model.generate_content(prompt)
                    summary = response.text if hasattr(response, 'text') else str(response)
                except Exception as e:
                    # Fallback if Gemini fails
                    summary = f"Summary for {topic} based on course materials."
            
            # Store topic data
            kg_data[topic_id] = {
                'summary': summary,
                'sources': list(set(source_names))  # Remove duplicates
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
