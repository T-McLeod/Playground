/**
 * API Client
 * Centralized API calls for the playground application
 */

const ApiClient = {
    /**
     * Load knowledge graph data from the server
     * @param {string} playgroundId - The playground ID
     * @returns {Promise<Object>} The knowledge graph data
     */
    async loadKnowledgeGraph(playgroundId) {
        const response = await fetch(`/api/get-graph?playground_id=${playgroundId}`);
        if (!response.ok) {
            throw new Error(`Failed to load graph: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * Send a chat message and get a response
     * @param {string} playgroundId - The playground ID
     * @param {string} query - The user's question
     * @returns {Promise<Object>} The chat response with answer and sources
     */
    async sendChatMessage(playgroundId, query) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                playground_id: playgroundId,
                query: query
            })
        });

        if (!response.ok) {
            throw new Error(`Chat request failed: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * Get a signed download URL for a GCS file
     * @param {string} gcsUri - The GCS URI of the file
     * @returns {Promise<string>} The signed download URL
     */
    async getDownloadUrl(gcsUri) {
        const response = await fetch(`/api/download-source?gcs_uri=${encodeURIComponent(gcsUri)}`);
        if (!response.ok) {
            throw new Error('Failed to get download URL');
        }
        const data = await response.json();
        return data.download_url;
    },

    /**
     * Rate an AI response
     * @param {string} logDocId - The log document ID
     * @param {string} rating - 'helpful' or 'not_helpful'
     * @returns {Promise<Object>} The rating response
     */
    async rateAnswer(logDocId, rating) {
        const response = await fetch('/api/rate-answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                log_doc_id: logDocId,
                rating: rating
            })
        });

        if (!response.ok) {
            throw new Error('Failed to submit rating');
        }
        return response.json();
    },

    /**
     * Log a node click for analytics
     * @param {Object} data - The click data
     * @returns {Promise<void>}
     */
    async logNodeClick(data) {
        try {
            await fetch('/api/log-node-click', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    playground_id: data.playgroundId,
                    node_id: data.nodeId,
                    node_label: data.nodeLabel,
                    node_type: data.nodeType || 'topic',
                    user_id: data.userId || '',
                    timestamp: new Date().toISOString()
                })
            });
        } catch (error) {
            console.error('Error logging node click:', error);
            // Don't throw - analytics failures shouldn't block UX
        }
    },

    /**
     * Add a new topic to the knowledge graph (teacher only)
     * @param {string} playgroundId - The playground ID
     * @param {string} topicName - The topic name
     * @param {string} summary - Optional topic summary
     * @returns {Promise<Object>} The response
     */
    async addTopic(playgroundId, topicName, summary) {
        const response = await fetch('/api/add-topic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                playground_id: playgroundId,
                topic_name: topicName,
                summary: summary || undefined
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to add topic');
        }
        return response.json();
    },

    /**
     * Remove a topic from the knowledge graph (teacher only)
     * @param {string} playgroundId - The playground ID
     * @param {string} topicId - The topic ID to remove
     * @returns {Promise<Object>} The response
     */
    async removeTopic(playgroundId, topicId) {
        const response = await fetch('/api/remove-topic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                playground_id: playgroundId,
                topic_id: topicId
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || 'Failed to remove topic');
        }
        return response.json();
    }
};

// Export for ES modules or attach to window
if (typeof window !== 'undefined') {
    window.ApiClient = ApiClient;
}
