// ROLE 1: Frontend Developer - All client-side logic here

// State management
let currentState = APP_STATE;
let graphData = null;
let network = null;

// Initialize the UI based on the current state
function initializeUI() {
    // Hide all pages
    document.querySelectorAll('.page-state').forEach(page => {
        page.style.display = 'none';
    });

    // Show the appropriate page based on state
    switch (currentState) {
        case 'NEEDS_INIT':
            document.getElementById('init-page').style.display = 'block';
            setupInitPage();
            break;
        case 'NOT_READY':
            document.getElementById('not-ready-page').style.display = 'block';
            break;
        case 'GENERATING':
            document.getElementById('loading-page').style.display = 'block';
            pollForCompletion();
            break;
        case 'ACTIVE':
            document.getElementById('app-page').style.display = 'block';
            setupAppPage();
            break;
    }
}

// Setup the initialization page
function setupInitPage() {
    // Show landing screen with "Generate Now!" button
    const generateNowBtn = document.getElementById('generate-now-btn');
    
    if (generateNowBtn) {
        generateNowBtn.addEventListener('click', () => {
            startTopicGeneration();
        });
    }
}

// Start the topic generation process
function startTopicGeneration() {
    // Hide landing screen
    document.getElementById('landing-screen').style.display = 'none';
    
    // Show loading
    document.getElementById('init-loading').style.display = 'block';
    
    // Attempt to load AI-suggested topics
    loadSuggestedTopics();
}

// Load AI-suggested topics from the backend
async function loadSuggestedTopics() {
    const loadingDiv = document.getElementById('init-loading');
    const editorDiv = document.getElementById('init-editor');
    
    try {
        const response = await fetch('/api/generate-suggested-topics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course_id: COURSE_ID })
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate topics');
        }
        
        const topicsData = await response.json();
        
        // Hide loading, show editor
        loadingDiv.style.display = 'none';
        editorDiv.style.display = 'block';
        
        // Render the editable topics
        renderTopicEditor(topicsData);
        
        // Setup event handlers
        setupTopicEditorHandlers();
        
    } catch (error) {
        console.error('Failed to generate topics:', error);
        
        // Show enhanced error message with Airbnb-style design
        loadingDiv.innerHTML = `
            <div class="generation-failed">
                <div class="error-illustration">
                    <div class="sad-face">
                        <div class="face-circle">
                            <div class="eye left-eye"></div>
                            <div class="eye right-eye"></div>
                            <div class="mouth"></div>
                        </div>
                        <div class="sparkle sparkle-1">✨</div>
                        <div class="sparkle sparkle-2">⚡</div>
                        <div class="sparkle sparkle-3">💫</div>
                    </div>
                </div>
                <h2 class="error-title">Oops!</h2>
                <p class="error-message">We can't seem to generate topics automatically right now.</p>
                <p class="error-hint">But don't worry! You can still create an amazing course by adding topics manually.</p>
                <button id="start-manual-btn" class="manual-btn">
                    <span class="btn-icon">✏️</span>
                    <span class="btn-text">Create Topics Manually</span>
                </button>
            </div>
        `;
        
        // Add event listener to the manual button
        document.getElementById('start-manual-btn').addEventListener('click', () => {
            loadingDiv.style.display = 'none';
            editorDiv.style.display = 'block';
            
            // Start with one blank topic
            renderTopicEditor([{ 
                topic: 'My First Topic', 
                summary: 'Click to edit this topic and add your course content.' 
            }]);
            setupTopicEditorHandlers();
        });
    }
}

// Calculate node size based on text content (returns width and height for ovals)
function calculateNodeSize(topic, summary, skipVariation = false) {
    // Calculate total text length
    const topicLength = topic.length;
    const summaryLength = summary.length;
    const totalLength = topicLength + summaryLength;
    
    // Also consider the number of lines in summary (newlines increase height)
    const summaryLines = summary.split('\n').length;
    const lineHeightFactor = Math.max(1, summaryLines * 0.3);
    
    // Define size ranges for horizontal ovals (width > height)
    // Width ranges from 240px to 600px (increased max for longer content)
    // Height ranges from 120px to 350px (increased max for longer content)
    let width, height;
    
    if (totalLength < 80) {
        width = 240;
        height = 120;
    } else if (totalLength < 120) {
        width = 300;
        height = 140;
    } else if (totalLength < 160) {
        width = 340;
        height = 160;
    } else if (totalLength < 200) {
        width = 380;
        height = 180;
    } else if (totalLength < 250) {
        width = 420;
        height = 210;
    } else if (totalLength < 300) {
        width = 460;
        height = 240;
    } else if (totalLength < 400) {
        width = 520;
        height = 280;
    } else if (totalLength < 500) {
        width = 560;
        height = 310;
    } else {
        width = 600;
        height = 350;
    }
    
    // Adjust height based on line count
    height = Math.min(350, height * lineHeightFactor);
    
    // Add slight variation for more organic look (only on initial render)
    if (!skipVariation) {
        const widthVariation = Math.random() * 20 - 10; // -10 to +10
        const heightVariation = Math.random() * 15 - 7.5; // -7.5 to +7.5
        
        return {
            width: Math.max(240, Math.min(600, width + widthVariation)),
            height: Math.max(120, Math.min(350, height + heightVariation))
        };
    }
    
    return {
        width: Math.max(240, Math.min(600, width)),
        height: Math.max(120, Math.min(350, height))
    };
}

// Render the topic editor with visual nodes
function renderTopicEditor(topicsData) {
    const canvas = document.getElementById('topic-canvas');
    canvas.innerHTML = ''; // Clear existing
    
    // Store topics data globally for easy access
    window.topicsData = topicsData;
    
    // Calculate sizes for each node (now returns {width, height})
    const nodeSizes = topicsData.map(item => 
        calculateNodeSize(item.topic, item.summary)
    );
    window.nodeSizes = nodeSizes;
    
    // Calculate positions for nodes (distributed layout)
    const positions = calculateNodePositions(topicsData.length, nodeSizes);
    
    topicsData.forEach((item, index) => {
        const node = document.createElement('div');
        node.className = `topic-node color-${(index % 6) + 1}`;
        node.dataset.index = index;
        
        // Set dynamic size (width and height for oval)
        const size = nodeSizes[index];
        node.style.width = size.width + 'px';
        node.style.height = size.height + 'px';
        
        // Set position
        node.style.left = positions[index].x + 'px';
        node.style.top = positions[index].y + 'px';
        
        // Create delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'node-delete-btn';
        deleteBtn.dataset.index = index;
        deleteBtn.innerHTML = '&times;';
        
        // Create editable title
        const title = document.createElement('div');
        title.className = 'node-title';
        title.contentEditable = 'true';
        title.textContent = item.topic;
        title.dataset.index = index;
        title.dataset.field = 'topic';
        
        // Create editable summary
        const summary = document.createElement('div');
        summary.className = 'node-summary';
        summary.contentEditable = 'true';
        summary.textContent = item.summary;
        summary.dataset.index = index;
        summary.dataset.field = 'summary';
        
        // Add elements to node
        node.appendChild(deleteBtn);
        node.appendChild(title);
        node.appendChild(summary);
        
        // Setup inline editing handlers
        setupInlineEditHandlers(title, index, 'topic');
        setupInlineEditHandlers(summary, index, 'summary');
        
        canvas.appendChild(node);
    });
}

// Calculate positions for nodes in an attractive layout
function calculateNodePositions(count, nodeSizes = null) {
    const canvas = document.getElementById('topic-canvas');
    const canvasWidth = canvas.offsetWidth || 800;
    const canvasHeight = 500;
    
    // Use provided sizes or defaults (now {width, height} objects)
    const sizes = nodeSizes || Array(count).fill({ width: 340, height: 160 });
    const padding = 40;
    
    const positions = [];
    
    if (count === 1) {
        positions.push({
            x: (canvasWidth - sizes[0].width) / 2,
            y: (canvasHeight - sizes[0].height) / 2
        });
    } else if (count === 2) {
        positions.push(
            { x: canvasWidth * 0.25 - sizes[0].width / 2, y: (canvasHeight - sizes[0].height) / 2 },
            { x: canvasWidth * 0.75 - sizes[1].width / 2, y: (canvasHeight - sizes[1].height) / 2 }
        );
    } else if (count === 3) {
        positions.push(
            { x: padding, y: padding },
            { x: canvasWidth - sizes[1].width - padding, y: canvasHeight * 0.4 },
            { x: canvasWidth * 0.3, y: canvasHeight - sizes[2].height - padding }
        );
    } else {
        // For 4+ nodes, arrange in a scattered grid pattern
        const cols = Math.ceil(Math.sqrt(count));
        const rows = Math.ceil(count / cols);
        const cellWidth = (canvasWidth - padding * 2) / cols;
        const cellHeight = (canvasHeight - padding * 2) / rows;
        
        for (let i = 0; i < count; i++) {
            const row = Math.floor(i / cols);
            const col = i % cols;
            const nodeSize = sizes[i];
            
            // Add some randomness for a more organic look
            const randomX = (Math.random() - 0.5) * 40;
            const randomY = (Math.random() - 0.5) * 30;
            
            positions.push({
                x: padding + col * cellWidth + (cellWidth - nodeSize.width) / 2 + randomX,
                y: padding + row * cellHeight + (cellHeight - nodeSize.height) / 2 + randomY
            });
        }
    }
    
    return positions;
}

// Setup inline editing handlers for a contentEditable element
function setupInlineEditHandlers(element, index, field) {
    const node = element.closest('.topic-node');
    
    // Prevent click from propagating to node
    element.addEventListener('click', (e) => {
        e.stopPropagation();
    });
    
    // Focus event - zoom in and center the node
    element.addEventListener('focus', () => {
        zoomToNode(node);
    });
    
    // Save on blur (when user clicks away)
    element.addEventListener('blur', () => {
        const newValue = element.textContent.trim();
        if (newValue && window.topicsData[index]) {
            window.topicsData[index][field] = newValue;
            
            // Recalculate and apply new size based on updated content
            resizeNodeAfterEdit(node, index);
        }
        
        // Check if no other element in this node is focused
        setTimeout(() => {
            const activeElement = document.activeElement;
            const isInSameNode = activeElement && activeElement.closest('.topic-node') === node;
            if (!isInSameNode) {
                zoomOutNode(node);
            }
        }, 10);
    });
    
    // Prevent Enter key from creating new lines in title
    if (field === 'topic') {
        element.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                element.blur(); // Save and exit editing
            }
        });
    }
    
    // Allow Enter in summary but save on Escape
    element.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            element.blur(); // Save and exit editing
        }
    });
}

// Resize node after editing to fit content
function resizeNodeAfterEdit(node, index) {
    if (!window.topicsData[index]) return;
    
    const topic = window.topicsData[index].topic;
    const summary = window.topicsData[index].summary;
    
    // Calculate new size based on updated content
    const newSize = calculateNodeSize(topic, summary);
    
    // Update stored size
    if (window.nodeSizes) {
        window.nodeSizes[index] = newSize;
    }
    
    // Apply new size with smooth transition
    node.style.width = newSize.width + 'px';
    node.style.height = newSize.height + 'px';
}

// Zoom in and center a node
function zoomToNode(node) {
    const canvas = document.getElementById('topic-canvas');
    const allNodes = canvas.querySelectorAll('.topic-node');
    
    // Get node's current position
    const nodeRect = node.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();
    
    // Calculate center position relative to canvas
    const currentCenterX = nodeRect.left + nodeRect.width / 2 - canvasRect.left;
    const currentCenterY = nodeRect.top + nodeRect.height / 2 - canvasRect.top;
    
    // Calculate target center position (middle of canvas)
    const targetCenterX = canvasRect.width / 2;
    const targetCenterY = canvasRect.height / 2;
    
    // Calculate offset needed
    const offsetX = targetCenterX - currentCenterX;
    const offsetY = targetCenterY - currentCenterY;
    
    // Store original position
    node.dataset.originalLeft = node.style.left;
    node.dataset.originalTop = node.style.top;
    
    // Apply focused class and adjust position
    node.classList.add('focused');
    
    // Adjust position to center (accounting for scale)
    const currentLeft = parseFloat(node.style.left);
    const currentTop = parseFloat(node.style.top);
    node.style.left = (currentLeft + offsetX) + 'px';
    node.style.top = (currentTop + offsetY) + 'px';
    
    // Dim all other nodes
    allNodes.forEach(otherNode => {
        if (otherNode !== node) {
            otherNode.classList.add('dimmed');
        }
    });
}

// Zoom out and restore node position
function zoomOutNode(node) {
    const canvas = document.getElementById('topic-canvas');
    const allNodes = canvas.querySelectorAll('.topic-node');
    
    // Restore original position
    if (node.dataset.originalLeft) {
        node.style.left = node.dataset.originalLeft;
        node.style.top = node.dataset.originalTop;
    }
    
    // Remove focused class
    node.classList.remove('focused');
    
    // Restore all other nodes
    allNodes.forEach(otherNode => {
        otherNode.classList.remove('dimmed');
    });
}

// Setup event handlers for the topic editor
function setupTopicEditorHandlers() {
    // Handle "Add Custom Topic" button
    const addBtn = document.getElementById('add-topic-btn');
    addBtn.addEventListener('click', () => {
        addBlankTopicItem();
    });
    
    // Handle "Generate Course" button
    const generateBtn = document.getElementById('generate-course-btn');
    generateBtn.addEventListener('click', () => {
        submitTopicsData();
    });
    
    // Delegate delete button clicks on canvas
    const canvas = document.getElementById('topic-canvas');
    canvas.addEventListener('click', (e) => {
        if (e.target.classList.contains('node-delete-btn')) {
            e.stopPropagation();
            const index = parseInt(e.target.dataset.index);
            deleteTopicNode(index);
        }
    });
}

// Setup modal event handlers
function setupModalHandlers() {
    const modal = document.getElementById('edit-modal');
    const closeBtn = modal.querySelector('.modal-close');
    const cancelBtn = document.getElementById('cancel-edit-btn');
    const saveBtn = document.getElementById('save-topic-btn');
    
    // Close modal
    closeBtn.addEventListener('click', closeEditModal);
    cancelBtn.addEventListener('click', closeEditModal);
    
    // Close when clicking outside modal
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeEditModal();
        }
    });
    
    // Save changes
    saveBtn.addEventListener('click', saveTopicChanges);
}

// Open edit modal for a topic
function openEditModal(index) {
    const modal = document.getElementById('edit-modal');
    const topic = window.topicsData[index];
    
    // Populate modal fields
    document.getElementById('edit-topic-name').value = topic.topic;
    document.getElementById('edit-topic-summary').value = topic.summary;
    
    // Store current index
    modal.dataset.editingIndex = index;
    
    // Show modal
    modal.style.display = 'flex';
}

// Close edit modal
function closeEditModal() {
    const modal = document.getElementById('edit-modal');
    modal.style.display = 'none';
    delete modal.dataset.editingIndex;
}

// Save topic changes from modal
function saveTopicChanges() {
    const modal = document.getElementById('edit-modal');
    const index = parseInt(modal.dataset.editingIndex);
    
    const newTopic = document.getElementById('edit-topic-name').value.trim();
    const newSummary = document.getElementById('edit-topic-summary').value.trim();
    
    if (!newTopic || !newSummary) {
        alert('Please fill in both topic name and summary.');
        return;
    }
    
    // Update data
    window.topicsData[index] = {
        topic: newTopic,
        summary: newSummary
    };
    
    // Re-render nodes
    renderTopicEditor(window.topicsData);
    
    // Close modal
    closeEditModal();
}

// Add a blank topic node
function addBlankTopicItem() {
    if (!window.topicsData) {
        window.topicsData = [];
    }
    
    // Add new blank topic to data
    window.topicsData.push({
        topic: 'New Topic',
        summary: 'Click to edit this topic summary.'
    });
    
    // Re-render all nodes
    renderTopicEditor(window.topicsData);
    
    // Focus on the new topic's title for immediate editing
    setTimeout(() => {
        const canvas = document.getElementById('topic-canvas');
        const newNodes = canvas.querySelectorAll('.topic-node');
        const newNode = newNodes[newNodes.length - 1];
        if (newNode) {
            const titleElement = newNode.querySelector('.node-title');
            if (titleElement) {
                titleElement.focus();
                // Select all text for easy replacement
                const range = document.createRange();
                range.selectNodeContents(titleElement);
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }
    }, 100);
}

// Delete a topic node
function deleteTopicNode(index) {
    if (window.topicsData.length <= 1) {
        alert('You must have at least one topic.');
        return;
    }
    
    if (confirm('Are you sure you want to delete this topic?')) {
        // Remove from data
        window.topicsData.splice(index, 1);
        
        // Re-render nodes
        renderTopicEditor(window.topicsData);
    }
}

// Collect topics data and submit to backend
async function submitTopicsData() {
    const generateBtn = document.getElementById('generate-course-btn');
    
    // Use the global topics data
    const topicsData = window.topicsData || [];
    
    // Validate data
    const validTopics = topicsData.filter(item => 
        item.topic && item.topic.trim() && 
        item.summary && item.summary.trim()
    );
    
    if (validTopics.length === 0) {
        alert('Please add at least one topic with both a name and summary.');
        return;
    }
    
    // Disable button and show loading state
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';
    
    // Animate nodes spreading out and removing delete buttons
    await animateNodesForGeneration();
    
        try {
            const response = await fetch('/api/initialize-course', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                course_id: COURSE_ID, 
                topics_data: validTopics 
            })
            });
            
            const result = await response.json();
            
        if (result.status === 'generating' || result.status === 'complete') {
            // Hide the generate button
            const generateAction = document.querySelector('.generate-action');
            if (generateAction) {
                generateAction.style.display = 'none';
            }
            
            // Show chat interface
            showChatInterface();
        } else {
            throw new Error('Unexpected response status');
        }
        
        } catch (error) {
        console.error('Course generation failed:', error);
        alert('Failed to generate course. Please try again.');
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Course';
    }
}

// Animate nodes spreading out and hide delete buttons
async function animateNodesForGeneration() {
    const canvas = document.getElementById('topic-canvas');
    const nodes = canvas.querySelectorAll('.topic-node');
    const addBtn = document.getElementById('add-topic-btn');
    
    // Hide add button and delete buttons
    if (addBtn) {
        addBtn.style.opacity = '0';
        addBtn.style.pointerEvents = 'none';
    }
    
    // Add finalizing class to canvas
    canvas.classList.add('finalizing');
    
    // Fade out all delete buttons and disable editing
    nodes.forEach(node => {
        const deleteBtn = node.querySelector('.node-delete-btn');
        if (deleteBtn) {
            deleteBtn.style.opacity = '0';
            deleteBtn.style.pointerEvents = 'none';
        }
        
        // Disable editing on title and summary
        const title = node.querySelector('.node-title');
        const summary = node.querySelector('.node-summary');
        if (title) {
            title.contentEditable = 'false';
            title.style.cursor = 'default';
        }
        if (summary) {
            summary.contentEditable = 'false';
            summary.style.cursor = 'default';
        }
        
        // Remove hover effects
        node.style.cursor = 'default';
    });
    
    // Calculate new evenly distributed positions
    const newPositions = calculateEvenlySpreadPositions(nodes.length);
    
    // Animate each node to its new position
    nodes.forEach((node, index) => {
        const newPos = newPositions[index];
        node.style.transition = 'all 1s cubic-bezier(0.4, 0, 0.2, 1)';
        node.style.left = newPos.x + 'px';
        node.style.top = newPos.y + 'px';
        node.style.transform = 'scale(1.05)';
    });
    
    // Wait for animation to complete
    return new Promise(resolve => {
        setTimeout(() => {
            nodes.forEach(node => {
                node.style.transform = 'scale(1)';
            });
            setTimeout(resolve, 300);
        }, 1000);
    });
}

// Calculate evenly spread positions in a circular/grid pattern
function calculateEvenlySpreadPositions(count) {
    const canvas = document.getElementById('topic-canvas');
    const canvasWidth = canvas.offsetWidth || 1200;
    const canvasHeight = canvas.offsetHeight || 600;
    const padding = 60;
    
    // Use stored node sizes if available (now {width, height} objects)
    const nodeSizes = window.nodeSizes || Array(count).fill({ width: 340, height: 160 });
    
    const positions = [];
    
    // Use a circular layout for better distribution
    if (count <= 3) {
        // For small counts, use horizontal layout
        const spacing = Math.min((canvasWidth - padding * 2) / count, 450);
        const avgNodeWidth = nodeSizes.reduce((a, b) => a + b.width, 0) / nodeSizes.length;
        const startX = (canvasWidth - (spacing * (count - 1))) / 2 - avgNodeWidth / 2;
        
        for (let i = 0; i < count; i++) {
            const nodeSize = nodeSizes[i];
            const centerY = (canvasHeight - nodeSize.height) / 2;
            
            positions.push({
                x: startX + i * spacing,
                y: centerY
            });
        }
    } else {
        // For larger counts, use circular pattern
        const centerX = canvasWidth / 2;
        const centerY = canvasHeight / 2;
        const radius = Math.min(canvasWidth, canvasHeight) * 0.35;
        
        for (let i = 0; i < count; i++) {
            const nodeSize = nodeSizes[i];
            const angle = (i * 2 * Math.PI) / count - Math.PI / 2;
            positions.push({
                x: centerX + radius * Math.cos(angle) - nodeSize.width / 2,
                y: centerY + radius * Math.sin(angle) - nodeSize.height / 2
            });
        }
    }
    
    return positions;
}

// Helper function to escape HTML and prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Poll for completion when in GENERATING state
async function pollForCompletion() {
    // TODO: Implement polling logic
    // Check the course status every few seconds
    // When status becomes ACTIVE, reload the page or update state
}

// Setup the main application page
async function setupAppPage() {
    // Load graph data
    await loadGraphData();
    
    // Initialize Vis.js network
    initializeGraph();
    
    // Setup chat interface
    setupChat();
    
    // Setup file toggle
    setupFileToggle();
}

// Load graph data from API
async function loadGraphData() {
    try {
        const response = await fetch(`/api/get-graph?course_id=${COURSE_ID}`);
        const data = await response.json();
        
        graphData = {
            nodes: JSON.parse(data.nodes),
            edges: JSON.parse(data.edges),
            data: JSON.parse(data.data)
        };
    } catch (error) {
        console.error('Failed to load graph data:', error);
    }
}

// Initialize the Vis.js graph visualization
function initializeGraph() {
    if (!graphData) return;
    
    const container = document.getElementById('graph-network');
    const data = {
        nodes: new vis.DataSet(graphData.nodes),
        edges: new vis.DataSet(graphData.edges)
    };
    
    const options = {
        // TODO: Configure Vis.js options
        // Set colors for topic vs file nodes
        // Configure physics, layout, etc.
    };
    
    network = new vis.Network(container, data, options);
    
    // Handle node clicks
    network.on('click', (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            showNodeDetails(nodeId);
        }
    });
}

// Show details for a clicked node
function showNodeDetails(nodeId) {
    const detailsDiv = document.getElementById('node-details');
    
    // TODO: Implement node details display
    // If it's a topic node, show summary and sources
    // If it's a file node, show link to file
    
    detailsDiv.innerHTML = `<p>Details for node: ${nodeId}</p>`;
}

// Setup the chat interface
function setupChat() {
    const sendBtn = document.getElementById('chat-send');
    const input = document.getElementById('chat-input');
    
    sendBtn.addEventListener('click', () => sendMessage());
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
}

// Send a chat message
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    
    if (!query) return;
    
    // Add user message to chat
    addMessageToChat('user', query);
    input.value = '';
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course_id: COURSE_ID, query: query })
        });
        
        const result = await response.json();
        
        // Add bot response to chat
        addMessageToChat('bot', result.answer, result.sources);
        
    } catch (error) {
        console.error('Chat failed:', error);
        addMessageToChat('bot', 'Sorry, I encountered an error. Please try again.');
    }
}

// Add a message to the chat display
function addMessageToChat(sender, message, sources = []) {
    const messagesDiv = document.getElementById('chat-messages');
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${sender}-message`;
    messageElement.innerHTML = `<p>${message}</p>`;
    
    if (sources.length > 0) {
        const sourcesHTML = sources.map(s => `<span class="source">${s}</span>`).join(', ');
        messageElement.innerHTML += `<div class="sources">Sources: ${sourcesHTML}</div>`;
    }
    
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Show chat interface and set up handlers
function showChatInterface() {
    const chatInterface = document.getElementById('chat-interface');
    if (!chatInterface) return;
    
    // Show the chat interface
    chatInterface.style.display = 'block';
    
    // Set up chat handlers
    setupChatHandlers();
    
    // Set up collapse/expand functionality
    setupChatToggle();
    
    // Set up back to edit button
    setupBackToEditButton();
    
    // Add welcome message
    addChatMessage('assistant', 'Course generated! You can now ask me questions about your course materials.');
}

// Set up back to edit button functionality
function setupBackToEditButton() {
    const backToEditBtn = document.getElementById('back-to-edit-btn');
    if (!backToEditBtn) return;
    
    backToEditBtn.addEventListener('click', () => {
        returnToEditMode();
    });
}

// Return to edit mode from finalized state
function returnToEditMode() {
    const canvas = document.getElementById('topic-canvas');
    const chatInterface = document.getElementById('chat-interface');
    const generateAction = document.querySelector('.generate-action');
    const generateBtn = document.getElementById('generate-course-btn');
    const addBtn = document.getElementById('add-topic-btn');
    const nodes = canvas.querySelectorAll('.topic-node');
    
    // Hide chat interface
    if (chatInterface) {
        chatInterface.style.display = 'none';
    }
    
    // Show generate button again and reset its state
    if (generateAction) {
        generateAction.style.display = 'flex';
    }
    
    // Reset generate button to original state
    if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Course';
    }
    
    // Show add button
    if (addBtn) {
        addBtn.style.opacity = '1';
        addBtn.style.pointerEvents = 'auto';
        addBtn.style.display = 'inline-flex';
    }
    
    // Remove finalizing class
    canvas.classList.remove('finalizing');
    
    // Re-enable all nodes for editing
    nodes.forEach(node => {
        // Show delete buttons
        const deleteBtn = node.querySelector('.node-delete-btn');
        if (deleteBtn) {
            deleteBtn.style.opacity = '1';
            deleteBtn.style.pointerEvents = 'auto';
        }
        
        // Re-enable editing on title and summary
        const title = node.querySelector('.node-title');
        const summary = node.querySelector('.node-summary');
        if (title) {
            title.contentEditable = 'true';
            title.style.cursor = 'text';
        }
        if (summary) {
            summary.contentEditable = 'true';
            summary.style.cursor = 'text';
        }
        
        // Restore hover effects
        node.style.cursor = 'pointer';
    });
    
    // Re-render with original scattered positions
    if (window.topicsData) {
        renderTopicEditor(window.topicsData);
    }
}

// Set up chat event handlers
function setupChatHandlers() {
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    
    if (!chatInput || !chatSendBtn) return;
    
    // Send message on button click
    chatSendBtn.addEventListener('click', sendChatMessage);
    
    // Send message on Enter key
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

// Send a chat message
async function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    
    if (!chatInput || !chatSendBtn) return;
    
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addChatMessage('user', message);
    
    // Clear input and disable button
    chatInput.value = '';
    chatSendBtn.disabled = true;
    
    // Add loading message
    const loadingId = addChatMessage('loading', 'Thinking...');
    
    try {
        // Call RAG API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: COURSE_ID,
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        
        const result = await response.json();
        
        // Remove loading message
        removeChatMessage(loadingId);
        
        // Add assistant response
        addChatMessage('assistant', result.response || 'Sorry, I could not generate a response.');
        
    } catch (error) {
        console.error('Chat error:', error);
        
        // Remove loading message
        removeChatMessage(loadingId);
        
        // Add error message
        addChatMessage('assistant', 'Sorry, I encountered an error. Please try again.');
        
    } finally {
        // Re-enable button
        chatSendBtn.disabled = false;
        chatInput.focus();
    }
}

// Add a message to the chat
function addChatMessage(type, text) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return null;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.textContent = text;
    
    // Generate unique ID for the message
    const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    messageDiv.id = messageId;
    
    chatMessages.appendChild(messageDiv);
    
    // Auto-scroll to bottom
    const container = document.getElementById('chat-messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
    
    return messageId;
}

// Remove a chat message by ID
function removeChatMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// Set up chat collapse/expand functionality
function setupChatToggle() {
    const chatInterface = document.getElementById('chat-interface');
    const chatToggleBtn = document.getElementById('chat-toggle-btn');
    const chatInput = document.getElementById('chat-input');
    const chatInputContainer = document.getElementById('chat-input-container');
    
    if (!chatInterface || !chatToggleBtn) return;
    
    // Toggle button click
    chatToggleBtn.addEventListener('click', () => {
        chatInterface.classList.toggle('collapsed');
    });
    
    // Expand when clicking on input area
    if (chatInput) {
        chatInput.addEventListener('focus', () => {
            chatInterface.classList.remove('collapsed');
        });
    }
    
    // Also expand when clicking anywhere in the input container
    if (chatInputContainer) {
        chatInputContainer.addEventListener('click', () => {
            chatInterface.classList.remove('collapsed');
        });
    }
}

// Setup file toggle functionality
function setupFileToggle() {
    const toggleBtn = document.getElementById('toggle-files');
    
    // TODO: Implement file list toggle
    // Show/hide file nodes in the graph
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeUI);
