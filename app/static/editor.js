// Editor page - Load and display knowledge graph topics for editing

(function() {
    // Local scope to avoid conflicts with app.js
    let editorGraphData = null;
    let editorNetwork = null;

    async function loadGraphData() {
        try {
            console.log('Loading graph data for editor...');
            const response = await fetch(`/api/get-graph?playground_id=${PLAYGROUND_ID}`);
            const data = await response.json();
            
            editorGraphData = {
                nodes: JSON.parse(data.nodes),
                edges: JSON.parse(data.edges),
                data: JSON.parse(data.data)
            };

            console.log('Graph data loaded:', editorGraphData);
            
            // Convert graph to topics and render editor
            const topicsData = convertGraphToTopics();
            renderTopicEditor(topicsData);
            setupTopicEditorHandlers();
            
        } catch (error) {
            console.error('Failed to load graph data:', error);
            alert('Failed to load course topics. Please refresh the page.');
        }
    }

    // Convert knowledge graph to topics editor format
    function convertGraphToTopics() {
        const topicsData = [];
        const topicNodes = editorGraphData.nodes.filter(node => node.group === 'topic');
        
        for (const node of topicNodes) {
            const topicId = node.id;
            const topicInfo = editorGraphData.data[topicId] || {};
            
            topicsData.push({
                topic: node.label || 'Untitled Topic',
                summary: topicInfo.summary || 'No summary available.'
            });
        }
        
        return topicsData;
    }

    // Initialize editor on page load
    document.addEventListener('DOMContentLoaded', () => {
        loadGraphData();
    });
})();
