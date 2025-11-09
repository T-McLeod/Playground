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
            startAutoGeneration();
        });
    }
}

// Start the automatic course generation pipeline
async function startAutoGeneration() {
    const generateBtn = document.getElementById('generate-now-btn');
    const landingContent = document.querySelector('.landing-content');
    const googleLoader = document.getElementById('google-loader');
    const landingHint = document.querySelector('.landing-hint');
    
    if (!generateBtn || !googleLoader) return;
    
    // Get button position and dimensions
    const btnRect = generateBtn.getBoundingClientRect();
    const landingRect = document.getElementById('landing-screen').getBoundingClientRect();
    
    // Calculate relative position within landing screen
    const relativeTop = btnRect.top - landingRect.top + btnRect.height / 2;
    const relativeLeft = btnRect.left - landingRect.left + btnRect.width / 2;
    
    // Position loader at button location
    googleLoader.style.top = relativeTop + 'px';
    googleLoader.style.left = relativeLeft + 'px';
    googleLoader.style.transform = 'translate(-50%, -50%)';
    googleLoader.style.position = 'absolute';
    
    // Hide hint text
    if (landingHint) landingHint.style.opacity = '0';
    
    // Animate decorative shapes flying out
    const decorativeShapes = document.querySelectorAll('.shape');
    decorativeShapes.forEach((shape, index) => {
        const randomAngle = Math.random() * 360;
        const randomDistance = 200 + Math.random() * 300;
        const randomX = Math.cos(randomAngle * Math.PI / 180) * randomDistance;
        const randomY = Math.sin(randomAngle * Math.PI / 180) * randomDistance;
        
        shape.style.transition = `all 1s cubic-bezier(0.4, 0, 0.2, 1) ${index * 0.05}s`;
        shape.style.transform = `translate(${randomX}px, ${randomY}px) scale(0)`;
        shape.style.opacity = '0';
    });
    
    // Animate button collapse
    generateBtn.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
    generateBtn.style.transform = 'scale(0)';
    generateBtn.style.opacity = '0';
    
    // Show loader after button starts collapsing
    setTimeout(() => {
        googleLoader.style.display = 'block';
        googleLoader.style.opacity = '0';
        googleLoader.style.transition = 'opacity 0.5s ease-in';
        
        // Fade in loader
        requestAnimationFrame(() => {
            googleLoader.style.opacity = '1';
        });
        
        // Hide other landing content
        if (landingContent) {
            landingContent.querySelector('.landing-title').style.opacity = '0';
            landingContent.querySelector('.landing-subtitle').style.opacity = '0';
        }
    }, 250);
    
        try {
            const response = await fetch('/api/initialize-course', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: COURSE_ID
                // No topics - backend will auto-extract
            })
            })
            
            const result = await response.json();
            
        if (!response.ok) {
            throw new Error(result.error || 'Generation failed');
        }
        
        // Course initialization successful - redirect to launch endpoint
        window.location.href = `/launch?course_id=${COURSE_ID}&user_id=${USER_ID || ''}&role=${USER_ROLES || ''}`;
        
    } catch (error) {
        console.error('Auto-generation failed:', error);
        showManualFallback(error.message);
    }
}

// Convert knowledge graph API response to topics editor format
function convertGraphToTopics(apiResponse) {
    const nodes = apiResponse.kg_nodes || [];
    const data = apiResponse.kg_data || {};
    
    const topicsData = [];
    
    // Parse JSON strings if needed
    const parsedNodes = typeof nodes === 'string' ? JSON.parse(nodes) : nodes;
    const parsedData = typeof data === 'string' ? JSON.parse(data) : data;
    
    // Filter for topic nodes only (not file nodes)
    const topicNodes = parsedNodes.filter(node => node.group === 'topic');
    
    // Convert to topics editor format
    for (const node of topicNodes) {
        const topicId = node.id; // e.g., "topic_1"
        const topicInfo = parsedData[topicId] || {};
        
        topicsData.push({
            topic: node.label || 'Untitled Topic',
            summary: topicInfo.summary || 'No summary available.'
        });
    }
    
    console.log('Converted topics data:', topicsData);
    return topicsData;
}

// Show manual fallback UI when auto-generation fails
function showManualFallback(errorMessage) {
    const loadingDiv = document.getElementById('init-loading');
    const editorDiv = document.getElementById('init-editor');
    
    // Show the Airbnb-style error page
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
            <p class="error-message">We couldn't auto-generate topics: ${escapeHtml(errorMessage)}</p>
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
        renderTopicEditor([{ 
            topic: 'My First Topic', 
            summary: 'Click to edit this topic and add your course content.' 
        }]);
        setupTopicEditorHandlers();
    });
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
        const response = await fetch(`/api/get-graph?course_id=${COURSE_ID}`, {
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
    
    // Fixed compact size for all nodes
    const compactSize = { width: 180, height: 80 };
    const nodeSizes = topicsData.map(() => compactSize);
    window.nodeSizes = nodeSizes;
    
    // Calculate positions for nodes (distributed layout)
    const positions = calculateNodePositions(topicsData.length, nodeSizes);
    
    topicsData.forEach((item, index) => {
        const node = document.createElement('div');
        node.className = `topic-node color-${(index % 6) + 1} compact`;
        node.dataset.index = index;
        
        // Set compact size
        node.style.width = compactSize.width + 'px';
        node.style.height = compactSize.height + 'px';
        
        // Set position
        node.style.left = positions[index].x + 'px';
        node.style.top = positions[index].y + 'px';
        
        // Store original position and size
        node.dataset.originalLeft = positions[index].x;
        node.dataset.originalTop = positions[index].y;
        node.dataset.originalWidth = compactSize.width;
        node.dataset.originalHeight = compactSize.height;
        
        // Create delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'node-delete-btn';
        deleteBtn.dataset.index = index;
        deleteBtn.innerHTML = '&times;';
        
        // Create editable title (always visible)
        const title = document.createElement('div');
        title.className = 'node-title';
        title.contentEditable = 'true';
        title.textContent = item.topic;
        title.dataset.index = index;
        title.dataset.field = 'topic';
        
        // Create editable summary (hidden in compact mode)
        const summary = document.createElement('div');
        summary.className = 'node-summary';
        summary.contentEditable = 'true';
        summary.textContent = item.summary;
        summary.dataset.index = index;
        summary.dataset.field = 'summary';
        summary.style.display = 'none'; // Hidden by default
        
        // Add elements to node
        node.appendChild(deleteBtn);
        node.appendChild(title);
        node.appendChild(summary);
        
        // Setup click-to-expand and inline editing handlers
        setupNodeExpandHandlers(node, title, summary, index);
        
        canvas.appendChild(node);
    });
    
    // Setup canvas click to collapse expanded nodes (click outside)
    setupCanvasClickToCollapse(canvas);
    
    // Setup escape key to collapse expanded nodes
    setupEscapeKeyHandler();
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

// Setup node expand/collapse and editing handlers
function setupNodeExpandHandlers(node, title, summary, index) {
    let isExpanded = false;
    
    // Click on node (not on contentEditable areas) to expand
    node.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent canvas click handler from firing
        
        // Don't toggle if clicking on delete button or if already editing
        if (e.target.closest('.node-delete-btn')) return;
        if (e.target.contentEditable === 'true' && isExpanded) return;
        
        if (!isExpanded) {
            // Collapse any other expanded nodes first
            collapseAllNodes();
            
            expandNode(node, title, summary);
            isExpanded = true;
            
            // Store reference to currently expanded node
            window.currentExpandedNode = { node, title, summary, handlers: { setExpanded: (val) => { isExpanded = val; } } };
        }
    });
    
    // Handle focus on title
    title.addEventListener('focus', () => {
        if (!isExpanded) {
            // Collapse any other expanded nodes first
            collapseAllNodes();
            
            expandNode(node, title, summary);
            isExpanded = true;
            window.currentExpandedNode = { node, title, summary, handlers: { setExpanded: (val) => { isExpanded = val; } } };
        }
    });
    
    // Handle focus on summary
    summary.addEventListener('focus', () => {
        if (!isExpanded) {
            // Collapse any other expanded nodes first
            collapseAllNodes();
            
            expandNode(node, title, summary);
            isExpanded = true;
            window.currentExpandedNode = { node, title, summary, handlers: { setExpanded: (val) => { isExpanded = val; } } };
        }
    });
    
    // Save on blur - check if focus left the node entirely
    const handleBlur = () => {
        setTimeout(() => {
            const activeElement = document.activeElement;
            const isStillInNode = activeElement && activeElement.closest('.topic-node') === node;
            
            if (!isStillInNode && isExpanded) {
                // Save changes
                const newTitle = title.textContent.trim();
                const newSummary = summary.textContent.trim();
                
                if (newTitle) {
                    window.topicsData[index].topic = newTitle;
                    window.topicsData[index].summary = newSummary;
                }
                
                // Collapse node
                collapseNode(node, summary);
                isExpanded = false;
            }
        }, 10);
    };
    
    title.addEventListener('blur', handleBlur);
    summary.addEventListener('blur', handleBlur);
    
    // Keyboard shortcuts
    title.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            summary.focus();
        } else if (e.key === 'Escape') {
            title.blur();
        }
    });
    
    summary.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            summary.blur();
        }
    });
}

// Expand node for editing
function expandNode(node, title, summary) {
    const canvas = document.getElementById('topic-canvas');
    
    // Calculate expanded size - fixed dimensions for consistent layout
    const viewportWidth = window.innerWidth;
    const padding = 80; // Padding from edges
    
    const expandedWidth = Math.min(viewportWidth - padding * 2, 1200); // Max 1200px width
    const expandedHeight = 600; // Fixed height for consistent summary area
    
    // Add expanded class
    node.classList.remove('compact');
    node.classList.add('expanded');
    
    // Set expanded size with smooth transition
    node.style.width = expandedWidth + 'px';
    node.style.height = expandedHeight + 'px';
    
    // Show summary
    summary.style.display = 'block';
    
    // Dim other nodes
    const allNodes = canvas.querySelectorAll('.topic-node');
    allNodes.forEach(otherNode => {
        if (otherNode !== node) {
            otherNode.classList.add('dimmed');
        }
    });
    
    // Zoom to node and center it
    zoomToNode(node);
}

// Collapse node back to compact view
function collapseNode(node, summary) {
    const canvas = document.getElementById('topic-canvas');
    
    // Remove expanded class, add compact
    node.classList.remove('expanded');
    node.classList.add('compact');
    
    // Restore compact size
    node.style.width = node.dataset.originalWidth + 'px';
    node.style.height = node.dataset.originalHeight + 'px';
    
    // Hide summary
    summary.style.display = 'none';
    
    // Un-dim other nodes
    const allNodes = canvas.querySelectorAll('.topic-node');
    allNodes.forEach(otherNode => {
        otherNode.classList.remove('dimmed');
    });
    
    // Zoom out
    zoomOutNode(node);
}

// Collapse all currently expanded nodes
function collapseAllNodes() {
    if (window.currentExpandedNode) {
        const { node, summary, handlers } = window.currentExpandedNode;
        collapseNode(node, summary);
        handlers.setExpanded(false);
        window.currentExpandedNode = null;
    }
}

// Setup canvas click handler to collapse nodes when clicking outside
function setupCanvasClickToCollapse(canvas) {
    // Remove any existing handler to avoid duplicates
    if (window.canvasClickHandler) {
        canvas.removeEventListener('click', window.canvasClickHandler);
    }
    
    // Create new handler
    window.canvasClickHandler = (e) => {
        // Only collapse if clicking directly on canvas (not on a node)
        if (e.target === canvas) {
            collapseAllNodes();
        }
    };
    
    canvas.addEventListener('click', window.canvasClickHandler);
}

// Setup escape key handler to collapse expanded nodes
function setupEscapeKeyHandler() {
    // Remove any existing handler to avoid duplicates
    if (window.escapeKeyHandler) {
        document.removeEventListener('keydown', window.escapeKeyHandler);
    }
    
    // Create new handler
    window.escapeKeyHandler = (e) => {
        if (e.key === 'Escape') {
            collapseAllNodes();
        }
    };
    
    document.addEventListener('keydown', window.escapeKeyHandler);
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
    
    console.log('Topics data:', topicsData);
    console.log('Valid topics:', validTopics);
    
    if (validTopics.length === 0) {
        alert('Please add at least one topic with both a name and summary before generating the course.');
        return;
    }
    
    // Disable button and show loading state
    generateBtn.disabled = true;
    generateBtn.textContent = 'Finalizing...';
    
    console.log('Starting animation...');
    
    // Animate nodes spreading out and removing delete buttons
    await animateNodesForGeneration();
    
    console.log('Animation complete!');
    
    // Hide the generate action buttons
    const generateAction = document.querySelector('.generate-action');
    if (generateAction) {
        generateAction.style.display = 'none';
    }
    
    // Reset button state
    generateBtn.textContent = 'Generate Course';
    generateBtn.disabled = false;
    
    console.log('About to show chat interface...');
    
    // Show chat interface
    showChatInterface();
    
    console.log('Chat interface should be visible now!');
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
    const canvasHeight = 600; // Fixed height for consistent spread
    const padding = 80;
    
    // Use compact node size for final layout
    const nodeSize = { width: 180, height: 80 };
    
    const positions = [];
    
    if (count === 1) {
        // Single node - center it
        positions.push({
            x: (canvasWidth - nodeSize.width) / 2,
            y: (canvasHeight - nodeSize.height) / 2
        });
    } else if (count <= 3) {
        // 2-3 nodes - horizontal line
        const spacing = (canvasWidth - padding * 2 - nodeSize.width) / (count - 1);
        for (let i = 0; i < count; i++) {
            positions.push({
                x: padding + i * spacing,
                y: (canvasHeight - nodeSize.height) / 2
            });
        }
    } else {
        // 4+ nodes - even grid distribution
        const cols = Math.ceil(Math.sqrt(count * (canvasWidth / canvasHeight)));
        const rows = Math.ceil(count / cols);
        
        const cellWidth = (canvasWidth - padding * 2) / cols;
        const cellHeight = (canvasHeight - padding * 2) / rows;
        
        for (let i = 0; i < count; i++) {
            const row = Math.floor(i / cols);
            const col = i % cols;
            
            // Center within cell
            const x = padding + col * cellWidth + (cellWidth - nodeSize.width) / 2;
            const y = padding + row * cellHeight + (cellHeight - nodeSize.height) / 2;
            
            positions.push({ x, y });
        }
    }
    
    return positions;
}

// Old circular layout code for reference (keeping rest of function)
function calculateEvenlySpreadPositions_OLD(count) {
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
    
    // Initialize graph visualization
    initializeGraph();
    
    // Setup chat interface
    setupChat();
    
    // Setup chat toggle (collapse/expand)
    setupChatToggleActive();
    
    // Setup edit button
    setupEditButtonActive();
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

// Initialize the graph visualization for ACTIVE state
function initializeGraph() {
    if (!graphData) return;
    
    const container = document.getElementById('graph-network-active');
    
    if (!container) {
        console.warn('Graph container not found');
        return;
    }
    
    // Convert graph data to topics format
    const topicsData = [];
    const topicNodes = graphData.nodes.filter(node => node.group === 'topic');
    
    for (const node of topicNodes) {
        const topicId = node.id;
        const topicInfo = graphData.data[topicId] || {};
        
        topicsData.push({
            topic: node.label || 'Untitled Topic',
            summary: topicInfo.summary || 'No summary available.'
        });
    }
    
    // Store globally for reference
    window.topicsData = topicsData;
    
    // Create visual nodes (full-screen style)
    container.innerHTML = '';
    container.style.position = 'fixed';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100vw';
    container.style.height = '100vh';
    container.style.backgroundColor = '#f5f5f5';
    container.style.padding = '0';
    container.style.margin = '0';
    container.style.overflow = 'hidden';
    
    // Calculate positions for full viewport
    const canvasWidth = window.innerWidth;
    const canvasHeight = window.innerHeight;
    
    // Calculate node sizes
    const nodeSizes = topicsData.map(item => calculateNodeSize(item.topic, item.summary, true));
    window.nodeSizes = nodeSizes;
    
    const positions = calculatePositionsForContainer(topicsData.length, nodeSizes, canvasWidth, canvasHeight);
    
    // Render each node (read-only, no delete buttons)
    topicsData.forEach((item, index) => {
        const pos = positions[index];
        const size = nodeSizes[index];
        const colorClass = `color-${(index % 6) + 1}`;
        
        const nodeDiv = document.createElement('div');
        nodeDiv.className = `topic-node ${colorClass}`;
        nodeDiv.style.position = 'absolute';
        nodeDiv.style.left = `${pos.x}px`;
        nodeDiv.style.top = `${pos.y}px`;
        nodeDiv.style.width = `${size.width}px`;
        nodeDiv.style.height = `${size.height}px`;
        nodeDiv.style.cursor = 'default';
        
        const titleDiv = document.createElement('div');
        titleDiv.className = 'node-title';
        titleDiv.textContent = item.topic;
        titleDiv.contentEditable = 'false';
        titleDiv.style.cursor = 'default';
        
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'node-summary';
        summaryDiv.textContent = item.summary;
        summaryDiv.contentEditable = 'false';
        summaryDiv.style.cursor = 'default';
        
        nodeDiv.appendChild(titleDiv);
        nodeDiv.appendChild(summaryDiv);
        
        container.appendChild(nodeDiv);
    });
    
    // Show chat interface
    const chatInterface = document.getElementById('chat-interface-active');
    if (chatInterface) {
        chatInterface.style.display = 'block';
    }
}

// Setup chat toggle for ACTIVE state
function setupChatToggleActive() {
    const chatInterface = document.getElementById('chat-interface-active');
    const chatToggleBtn = document.getElementById('chat-toggle-btn-active');
    const chatInput = document.getElementById('chat-input-active');
    const chatInputContainer = document.getElementById('chat-input-container-active');
    
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

// Setup edit button for ACTIVE state
function setupEditButtonActive() {
    const editBtn = document.getElementById('back-to-edit-btn-active');
    
    if (!editBtn) return;
    
    editBtn.addEventListener('click', () => {
        // This would reload the page in NEEDS_INIT state to edit topics
        // For now, show alert that editing is not available in production
        alert('To edit topics, please re-initialize the course from Canvas.');
    });
}

// Helper function to calculate node positions for any container
function calculatePositionsForContainer(count, nodeSizes, containerWidth, containerHeight) {
    const positions = [];
    
    if (!nodeSizes || nodeSizes.length === 0) {
        // Fallback to default sizes
        nodeSizes = Array(count).fill({width: 200, height: 150});
    }
    
    if (count <= 4) {
        // For small counts, use horizontal layout
        const spacing = 40;
        const totalWidth = nodeSizes.reduce((sum, size) => sum + size.width, 0) + (count - 1) * spacing;
        let startX = (containerWidth - totalWidth) / 2;
        const centerY = containerHeight / 2;
        
        for (let i = 0; i < count; i++) {
            const nodeSize = nodeSizes[i];
            positions.push({
                x: startX,
                y: centerY - nodeSize.height / 2
            });
            startX += nodeSize.width + spacing;
        }
    } else {
        // For larger counts, use circular pattern
        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;
        const radius = Math.min(containerWidth, containerHeight) * 0.35;
        
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

// Setup the chat interface
function setupChat() {
    const sendBtn = document.getElementById('chat-send-active');
    const input = document.getElementById('chat-input-active');
    
    if (!sendBtn || !input) {
        console.warn('Chat elements not found');
        return;
    }
    
    sendBtn.addEventListener('click', () => sendMessage());
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
}

// Send a chat message
async function sendMessage() {
    const input = document.getElementById('chat-input-active');
    const sendBtn = document.getElementById('chat-send-active');
    
    if (!input || !sendBtn) {
        console.warn('Chat input elements not found');
        return;
    }
    
    const query = input.value.trim();
    
    if (!query) return;
    
    // Add user message to chat
    addMessageToChat('user', query);
    input.value = '';
    
    // Disable input while processing
    input.disabled = true;
    sendBtn.disabled = true;
    sendBtn.textContent = 'Thinking...';
    
    // Add loading indicator
    const loadingId = 'msg-loading-' + Date.now();
    addMessageToChat('bot', '...', [], loadingId);
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                course_id: COURSE_ID, 
                query: query 
            })
        });
        
        const result = await response.json();
        
        // Remove loading indicator
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();
        
        // Add bot response to chat
        if (response.ok) {
        addMessageToChat('bot', result.answer, result.sources);
        } else {
            addMessageToChat('bot', 'Sorry, I encountered an error: ' + (result.error || 'Unknown error'));
        }
        
    } catch (error) {
        console.error('Chat failed:', error);
        
        // Remove loading indicator
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();
        
        addMessageToChat('bot', 'Sorry, I encountered an error. Please try again.');
    } finally {
        // Re-enable input
        input.disabled = false;
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send';
        input.focus();
    }
}

// Add a message to the chat display
function addMessageToChat(sender, message, sources = [], messageId = null) {
    const messagesDiv = document.getElementById('chat-messages-active');
    
    if (!messagesDiv) {
        console.warn('Chat messages container not found');
        return;
    }
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${sender}-message`;
    if (messageId) {
        messageElement.id = messageId;
    }
    
    // Create message content
    const messagePara = document.createElement('p');
    messagePara.textContent = message;
    messageElement.appendChild(messagePara);
    
    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';
        sourcesDiv.innerHTML = '<strong>Sources:</strong> ';
        
        sources.forEach((source, index) => {
            const sourceSpan = document.createElement('span');
            sourceSpan.className = 'source';
            sourceSpan.textContent = source;
            sourcesDiv.appendChild(sourceSpan);
            
            if (index < sources.length - 1) {
                sourcesDiv.appendChild(document.createTextNode(', '));
            }
        });
        
        messageElement.appendChild(sourcesDiv);
    }
    
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Show chat interface and set up handlers
function showChatInterface() {
    console.log('showChatInterface called');
    const chatInterface = document.getElementById('chat-interface');
    console.log('chatInterface element:', chatInterface);
    
    if (!chatInterface) {
        console.error('Chat interface element not found!');
        return;
    }
    
    // Show the chat interface (use flex to match CSS definition)
    chatInterface.style.display = 'flex';
    console.log('Set display to flex');
    
    // Set up chat handlers
    setupChatHandlers();
    console.log('Setup chat handlers');
    
    // Set up collapse/expand functionality
    setupChatToggle();
    console.log('Setup chat toggle');
    
    // Set up back to edit button
    setupBackToEditButton();
    console.log('Setup back to edit button');
    
    // Add welcome message
    addChatMessage('assistant', 'Course generated! You can now ask me questions about your course materials.');
    console.log('Added welcome message');
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
                query: message
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        
        const result = await response.json();
        
        // Remove loading message
        removeChatMessage(loadingId);
        
        // Add assistant response
        const answer = result.answer || result.response || 'Sorry, I could not generate a response.';
        addChatMessage('assistant', answer);
        
        // Add sources if available
        if (result.sources && result.sources.length > 0) {
            const sourcesText = '📚 Sources:\n' + result.sources.map((src, i) => 
                `${i + 1}. ${src}`
            ).join('\n');
            addChatMessage('sources', sourcesText);
        }
        
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
    messageDiv.style.whiteSpace = 'pre-wrap';
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.IS_EDITOR) {
        console.log("Editor mode — skipping initializeUI()");
        return;
    }
    initializeUI();
});