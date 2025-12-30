/**
 * Base View Class
 * Shared functionality for Student and Teacher views
 */

class BaseView {
    constructor(playgroundId, userId) {
        this.playgroundId = playgroundId;
        this.userId = userId;
        this.knowledgeGraph = null;
        this.currentView = 'graph'; // 'cards' or 'graph'
        
        // DOM element references
        this.elements = {};
    }

    /**
     * Initialize the view
     */
    async init() {
        this.cacheDOMElements();
        this.initializeEventListeners();
        await this.loadKnowledgeGraph();
    }

    /**
     * Cache commonly used DOM elements
     */
    cacheDOMElements() {
        this.elements = {
            topicsGrid: document.getElementById('topics-grid'),
            graphContainer: document.getElementById('graph-container'),
            networkCanvas: document.getElementById('network-canvas'),
            cardsViewBtn: document.getElementById('cards-view-btn'),
            graphViewBtn: document.getElementById('graph-view-btn'),
            fitGraphBtn: document.getElementById('fit-graph-btn'),
            resetZoomBtn: document.getElementById('reset-zoom-btn'),
            topicModal: document.getElementById('topic-modal'),
            modalTitle: document.getElementById('modal-topic-title'),
            modalSummary: document.getElementById('modal-topic-summary'),
            modalIcon: document.getElementById('modal-topic-icon'),
            resourceList: document.getElementById('resource-list'),
            modalClose: document.getElementById('modal-close'),
            loadingOverlay: document.getElementById('loading-overlay')
        };
    }

    /**
     * Initialize common event listeners
     */
    initializeEventListeners() {
        // View toggle handlers
        if (this.elements.cardsViewBtn) {
            this.elements.cardsViewBtn.addEventListener('click', () => this.switchView('cards'));
        }
        if (this.elements.graphViewBtn) {
            this.elements.graphViewBtn.addEventListener('click', () => this.switchView('graph'));
        }
        
        // Graph controls
        if (this.elements.fitGraphBtn) {
            this.elements.fitGraphBtn.addEventListener('click', () => {
                if (window.GraphRenderer) GraphRenderer.fit();
            });
        }
        if (this.elements.resetZoomBtn) {
            this.elements.resetZoomBtn.addEventListener('click', () => {
                if (window.GraphRenderer) GraphRenderer.resetZoom();
            });
        }

        // Initialize modal manager
        if (window.ModalManager) {
            ModalManager.init(this.elements);
        }
    }

    /**
     * Load knowledge graph data
     */
    async loadKnowledgeGraph() {
        UIHelpers.showLoading('Loading knowledge graph...');

        try {
            const data = await ApiClient.loadKnowledgeGraph(this.playgroundId);
            
            // Parse the response - handle both pre-parsed and string formats
            this.knowledgeGraph = {
                kg_nodes: typeof data.nodes === 'string' ? JSON.parse(data.nodes) : data.nodes,
                kg_edges: typeof data.edges === 'string' ? JSON.parse(data.edges) : data.edges,
                kg_data: typeof data.data === 'string' ? JSON.parse(data.data) : data.data,
                indexed_files: data.indexed_files || {}
            };

            console.log('Knowledge graph loaded:', this.knowledgeGraph);
            
            // Render both views (only one will be visible)
            this.renderTopicCards();
            this.renderGraph();
        } catch (error) {
            console.error('Error loading knowledge graph:', error);
            UIHelpers.showError('Failed to load topics. Please refresh the page.');
        } finally {
            UIHelpers.hideLoading();
        }
    }

    /**
     * Switch between cards and graph view
     * @param {string} view - 'cards' or 'graph'
     */
    switchView(view) {
        this.currentView = view;
        
        if (view === 'cards') {
            this.elements.topicsGrid.classList.add('view-active');
            this.elements.topicsGrid.classList.remove('view-hidden');
            this.elements.graphContainer.classList.add('view-hidden');
            this.elements.graphContainer.classList.remove('view-active');
            
            this.elements.cardsViewBtn.classList.add('active');
            this.elements.graphViewBtn.classList.remove('active');
        } else {
            this.elements.graphContainer.classList.add('view-active');
            this.elements.graphContainer.classList.remove('view-hidden');
            this.elements.topicsGrid.classList.add('view-hidden');
            this.elements.topicsGrid.classList.remove('view-active');
            
            this.elements.graphViewBtn.classList.add('active');
            this.elements.cardsViewBtn.classList.remove('active');
            
            // Fit graph when switching to it
            if (window.GraphRenderer) {
                setTimeout(() => GraphRenderer.fit(), 100);
            }
        }
    }

    /**
     * Render topic cards in the grid
     */
    renderTopicCards() {
        if (!this.knowledgeGraph || !this.knowledgeGraph.kg_nodes) {
            console.warn('No graph data to render cards');
            return;
        }

        const topicNodes = this.knowledgeGraph.kg_nodes.filter(node => node.group === 'topic');
        this.elements.topicsGrid.innerHTML = '';

        topicNodes.forEach(topic => {
            const card = document.createElement('div');
            card.className = 'topic-card';
            
            // Count connections (related resources)
            const connections = this.knowledgeGraph.kg_edges.filter(
                edge => edge.from === topic.id || edge.to === topic.id
            ).length;

            card.innerHTML = `
                <div class="topic-icon">
                    <i class="fas fa-book"></i>
                </div>
                <h3 class="topic-title">${topic.label}</h3>
                <p class="topic-summary">${topic.summary || 'Click to explore this topic'}</p>
                <div class="topic-meta">
                    <span><i class="fas fa-link"></i> ${connections} connections</span>
                </div>
            `;

            card.addEventListener('click', () => this.openTopicModal(topic));
            this.elements.topicsGrid.appendChild(card);
        });
    }

    /**
     * Render the graph visualization
     */
    renderGraph() {
        if (!this.knowledgeGraph || !this.elements.networkCanvas) {
            console.warn('Cannot render graph - missing data or container');
            return;
        }

        GraphRenderer.render(
            this.elements.networkCanvas,
            this.knowledgeGraph,
            {
                onTopicClick: (node) => this.openTopicModal(node),
                onFileClick: (node, indexedFiles) => this.handleFileClick(node, indexedFiles)
            }
        );
    }

    /**
     * Open topic modal - can be overridden by subclasses
     * @param {Object} topic - The topic node
     */
    openTopicModal(topic) {
        ModalManager.openTopicModal(topic, this.knowledgeGraph, {
            showIcon: this.showModalIcon || false,
            onOpen: (t) => this.logNodeClick(t.id, t.label, 'topic'),
            onResourceClick: (resource) => this.handleFileClick(resource, this.knowledgeGraph.indexed_files)
        });
    }

    /**
     * Handle file node click
     * @param {Object} node - The file node
     * @param {Object} indexedFiles - File index data
     */
    async handleFileClick(node, indexedFiles) {
        if (indexedFiles && indexedFiles[node.id]) {
            const fileData = indexedFiles[node.id];
            if (fileData.gcs_uri) {
                try {
                    const downloadUrl = await ApiClient.getDownloadUrl(fileData.gcs_uri);
                    window.open(downloadUrl, '_blank');
                } catch (error) {
                    console.error('Error downloading file:', error);
                    alert(`Failed to download ${fileData.display_name || node.label}. Please try again.`);
                }
            }
        } else {
            console.error('File not found in indexed_files');
        }
    }

    /**
     * Log a node click for analytics
     * @param {string} nodeId - The node ID
     * @param {string} nodeLabel - The node label
     * @param {string} nodeType - The node type
     */
    async logNodeClick(nodeId, nodeLabel, nodeType = 'topic') {
        await ApiClient.logNodeClick({
            playgroundId: this.playgroundId,
            nodeId,
            nodeLabel,
            nodeType,
            userId: this.userId
        });
    }
}

// Export for ES modules or attach to window
if (typeof window !== 'undefined') {
    window.BaseView = BaseView;
}
