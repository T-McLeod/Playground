/**
 * Graph Renderer
 * Handles vis-network graph visualization for knowledge graphs
 */

const GraphRenderer = {
    network: null,
    isDragging: false,

    /**
     * Node styling configuration
     */
    nodeStyles: {
        topic: {
            color: {
                background: '#001A57',  // Duke Blue for topics
                border: '#00134a',
                highlight: {
                    background: '#1e3a6e',
                    border: '#001A57'
                }
            },
            font: {
                color: '#ffffff',
                size: 20,
                face: 'Inter, Arial, sans-serif',
                bold: true
            },
            shape: 'box',
            size: 30,
            borderWidth: 2,
            shadow: true,
            margin: 18
        },
        file: {
            color: {
                background: '#a8c8f0',  // Pastel blue for sources
                border: '#7eb0e8',
                highlight: {
                    background: '#d4e4f7',
                    border: '#a8c8f0'
                }
            },
            font: {
                color: '#1e293b',
                size: 15,
                face: 'Inter, Arial, sans-serif',
                bold: false
            },
            shape: 'ellipse',
            size: 20,
            borderWidth: 2,
            shadow: true,
            margin: 8
        }
    },

    /**
     * Default physics options for the graph
     */
    defaultPhysicsOptions: {
        enabled: true,
        barnesHut: {
            gravitationalConstant: -1200,
            centralGravity: 0.05,
            springLength: 250,
            springConstant: 0.005,
            damping: 0.25,
            avoidOverlap: 0.2
        },
        stabilization: {
            iterations: 300,
            updateInterval: 25
        }
    },

    /**
     * Prepare nodes for vis-network
     * @param {Array} nodes - Raw node data from the knowledge graph
     * @returns {Array} Formatted nodes for vis-network
     */
    prepareNodes(nodes) {
        return nodes.map(node => {
            const isTopicNode = node.group === 'topic';
            const style = isTopicNode ? this.nodeStyles.topic : this.nodeStyles.file;

            return {
                id: node.id,
                label: node.label,
                title: node.label, // Tooltip
                group: node.group,
                color: style.color,
                font: style.font,
                shape: style.shape,
                size: style.size,
                borderWidth: style.borderWidth,
                shadow: style.shadow,
                margin: style.margin
            };
        });
    },

    /**
     * Prepare edges for vis-network
     * @param {Array} edges - Raw edge data from the knowledge graph
     * @returns {Array} Formatted edges for vis-network
     */
    prepareEdges(edges) {
        return edges.map(edge => ({
            from: edge.from,
            to: edge.to,
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 0.8,
                    type: 'arrow'
                }
            },
            color: {
                color: '#cbd5e1',
                highlight: '#001A57'
            },
            width: 2,
            smooth: {
                enabled: true,
                type: 'dynamic',
                roundness: 0.5
            },
            length: 200
        }));
    },

    /**
     * Get default network options
     * @param {Object} customPhysics - Optional custom physics options
     * @returns {Object} Network options
     */
    getNetworkOptions(customPhysics = null) {
        return {
            layout: {
                improvedLayout: true,
                hierarchical: false,
                randomSeed: 2
            },
            physics: customPhysics || this.defaultPhysicsOptions,
            edges: {
                smooth: {
                    type: 'dynamic',
                    forceDirection: 'horizontal',
                    roundness: 0.5
                },
                endPointOffset: {
                    from: 0,
                    to: 15
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                navigationButtons: true,
                keyboard: true,
                zoomView: true,
                dragView: true
            },
            nodes: {
                shape: 'box',
                margin: 15,
                widthConstraint: {
                    maximum: 250
                },
                borderWidth: 2,
                borderWidthSelected: 3
            },
            configure: {
                enabled: false
            },
            autoResize: true,
            width: '100%',
            height: '100%'
        };
    },

    /**
     * Render the knowledge graph
     * @param {HTMLElement} container - The container element
     * @param {Object} knowledgeGraph - The knowledge graph data
     * @param {Object} callbacks - Callbacks for node clicks
     * @param {Object} options - Optional custom options
     * @returns {Object} The vis-network instance
     */
    render(container, knowledgeGraph, callbacks = {}, options = {}) {
        if (!knowledgeGraph || !knowledgeGraph.kg_nodes || !knowledgeGraph.kg_edges) {
            console.warn('No graph data to render');
            return null;
        }

        // Prepare data
        const nodes = this.prepareNodes(knowledgeGraph.kg_nodes);
        const edges = this.prepareEdges(knowledgeGraph.kg_edges);

        const data = {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        };

        const networkOptions = this.getNetworkOptions(options.physics);

        // Create network
        this.network = new vis.Network(container, data, networkOptions);

        // Track dragging to prevent opening modal on drag
        this.isDragging = false;

        this.network.on('dragStart', () => {
            this.isDragging = true;
        });

        this.network.on('dragEnd', () => {
            setTimeout(() => {
                this.isDragging = false;
            }, 100);
        });

        // Handle node clicks
        this.network.on('click', (params) => {
            if (!this.isDragging && params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const node = knowledgeGraph.kg_nodes.find(n => n.id === nodeId);

                if (node) {
                    if (node.group === 'topic' && callbacks.onTopicClick) {
                        callbacks.onTopicClick(node);
                    } else if ((node.group === 'file_pdf' || node.group === 'file') && callbacks.onFileClick) {
                        callbacks.onFileClick(node, knowledgeGraph.indexed_files);
                    }
                }
            }
        });

        // Fit graph after stabilization
        this.network.once('stabilizationIterationsDone', () => {
            this.network.fit();
        });

        return this.network;
    },

    /**
     * Fit the graph to the viewport
     */
    fit() {
        if (this.network) {
            this.network.fit();
        }
    },

    /**
     * Reset zoom to default
     */
    resetZoom() {
        if (this.network) {
            this.network.fit();
            this.network.moveTo({ scale: 1.0 });
        }
    },

    /**
     * Destroy the network instance
     */
    destroy() {
        if (this.network) {
            this.network.destroy();
            this.network = null;
        }
    }
};

// Export for ES modules or attach to window
if (typeof window !== 'undefined') {
    window.GraphRenderer = GraphRenderer;
}
