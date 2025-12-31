/**
 * Modal Manager
 * Handles modal display, resource rendering, and modal interactions
 */

const ModalManager = {
    currentTopic: null,
    topicModal: null,
    
    /**
     * Initialize the modal manager with DOM references
     * @param {Object} elements - DOM element references
     */
    init(elements) {
        this.topicModal = elements.topicModal || document.getElementById('topic-modal');
        this.modalTitle = elements.modalTitle || document.getElementById('modal-topic-title');
        this.modalSummary = elements.modalSummary || document.getElementById('modal-topic-summary');
        this.modalIcon = elements.modalIcon || document.getElementById('modal-topic-icon');
        this.resourceList = elements.resourceList || document.getElementById('resource-list');
        this.modalClose = elements.modalClose || document.getElementById('modal-close');
        
        // Bind close handlers
        if (this.modalClose) {
            this.modalClose.addEventListener('click', () => this.closeModal());
        }
        
        if (this.topicModal) {
            this.topicModal.addEventListener('click', (e) => {
                if (e.target === this.topicModal) this.closeModal();
            });
        }
        
        // Escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.topicModal && !this.topicModal.classList.contains('hidden')) {
                this.closeModal();
            }
        });
    },

    /**
     * Open the topic modal
     * @param {Object} topic - The topic node data
     * @param {Object} knowledgeGraph - The full knowledge graph
     * @param {Object} options - Optional configuration
     */
    openTopicModal(topic, knowledgeGraph, options = {}) {
        this.currentTopic = topic;

        // Get topic data from kg_data if available
        const topicData = knowledgeGraph.kg_data && knowledgeGraph.kg_data[topic.id] 
            ? knowledgeGraph.kg_data[topic.id] 
            : {};

        const summary = topicData.summary || 'No detailed summary available for this topic yet.';
        
        // Update modal title
        if (this.modalTitle) {
            this.modalTitle.textContent = topic.label;
        }
        
        // Update modal summary with markdown rendering
        if (this.modalSummary) {
            if (window.MarkdownUtils) {
                this.modalSummary.innerHTML = window.MarkdownUtils.renderMarkdownWithMath(summary);
            } else {
                this.modalSummary.textContent = summary;
            }
        }
        
        // Update icon if available
        if (this.modalIcon && options.showIcon) {
            const icons = ['📚', '🧠', '💡', '🔬', '🎯', '🚀', '⚡', '🌟', '🎨', '🔥', '💎', '🌈', '🎭', '🏆', '🎪'];
            const topicIndex = knowledgeGraph.kg_nodes.findIndex(n => n.id === topic.id);
            this.modalIcon.textContent = icons[topicIndex % icons.length];
        }

        // Get and render related resources
        const relatedResources = this.getRelatedResources(topic.id, knowledgeGraph);
        this.renderRelatedResources(relatedResources, knowledgeGraph, options.onResourceClick);

        // Call beforeOpen callback if provided (for clearing chat, etc.)
        if (options.beforeOpen) {
            options.beforeOpen(topic);
        }

        // Show modal with animation
        if (this.topicModal) {
            this.topicModal.classList.remove('hidden');
            setTimeout(() => this.topicModal.classList.add('show'), 10);
        }

        // Log analytics if callback provided
        if (options.onOpen) {
            options.onOpen(topic);
        }
    },

    /**
     * Close the modal
     */
    closeModal() {
        if (!this.topicModal) return;
        
        this.topicModal.classList.remove('show');
        setTimeout(() => {
            this.topicModal.classList.add('hidden');
            this.currentTopic = null;
        }, 300);
    },

    /**
     * Get current topic
     * @returns {Object} The current topic
     */
    getCurrentTopic() {
        return this.currentTopic;
    },

    /**
     * Get related resources for a topic
     * @param {string} topicId - The topic ID
     * @param {Object} knowledgeGraph - The knowledge graph
     * @returns {Array} Related resource nodes
     */
    getRelatedResources(topicId, knowledgeGraph) {
        if (!knowledgeGraph.kg_edges || !knowledgeGraph.kg_nodes) return [];

        const relatedNodeIds = new Set();
        
        // Find all connected nodes
        knowledgeGraph.kg_edges.forEach(edge => {
            if (edge.from === topicId) relatedNodeIds.add(edge.to);
            if (edge.to === topicId) relatedNodeIds.add(edge.from);
        });
        console.log('Related node IDs for topic', topicId, ':', Array.from(relatedNodeIds));

        // Get node details - look for file nodes
        const resources = [];
        relatedNodeIds.forEach(nodeId => {
            const node = knowledgeGraph.kg_nodes.find(n => n.id === nodeId);
            if (node && node.group === 'file') {
                resources.push(node);
            }
        });

        return resources;
    },

    /**
     * Render related resources in the modal
     * @param {Array} resources - The resources to render
     * @param {Object} knowledgeGraph - The knowledge graph
     * @param {Function} onResourceClick - Click handler for resources
     */
    renderRelatedResources(resources, knowledgeGraph, onResourceClick) {
        console.log('Rendering related resources:', resources);
        if (!this.resourceList) return;
        
        if (resources.length === 0) {
            this.resourceList.innerHTML = '<li style="cursor: default;">No resources linked yet</li>';
            return;
        }

        this.resourceList.innerHTML = '';
        resources.forEach(resource => {
            const li = document.createElement('li');
            li.textContent = resource.label;
            li.dataset.resourceId = resource.id;
            
            li.addEventListener('click', () => {
                if (onResourceClick) {
                    onResourceClick(resource, knowledgeGraph);
                } else {
                    this.openResource(resource, knowledgeGraph);
                }
            });
            
            this.resourceList.appendChild(li);
        });
    },

    /**
     * Open a resource (default handler)
     * @param {Object} resource - The resource node
     * @param {Object} knowledgeGraph - The knowledge graph
     */
    async openResource(resource, knowledgeGraph) {
        const fileId = resource.id;
        
        if (knowledgeGraph.indexed_files && knowledgeGraph.indexed_files[fileId]) {
            const fileData = knowledgeGraph.indexed_files[fileId];
            if (fileData.gcs_uri && window.ApiClient) {
                try {
                    const downloadUrl = await window.ApiClient.getDownloadUrl(fileData.gcs_uri);
                    window.open(downloadUrl, '_blank');
                    return;
                } catch (error) {
                    console.error('Error downloading resource:', error);
                }
            }
        }
        
        console.error('Could not find GCS URI for file:', resource);
        alert(`Could not open ${resource.label}. File may not be available.`);
    }
};

// Export for ES modules or attach to window
if (typeof window !== 'undefined') {
    window.ModalManager = ModalManager;
}
