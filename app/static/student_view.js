/**
 * STUDENT VIEW JAVASCRIPT
 * Interactive Knowledge Graph Exploration with Cards and Graph Views
 */

// Global state
let knowledgeGraph = null;
let currentTopic = null;
let chatMessages = [];
let network = null; // vis-network instance
let currentView = 'graph'; // 'cards' or 'graph' - default to graph
let isChatExpanded = false;

// DOM Elements
const topicsGrid = document.getElementById('topics-grid');
const graphContainer = document.getElementById('graph-container');
const networkCanvas = document.getElementById('network-canvas');
const cardsViewBtn = document.getElementById('cards-view-btn');
const graphViewBtn = document.getElementById('graph-view-btn');
const fitGraphBtn = document.getElementById('fit-graph-btn');
const resetZoomBtn = document.getElementById('reset-zoom-btn');
const topicModal = document.getElementById('topic-modal');
const modalTitle = document.getElementById('modal-topic-title');
const modalIcon = document.getElementById('modal-topic-icon');
const modalSummary = document.getElementById('modal-topic-summary');
const resourceList = document.getElementById('resource-list');
const modalClose = document.getElementById('modal-close');
const chatPrompt = document.getElementById('chat-prompt');
const promptInput = document.getElementById('prompt-input');
const chatExpandFab = document.getElementById('chat-expand-fab');
const chatContainer = document.getElementById('chat-container');
const chatCollapseBtn = document.getElementById('chat-collapse');
const chatHeader = document.querySelector('.chat-header');
const chatMessagesContainer = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');
const loadingOverlay = document.getElementById('loading-overlay');

// ===========================
// MARKDOWN & MATH RENDERING
// ===========================

/**
 * Render markdown with LaTeX math support
 * Supports inline math: $...$  and display math: $$...$$
 */
function renderMarkdownWithMath(content) {
    // First, render markdown
    let html = marked.parse(content);
    
    // Create a temporary div to manipulate the HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // Render all math expressions using KaTeX
    renderMathInElement(tempDiv, {
        delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false}
        ],
        throwOnError: false,
        trust: true
    });
    
    return tempDiv.innerHTML;
}

// ===========================
// INITIALIZATION
// ===========================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Student View initialized for course:', COURSE_ID);
    console.log('User:', USER_ID);

    initializeEventListeners();
    loadKnowledgeGraph();
});

function initializeEventListeners() {
    // View toggle handlers
    cardsViewBtn.addEventListener('click', () => switchView('cards'));
    graphViewBtn.addEventListener('click', () => switchView('graph'));
    
    // Graph controls
    fitGraphBtn.addEventListener('click', () => {
        if (network) network.fit();
    });
    resetZoomBtn.addEventListener('click', () => {
        if (network) {
            network.fit();
            network.moveTo({ scale: 1.0 });
        }
    });

    // Modal close handlers
    modalClose.addEventListener('click', closeModal);
    topicModal.addEventListener('click', (e) => {
        // Close if clicking directly on the modal (not the content)
        if (e.target === topicModal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (isChatExpanded) {
                collapseChat();
            } else if (!topicModal.classList.contains('hidden')) {
                closeModal();
            }
        }
    });

    // Prompt input - focus expands the prompt, Enter sends message
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && promptInput.value.trim()) {
            e.preventDefault();
            const query = promptInput.value.trim();
            chatInput.value = query;
            promptInput.value = '';
            sendMessage();
        }
    });

    // Floating expand button
    chatExpandFab.addEventListener('click', expandChat);

    // Chat collapse/expand toggle
    chatCollapseBtn.addEventListener('click', toggleChat);
    if (chatHeader) {
        chatHeader.addEventListener('click', toggleChat);
    }

    // Chat input handlers
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = chatInput.scrollHeight + 'px';
    });
}

// ===========================
// KNOWLEDGE GRAPH LOADING
// ===========================

async function loadKnowledgeGraph() {
    showLoading('Loading knowledge graph...');

    try {
        const response = await fetch(`/api/get-graph?course_id=${COURSE_ID}`);
        if (!response.ok) {
            throw new Error(`Failed to load graph: ${response.statusText}`);
        }

        const data = await response.json();
        
        // Parse the JSON strings into objects
        knowledgeGraph = {
            kg_nodes: JSON.parse(data.nodes),
            kg_edges: JSON.parse(data.edges),
            kg_data: JSON.parse(data.data)
        };

        console.log('Knowledge graph loaded:', knowledgeGraph);
        
        // Render both views (only one will be visible)
        renderTopicCards();
        renderGraph();
    } catch (error) {
        console.error('Error loading knowledge graph:', error);
        showError('Failed to load topics. Please refresh the page.');
    } finally {
        hideLoading();
    }
}

// ===========================
// VIEW SWITCHING
// ===========================

function switchView(view) {
    currentView = view;
    
    if (view === 'cards') {
        topicsGrid.classList.add('view-active');
        topicsGrid.classList.remove('view-hidden');
        graphContainer.classList.add('view-hidden');
        graphContainer.classList.remove('view-active');
        
        cardsViewBtn.classList.add('active');
        graphViewBtn.classList.remove('active');
    } else {
        graphContainer.classList.add('view-active');
        graphContainer.classList.remove('view-hidden');
        topicsGrid.classList.add('view-hidden');
        topicsGrid.classList.remove('view-active');
        
        graphViewBtn.classList.add('active');
        cardsViewBtn.classList.remove('active');
        
        // Fit graph when switching to it
        if (network) {
            setTimeout(() => network.fit(), 100);
        }
    }
}

// ===========================
// TOPIC CARDS RENDERING
// ===========================

function renderTopicCards() {
    if (!knowledgeGraph || !knowledgeGraph.kg_nodes) {
        console.warn('No graph data to render cards');
        return;
    }

    const topicNodes = knowledgeGraph.kg_nodes.filter(node => node.group === 'topic');
    topicsGrid.innerHTML = '';

    topicNodes.forEach(topic => {
        const card = document.createElement('div');
        card.className = 'topic-card';
        
        // Count connections (related resources)
        const connections = knowledgeGraph.kg_edges.filter(
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

        card.addEventListener('click', () => openTopicModal(topic));
        topicsGrid.appendChild(card);
    });
}

// ===========================
// CHAT INTERFACE
// ===========================

function toggleChat() {
    if (isChatExpanded) {
        collapseChat();
    } else {
        expandChat();
    }
}

function expandChat() {
    isChatExpanded = true;
    chatContainer.classList.remove('collapsed');
    chatContainer.classList.add('expanded');
    
    // Hide floating button when chat is expanded
    chatExpandFab.classList.remove('visible');
    
    // Rotate arrow
    const collapseIcon = document.getElementById('collapse-icon');
    if (collapseIcon) {
        collapseIcon.style.transform = 'rotate(180deg)';
    }
    
    collapseIcon.onclick = collapseChat;
    
    // Focus on chat input
    setTimeout(() => chatInput.focus(), 300);
}

function collapseChat() {
    isChatExpanded = false;
    chatContainer.classList.remove('expanded');
    chatContainer.classList.add('collapsed');
    
    // Show floating button when chat is collapsed
    chatExpandFab.classList.add('visible');
    
    // Rotate arrow back
    const collapseIcon = document.getElementById('collapse-icon');
    if (collapseIcon) {
        collapseIcon.style.transform = 'rotate(0deg)';
    }
    collapseIcon.onclick = expandChat;
}

// ===========================
// GRAPH VISUALIZATION
// ===========================

function renderGraph() {
    if (!knowledgeGraph || !knowledgeGraph.kg_nodes || !knowledgeGraph.kg_edges) {
        console.warn('No graph data to render');
        return;
    }

    // Prepare nodes for vis-network
    const nodes = knowledgeGraph.kg_nodes.map(node => {
        const isTopicNode = node.group === 'topic';
        
        return {
            id: node.id,
            label: node.label,
            title: node.label, // Tooltip
            group: node.group,
            color: isTopicNode ? {
                background: '#6366f1',
                border: '#4f46e5',
                highlight: {
                    background: '#818cf8',
                    border: '#6366f1'
                }
            } : {
                background: '#10b981',
                border: '#059669',
                highlight: {
                    background: '#34d399',
                    border: '#10b981'
                }
            },
            font: {
                color: '#ffffff',
                size: isTopicNode ? 18 : 15,
                face: 'Arial',
                bold: isTopicNode ? true : false
            },
            shape: isTopicNode ? 'box' : 'ellipse',
            size: isTopicNode ? 25 : 20,
            borderWidth: 2,
            shadow: true,
            margin: isTopicNode ? 15 : 10
        };
    });

    // Prepare edges for vis-network - flexible, flowing curves
    const edges = knowledgeGraph.kg_edges.map(edge => ({
        from: edge.from,
        to: edge.to,
        arrows: {
            to: {
                enabled: true,
                scaleFactor: 1,
                type: 'arrow'
            }
        },
        color: {
            color: '#cbd5e1',
            highlight: '#6366f1'
        },
        width: 2,
        smooth: {
            enabled: true,
            type: 'dynamic',
            roundness: 0.5
        }
    }));

    // Create network
    const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };

    const options = {
        layout: {
            improvedLayout: true,
            hierarchical: false
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -800,
                centralGravity: 0.3,
                springLength: 120,
                springConstant: 0.04,
                damping: 0.2,
                avoidOverlap: 0.1
            },
            stabilization: {
                iterations: 250,
                updateInterval: 25
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
        edges: {
            smooth: {
                type: 'continuous'
            }
        },
        configure: {
            enabled: false
        },
        // Constrain nodes to stay within viewport
        autoResize: true,
        width: '100%',
        height: '100%'
    };

    // Initialize network
    network = new vis.Network(networkCanvas, data, options);

    // Track dragging to prevent opening modal on drag
    let isDragging = false;
    let clickPosition = null;
    
    network.on('dragStart', function(params) {
        isDragging = true;
        clickPosition = params.pointer.canvas;
    });
    
    network.on('dragEnd', function() {
        setTimeout(() => {
            isDragging = false;
        }, 100);
    });

    // Handle node clicks - only if not dragging
    network.on('click', function(params) {
        // Only open modal if we didn't drag and clicked on a topic node
        if (!isDragging && params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = knowledgeGraph.kg_nodes.find(n => n.id === nodeId);
            
            if (node && node.group === 'topic') {
                openTopicModal(node);
            }
        }
    });

    // Fit graph after stabilization
    network.once('stabilizationIterationsDone', function() {
        network.fit();
    });
}

// ===========================
// MODAL FUNCTIONALITY
// ===========================

async function openTopicModal(topic) {
    currentTopic = topic;

    // Get topic data
    const topicData = knowledgeGraph.kg_data && knowledgeGraph.kg_data[topic.id] 
        ? knowledgeGraph.kg_data[topic.id] 
        : {};

    const summary = topicData.summary || 'No detailed summary available for this topic yet.';
    
    // Get icon based on topic index
    const topicIndex = knowledgeGraph.kg_nodes.findIndex(n => n.id === topic.id);
    const icons = ['📚', '🧠', '💡', '🔬', '🎯', '🚀', '⚡', '🌟', '🎨', '🔥', '💎', '🌈', '🎭', '🏆', '🎪'];
    const icon = icons[topicIndex % icons.length];

    // Update modal content
    modalTitle.textContent = topic.label;
    modalIcon.textContent = icon;
    modalSummary.innerHTML = renderMarkdownWithMath(summary);

    // Get related resources
    const relatedResources = getRelatedResources(topic.id);
    renderRelatedResources(relatedResources);

    // Show modal with animation
    topicModal.classList.remove('hidden');
    setTimeout(() => topicModal.classList.add('show'), 10);

    // Log node click for analytics
    logNodeClick(topic.id, topic.label, 'topic');
}

function closeModal() {
    topicModal.classList.remove('show');
    setTimeout(() => {
        topicModal.classList.add('hidden');
        currentTopic = null;
    }, 300);
}

function getRelatedResources(topicId) {
    if (!knowledgeGraph.kg_edges || !knowledgeGraph.kg_nodes) return [];

    const relatedNodeIds = new Set();
    
    // Find all connected nodes
    knowledgeGraph.kg_edges.forEach(edge => {
        if (edge.from === topicId) relatedNodeIds.add(edge.to);
        if (edge.to === topicId) relatedNodeIds.add(edge.from);
    });

    // Get node details
    const resources = [];
    relatedNodeIds.forEach(nodeId => {
        const node = knowledgeGraph.kg_nodes.find(n => n.id === nodeId);
        if (node && node.group === 'resource') {
            resources.push(node);
        }
    });

    return resources;
}

function renderRelatedResources(resources) {
    if (resources.length === 0) {
        resourceList.innerHTML = '<li style="cursor: default;">No resources linked yet</li>';
        return;
    }

    resourceList.innerHTML = '';
    resources.forEach(resource => {
        const li = document.createElement('li');
        li.textContent = resource.label;
        li.dataset.resourceId = resource.id;
        li.addEventListener('click', () => openResource(resource));
        resourceList.appendChild(li);
    });
}

function openResource(resource) {
    // Get resource data
    const resourceData = knowledgeGraph.kg_data && knowledgeGraph.kg_data[resource.id] 
        ? knowledgeGraph.kg_data[resource.id] 
        : {};

    if (resourceData.url) {
        window.open(resourceData.url, '_blank');
    } else {
        alert(`Resource: ${resource.label}\n\nNo URL available for this resource.`);
    }
}

// ===========================
// CHAT FUNCTIONALITY
// ===========================

async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Expand chat if not already expanded
    if (!isChatExpanded) {
        expandChat();
    }

    // Disable input while sending
    chatInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message to chat
    addMessage({
        role: 'user',
        content: query
    });

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Show typing indicator
    typingIndicator.classList.remove('hidden');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                course_id: COURSE_ID,
                query: query
            })
        });

        if (!response.ok) {
            throw new Error(`Chat request failed: ${response.statusText}`);
        }

        const data = await response.json();

        // Add bot response
        addMessage({
            role: 'assistant',
            content: data.answer || data.response || 'I received your question but had trouble generating an answer.',
            sources: data.sources || []
        });

    } catch (error) {
        console.error('Error sending message:', error);
        addMessage({
            role: 'assistant',
            content: 'Sorry, I encountered an error processing your question. Please try again.',
            sources: []
        });
    } finally {
        typingIndicator.classList.add('hidden');
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

function addMessage(message) {
    chatMessages.push(message);

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.role === 'user' ? 'user-message' : 'bot-message'}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = message.role === 'user' ? '👤' : '🤖';

    const content = document.createElement('div');
    content.className = 'message-content';

    const text = document.createElement('div');
    // Render markdown with math for assistant messages, plain text for user messages
    if (message.role === 'user') {
        text.textContent = message.content;
    } else {
        text.innerHTML = renderMarkdownWithMath(message.content);
    }
    content.appendChild(text);

    // Add sources if available
    if (message.sources && message.sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';
        sourcesDiv.innerHTML = '<strong>Sources:</strong>';
        
        message.sources.forEach(source => {
            // Handle both old string format and new object format
            if (typeof source === 'string') {
                // Old format: just a filename string
                const sourceTag = document.createElement('span');
                sourceTag.className = 'source-tag';
                sourceTag.textContent = source;
                sourcesDiv.appendChild(sourceTag);
            } else if (source.filename && source.source_uri) {
                // New format: object with filename and source_uri
                const sourceLink = document.createElement('a');
                sourceLink.className = 'source-tag source-link';
                sourceLink.textContent = source.filename;
                sourceLink.href = '#';
                sourceLink.title = `Download ${source.filename}`;
                
                // Add click handler to get signed URL and download
                sourceLink.addEventListener('click', async (e) => {
                    e.preventDefault();
                    await downloadSource(source.source_uri, source.filename);
                });
                
                sourcesDiv.appendChild(sourceLink);
            }
        });

        content.appendChild(sourcesDiv);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatMessagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

/**
 * Downloads a source file from GCS using a signed URL
 */
async function downloadSource(gcsUri, filename) {
    try {
        // Fetch signed URL from backend
        const response = await fetch(`/api/download-source?gcs_uri=${encodeURIComponent(gcsUri)}`);
        
        if (!response.ok) {
            throw new Error('Failed to get download URL');
        }
        
        const data = await response.json();
        const downloadUrl = data.download_url;
        
        // Open the signed URL in a new tab to trigger download
        window.open(downloadUrl, '_blank');
        
    } catch (error) {
        console.error('Error downloading source:', error);
        alert(`Failed to download ${filename}. Please try again.`);
    }
}

// ===========================
// ANALYTICS
// ===========================

async function logNodeClick(nodeId, nodeLabel, nodeType = 'topic') {
    try {
        await fetch('/api/log-node-click', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                course_id: COURSE_ID,
                node_id: nodeId,
                node_label: nodeLabel,
                node_type: nodeType,
                user_id: USER_ID,
                timestamp: new Date().toISOString()
            })
        });
    } catch (error) {
        console.error('Error logging node click:', error);
        // Don't show error to user - analytics failures shouldn't block UX
    }
}

// ===========================
// UI HELPERS
// ===========================

function showLoading(message = 'Loading...') {
    const overlay = loadingOverlay;
    const p = overlay.querySelector('p');
    p.textContent = message;
    overlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function showError(message) {
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ef4444;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);
