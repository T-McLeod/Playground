/**
 * Explorer.js - Admin File Browser
 * 
 * Implements the Google Drive-like file explorer for managing
 * folders and bot instances using the Pointer Pattern.
 * 
 * Key Concepts:
 * - fs_id: Used for all organizational actions (navigate, move, delete, rename)
 * - playground_id: Used only when entering the editor for a bot
 */

// =============================================================================
// State Management
// =============================================================================

const ExplorerState = {
    currentFolderId: 'root',
    items: [],
    breadcrumbs: [],
    selectedItem: null,
    isLoading: false,
    modalMode: null, // 'folder' | 'instance' | 'rename'
    contextTarget: null // Item currently targeted by context menu
};

// =============================================================================
// DOM Elements
// =============================================================================

const DOM = {
    // Main containers
    loadingState: document.getElementById('loading-state'),
    emptyState: document.getElementById('empty-state'),
    itemsGrid: document.getElementById('items-grid'),
    breadcrumbs: document.getElementById('breadcrumbs'),
    
    // Buttons
    newInstanceBtn: document.getElementById('new-instance-btn'),
    newFolderBtn: document.getElementById('new-folder-btn'),
    emptyNewInstanceBtn: document.getElementById('empty-new-instance-btn'),
    
    // Modal
    createModal: document.getElementById('create-modal'),
    modalTitle: document.getElementById('modal-title'),
    itemNameInput: document.getElementById('item-name-input'),
    inputHint: document.getElementById('input-hint'),
    modalCreateBtn: document.getElementById('modal-create-btn'),
    modalCancelBtn: document.getElementById('modal-cancel-btn'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    
    // Context Menu
    contextMenu: document.getElementById('context-menu'),
    
    // Toast
    toastContainer: document.getElementById('toast-container')
};

// =============================================================================
// API Functions
// =============================================================================

const API = {
    /**
     * Fetches directory contents from the backend.
     * @param {string} parentId - The folder ID to browse
     * @returns {Promise<{items: Array, breadcrumbs: Array}>}
     */
    async browse(parentId = 'root') {
        const url = parentId === 'root' 
            ? '/api/admin/browse'
            : `/api/admin/browse?parent_id=${encodeURIComponent(parentId)}`;
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to browse: ${response.statusText}`);
        }
        return response.json();
    },
    
    /**
     * Creates a new folder.
     * @param {string} name - Folder display name
     * @param {string} parentId - Parent folder ID
     * @returns {Promise<Object>} The created folder item
     */
    async createFolder(name, parentId) {
        const response = await fetch('/api/admin/folders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent_id: parentId })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to create folder');
        }
        return response.json();
    },
    
    /**
     * Creates a new playground (bot instance).
     * @param {string} name - Instance display name
     * @param {string} parentId - Parent folder ID
     * @returns {Promise<Object>} The created bot item
     */
    async createPlayground(name, parentId) {
        const response = await fetch('/api/admin/playgrounds', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent_id: parentId })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to create instance');
        }
        return response.json();
    },
    
    /**
     * Renames an item (folder or bot).
     * @param {string} fsId - File system ID
     * @param {string} newName - New display name
     * @returns {Promise<Object>} The updated item
     */
    async renameItem(fsId, newName) {
        const response = await fetch('/api/admin/items/rename', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fs_id: fsId, new_name: newName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to rename item');
        }
        return response.json();
    },
    
    /**
     * Deletes an item from the file system.
     * @param {string} fsId - File system ID
     * @returns {Promise<void>}
     */
    async deleteItem(fsId) {
        const response = await fetch(`/api/admin/items?fs_id=${encodeURIComponent(fsId)}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to delete item');
        }
    },
    
    /**
     * Moves an item to a new parent folder.
     * @param {string} fsId - File system ID
     * @param {string} newParentId - Target folder ID
     * @returns {Promise<Object>}
     */
    async moveItem(fsId, newParentId) {
        const response = await fetch('/api/admin/move', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fs_id: fsId, new_parent_id: newParentId })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to move item');
        }
        return response.json();
    }
};

// =============================================================================
// Rendering Functions
// =============================================================================

/**
 * Renders the breadcrumb navigation.
 */
function renderBreadcrumbs() {
    const { breadcrumbs } = ExplorerState;
    
    DOM.breadcrumbs.innerHTML = breadcrumbs.map((crumb, index) => {
        const isLast = index === breadcrumbs.length - 1;
        const icon = crumb.id === 'root' ? '🏠' : '';
        
        if (isLast) {
            return `<span class="breadcrumb-current">${icon} ${crumb.name}</span>`;
        }
        return `
            <a href="#" class="breadcrumb-item" data-id="${crumb.id}">${icon} ${crumb.name}</a>
            <span class="breadcrumb-separator">›</span>
        `;
    }).join('');
    
    // Attach click handlers
    DOM.breadcrumbs.querySelectorAll('.breadcrumb-item').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            navigateToFolder(el.dataset.id);
        });
    });
}

/**
 * Renders a single item card.
 * @param {Object} item - The item data
 * @returns {string} HTML string
 */
function renderItemCard(item) {
    const isFolder = item.type === 'folder';
    const icon = isFolder ? '📁' : '🤖';
    const typeClass = isFolder ? 'folder' : 'bot';
    
    // Build status badge for bots
    let statusBadge = '';
    if (!isFolder && item.preview) {
        const status = item.preview.status || 'unknown';
        const statusClass = {
            'ACTIVE': 'status-active',
            'CREATED': 'status-created',
            'GENERATING': 'status-generating',
            'ERROR': 'status-error'
        }[status] || 'status-unknown';
        
        statusBadge = `<span class="status-badge ${statusClass}">${status}</span>`;
    }
    
    return `
        <div class="item-card ${typeClass}" 
             data-fs-id="${item.fs_id}" 
             data-type="${item.type}"
             data-playground-id="${item.playground_id || ''}"
             tabindex="0">
            <div class="item-icon">${icon}</div>
            <div class="item-info">
                <span class="item-name">${escapeHtml(item.name)}</span>
                ${statusBadge}
            </div>
        </div>
    `;
}

/**
 * Renders the items grid.
 */
function renderItems() {
    const { items, isLoading } = ExplorerState;
    
    // Handle loading state
    DOM.loadingState.classList.toggle('hidden', !isLoading);
    
    if (isLoading) {
        DOM.emptyState.classList.add('hidden');
        DOM.itemsGrid.classList.add('hidden');
        return;
    }
    
    // Handle empty state
    if (items.length === 0) {
        DOM.emptyState.classList.remove('hidden');
        DOM.itemsGrid.classList.add('hidden');
        return;
    }
    
    // Render items
    DOM.emptyState.classList.add('hidden');
    DOM.itemsGrid.classList.remove('hidden');
    DOM.itemsGrid.innerHTML = items.map(renderItemCard).join('');
    
    // Attach event handlers
    attachItemHandlers();
}

/**
 * Attaches event handlers to item cards.
 */
function attachItemHandlers() {
    DOM.itemsGrid.querySelectorAll('.item-card').forEach(card => {
        // Double-click to open
        card.addEventListener('dblclick', () => handleItemOpen(card));
        
        // Single click to select
        card.addEventListener('click', (e) => {
            e.stopPropagation();
            selectItem(card);
        });
        
        // Right-click for context menu
        card.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            showContextMenu(e, card);
        });
        
        // Keyboard navigation
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                handleItemOpen(card);
            }
        });
    });
}

// =============================================================================
// Navigation & Actions
// =============================================================================

/**
 * Navigates to a folder and updates the URL.
 * @param {string} folderId - Target folder ID
 */
async function navigateToFolder(folderId) {
    // Update URL without page reload
    const newUrl = folderId === 'root' 
        ? '/admin/browse'
        : `/admin/browse/${folderId}`;
    window.history.pushState({ folderId }, '', newUrl);
    
    // Fetch and render
    await loadFolder(folderId);
}

/**
 * Loads folder contents from API.
 * @param {string} folderId - Folder to load
 */
async function loadFolder(folderId) {
    ExplorerState.isLoading = true;
    ExplorerState.currentFolderId = folderId;
    renderItems();
    
    try {
        const data = await API.browse(folderId);
        ExplorerState.items = data.items;
        ExplorerState.breadcrumbs = data.breadcrumbs;
        ExplorerState.isLoading = false;
        
        renderBreadcrumbs();
        renderItems();
    } catch (error) {
        console.error('Failed to load folder:', error);
        ExplorerState.isLoading = false;
        renderItems();
        showToast('Failed to load folder', 'error');
    }
}

/**
 * Handles opening an item (double-click action).
 * @param {HTMLElement} card - The item card element
 */
function handleItemOpen(card) {
    const type = card.dataset.type;
    const fsId = card.dataset.fsId;
    const playgroundId = card.dataset.playgroundId;
    
    if (type === 'folder') {
        // Navigate into folder using fs_id
        navigateToFolder(fsId);
    } else if (type === 'playground') {
        // Navigate to editor using playground_id
        window.location.href = `/launch?playground_id=${playgroundId}&role=professor`;
    }
}

/**
 * Selects an item card.
 * @param {HTMLElement} card - The item card element
 */
function selectItem(card) {
    // Deselect previous
    DOM.itemsGrid.querySelectorAll('.item-card.selected').forEach(el => {
        el.classList.remove('selected');
    });
    
    // Select new
    card.classList.add('selected');
    ExplorerState.selectedItem = {
        fsId: card.dataset.fsId,
        type: card.dataset.type,
        playgroundId: card.dataset.playgroundId,
        element: card
    };
}

// =============================================================================
// Modal Functions
// =============================================================================

/**
 * Opens the create/rename modal.
 * @param {'folder'|'instance'|'rename'} mode - Modal mode
 * @param {Object} [existingItem] - For rename mode, the item being renamed
 */
function openModal(mode, existingItem = null) {
    ExplorerState.modalMode = mode;
    
    const titles = {
        folder: 'Create New Folder',
        instance: 'Create New Instance',
        rename: 'Rename Item'
    };
    
    const hints = {
        folder: 'Folders help you organize your bot instances.',
        instance: 'Instances are AI assistants you can configure.',
        rename: 'Enter a new name for this item.'
    };
    
    DOM.modalTitle.textContent = titles[mode];
    DOM.inputHint.textContent = hints[mode];
    DOM.itemNameInput.value = existingItem ? existingItem.name : '';
    DOM.itemNameInput.placeholder = mode === 'folder' ? 'Folder name...' : 'Instance name...';
    DOM.modalCreateBtn.textContent = mode === 'rename' ? 'Save' : 'Create';
    
    DOM.createModal.classList.remove('hidden');
    DOM.itemNameInput.focus();
    DOM.itemNameInput.select();
}

/**
 * Closes the modal.
 */
function closeModal() {
    DOM.createModal.classList.add('hidden');
    DOM.itemNameInput.value = '';
    ExplorerState.modalMode = null;
}

/**
 * Handles modal form submission.
 */
async function handleModalSubmit() {
    const name = DOM.itemNameInput.value.trim();
    
    if (!name) {
        DOM.itemNameInput.classList.add('error');
        return;
    }
    
    DOM.modalCreateBtn.disabled = true;
    DOM.modalCreateBtn.textContent = 'Creating...';
    
    try {
        let newItem;
        const { modalMode, currentFolderId, contextTarget } = ExplorerState;
        
        if (modalMode === 'folder') {
            newItem = await API.createFolder(name, currentFolderId);
            showToast(`Folder "${name}" created`, 'success');
        } else if (modalMode === 'instance') {
            newItem = await API.createPlayground(name, currentFolderId);
            showToast(`Instance "${name}" created`, 'success');
        } else if (modalMode === 'rename' && contextTarget) {
            newItem = await API.renameItem(contextTarget.fsId, name);
            showToast(`Renamed to "${name}"`, 'success');
        }
        
        closeModal();
        
        // Refresh the current folder
        await loadFolder(currentFolderId);
        
    } catch (error) {
        console.error('Modal action failed:', error);
        showToast(error.message, 'error');
    } finally {
        DOM.modalCreateBtn.disabled = false;
        DOM.modalCreateBtn.textContent = ExplorerState.modalMode === 'rename' ? 'Save' : 'Create';
    }
}

// =============================================================================
// Context Menu
// =============================================================================

/**
 * Shows the context menu at the specified position.
 * @param {MouseEvent} event - The right-click event
 * @param {HTMLElement} card - The item card
 */
function showContextMenu(event, card) {
    selectItem(card);
    
    ExplorerState.contextTarget = {
        fsId: card.dataset.fsId,
        type: card.dataset.type,
        playgroundId: card.dataset.playgroundId,
        name: card.querySelector('.item-name').textContent
    };
    
    // Position menu
    const menu = DOM.contextMenu;
    menu.style.left = `${event.clientX}px`;
    menu.style.top = `${event.clientY}px`;
    menu.classList.remove('hidden');
    
    // Adjust if off-screen
    const rect = menu.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
        menu.style.left = `${window.innerWidth - rect.width - 10}px`;
    }
    if (rect.bottom > window.innerHeight) {
        menu.style.top = `${window.innerHeight - rect.height - 10}px`;
    }
}

/**
 * Hides the context menu.
 */
function hideContextMenu() {
    DOM.contextMenu.classList.add('hidden');
    ExplorerState.contextTarget = null;
}

/**
 * Handles context menu actions.
 * @param {string} action - The action to perform
 */
async function handleContextAction(action) {
    const target = ExplorerState.contextTarget;
    if (!target) return;
    
    hideContextMenu();
    
    switch (action) {
        case 'open':
            if (target.type === 'folder') {
                navigateToFolder(target.fsId);
            } else {
                window.location.href = `/launch?playground_id=${target.playgroundId}&role=professor`;
            }
            break;
            
        case 'rename':
            openModal('rename', { name: target.name });
            break;
            
        case 'delete':
            if (confirm(`Are you sure you want to delete "${target.name}"?`)) {
                try {
                    await API.deleteItem(target.fsId);
                    showToast(`"${target.name}" deleted`, 'success');
                    await loadFolder(ExplorerState.currentFolderId);
                } catch (error) {
                    showToast(error.message, 'error');
                }
            }
            break;
            
        case 'move':
            // TODO: Implement move modal
            showToast('Move functionality coming soon', 'info');
            break;
    }
}

// =============================================================================
// Toast Notifications
// =============================================================================

/**
 * Shows a toast notification.
 * @param {string} message - The message to display
 * @param {'success'|'error'|'info'} type - Toast type
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    DOM.toastContainer.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Escapes HTML entities in a string.
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// =============================================================================
// Event Listeners
// =============================================================================

function initEventListeners() {
    // New Instance buttons
    DOM.newInstanceBtn.addEventListener('click', () => openModal('instance'));
    DOM.emptyNewInstanceBtn.addEventListener('click', () => openModal('instance'));
    
    // New Folder button
    DOM.newFolderBtn.addEventListener('click', () => openModal('folder'));
    
    // Modal controls
    DOM.modalCloseBtn.addEventListener('click', closeModal);
    DOM.modalCancelBtn.addEventListener('click', closeModal);
    DOM.modalCreateBtn.addEventListener('click', handleModalSubmit);
    
    // Modal keyboard shortcuts
    DOM.itemNameInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            handleModalSubmit();
        } else if (e.key === 'Escape') {
            closeModal();
        }
    });
    
    // Close modal on backdrop click
    DOM.createModal.querySelector('.modal-backdrop').addEventListener('click', closeModal);
    
    // Context menu actions
    DOM.contextMenu.querySelectorAll('.context-item').forEach(item => {
        item.addEventListener('click', () => handleContextAction(item.dataset.action));
    });
    
    // Hide context menu on click outside
    document.addEventListener('click', (e) => {
        if (!DOM.contextMenu.contains(e.target)) {
            hideContextMenu();
        }
    });
    
    // Deselect on clicking empty area
    DOM.itemsGrid.addEventListener('click', (e) => {
        if (e.target === DOM.itemsGrid) {
            DOM.itemsGrid.querySelectorAll('.item-card.selected').forEach(el => {
                el.classList.remove('selected');
            });
            ExplorerState.selectedItem = null;
        }
    });
    
    // Handle browser back/forward navigation
    window.addEventListener('popstate', (e) => {
        const folderId = e.state?.folderId || 'root';
        loadFolder(folderId);
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ignore if typing in input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        if (e.key === 'Delete' && ExplorerState.selectedItem) {
            handleContextAction('delete');
        }
    });
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    
    // Load initial folder from URL or server-provided value
    const folderId = typeof INITIAL_FOLDER_ID !== 'undefined' ? INITIAL_FOLDER_ID : 'root';
    loadFolder(folderId);
});
