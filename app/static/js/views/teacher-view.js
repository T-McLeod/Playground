/**
 * Teacher View
 * Extends BaseView with teacher-specific topic management functionality
 */

class TeacherView extends BaseView {
    constructor(playgroundId, userId) {
        super(playgroundId, userId);
        this.showModalIcon = true; // Teachers see icons in modal
        this.editingTopic = null; // Track topic being edited
    }

    /**
     * Cache additional teacher-specific DOM elements
     */
    cacheDOMElements() {
        super.cacheDOMElements();
        
        // Topic management elements
        this.elements.removeTopicBtn = document.getElementById('remove-topic-btn');
        this.elements.editTopicBtn = document.getElementById('edit-topic-btn');
        
        // Edit Modal Elements
        this.elements.editTopicModal = document.getElementById('edit-topic-modal');
        this.elements.editTopicClose = document.getElementById('edit-topic-close');
        this.elements.editTopicTitleInput = document.getElementById('edit-topic-title-input');
        this.elements.editTopicSummaryInput = document.getElementById('edit-topic-summary-input');
        this.elements.editResourceList = document.getElementById('edit-resource-list');
        this.elements.addResourceSelect = document.getElementById('add-resource-select');
        this.elements.addResourceBtn = document.getElementById('add-resource-btn');
        this.elements.saveTopicChangesBtn = document.getElementById('save-topic-changes-btn');
        this.elements.cancelTopicChangesBtn = document.getElementById('cancel-topic-changes-btn');

        this.elements.addTopicBtn = document.getElementById('add-topic-btn');
        this.elements.addTopicModal = document.getElementById('add-topic-modal');
        this.elements.addTopicClose = document.getElementById('add-topic-close');
        this.elements.addTopicCancel = document.getElementById('add-topic-cancel-btn');
        this.elements.addTopicSave = document.getElementById('add-topic-save-btn');
        this.elements.newTopicName = document.getElementById('new-topic-name');
        this.elements.newTopicSummary = document.getElementById('new-topic-summary');
    }

    /**
     * Initialize teacher-specific event listeners
     */
    initializeEventListeners() {
        super.initializeEventListeners();
        
        this.initRemoveTopicHandler();
        this.initEditTopicHandlers();
        this.initAddTopicHandlers();
    }

    /**
     * Initialize edit topic handlers
     */
    initEditTopicHandlers() {
        const { 
            editTopicBtn, editTopicClose, saveTopicChangesBtn, cancelTopicChangesBtn,
            addResourceBtn
        } = this.elements;
        
        if (editTopicBtn) {
            editTopicBtn.addEventListener('click', () => this.openEditTopicModal());
        }
        if (editTopicClose) {
            editTopicClose.addEventListener('click', () => this.closeEditTopicModal());
        }
        if (cancelTopicChangesBtn) {
            cancelTopicChangesBtn.addEventListener('click', () => this.closeEditTopicModal());
        }
        if (saveTopicChangesBtn) {
            saveTopicChangesBtn.addEventListener('click', () => this.saveTopicChanges());
        }
        if (addResourceBtn) {
            addResourceBtn.addEventListener('click', () => this.handleAddResource());
        }
    }

    /**
     * Open edit topic modal and populate with current data
     */
    openEditTopicModal() {
        const currentTopic = ModalManager.getCurrentTopic();
        if (!currentTopic) return;

        this.editingTopic = currentTopic; // Store for saving later

        const { 
            editTopicModal, editTopicTitleInput, editTopicSummaryInput, 
            addResourceSelect 
        } = this.elements;

        // Close view modal
        ModalManager.closeModal();

        // Populate fields
        editTopicTitleInput.value = currentTopic.label;
        
        const topicData = this.knowledgeGraph.kg_data && this.knowledgeGraph.kg_data[currentTopic.id] 
            ? this.knowledgeGraph.kg_data[currentTopic.id] 
            : {};
        editTopicSummaryInput.value = topicData.summary || '';

        // Populate Resources
        this.renderEditableResources(currentTopic.id);

        // Show edit modal
        if (editTopicModal) {
            editTopicModal.classList.remove('hidden');
            setTimeout(() => editTopicModal.classList.add('show'), 10);
        }
    }

    /**
     * Close edit topic modal and reopen view modal
     */
    closeEditTopicModal() {
        const { editTopicModal } = this.elements;
        const topicToReopen = this.editingTopic;

        if (editTopicModal) {
            editTopicModal.classList.remove('show');
            setTimeout(() => {
                editTopicModal.classList.add('hidden');
                this.editingTopic = null; // Clear stored topic
                
                // Reopen view modal if we have a topic
                if (topicToReopen) {
                    ModalManager.openTopicModal(topicToReopen, this.knowledgeGraph);
                }
            }, 300);
        }
    }

    /**
     * Render resources in editable mode
     */
    renderEditableResources(topicId) {
        const { editResourceList, addResourceSelect } = this.elements;
        if (!editResourceList) return;

        editResourceList.innerHTML = '';
        
        // Get current resources
        const currentResources = ModalManager.getRelatedResources(topicId, this.knowledgeGraph);
        
        // Render current resources
        currentResources.forEach(resource => {
            this.addResourceToEditList(resource);
        });

        // Populate Select Dropdown
        addResourceSelect.innerHTML = '<option value="">Select a file to link...</option>';
        
        const currentResourceIds = new Set(currentResources.map(r => r.id));
        const allFiles = Object.values(this.knowledgeGraph.indexed_files || {});
        const fileNodes = this.knowledgeGraph.kg_nodes.filter(n => n.group === 'file');
        const availableFiles = allFiles.length > 0 ? allFiles : fileNodes;

        availableFiles.forEach(file => {
            const fileId = file.id || file.file_id; 
            if (!currentResourceIds.has(fileId)) {
                const option = document.createElement('option');
                option.value = fileId;
                option.textContent = file.filename || file.label || file.name;
                addResourceSelect.appendChild(option);
            }
        });
    }

    /**
     * Add a resource item to the edit list UI
     */
    addResourceToEditList(resource) {
        const { editResourceList } = this.elements;
        const li = document.createElement('li');
        li.className = 'editable-resource-item';
        
        const span = document.createElement('span');
        span.textContent = resource.label;
        li.appendChild(span);
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '❌';
        removeBtn.className = 'btn-icon-small';
        removeBtn.title = 'Remove connection';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            li.remove();
            // Add back to dropdown if needed (optional enhancement)
        };
        li.appendChild(removeBtn);
        
        // Store ID for saving
        li.dataset.resourceId = resource.id;
        
        editResourceList.appendChild(li);
    }

    /**
     * Handle adding a resource from the dropdown
     */
    handleAddResource() {
        const { addResourceSelect } = this.elements;
        const selectedId = addResourceSelect.value;
        if (!selectedId) return;
        
        const allFiles = Object.values(this.knowledgeGraph.indexed_files || {});
        const fileNodes = this.knowledgeGraph.kg_nodes.filter(n => n.group === 'file');
        const availableFiles = allFiles.length > 0 ? allFiles : fileNodes;

        const selectedFile = availableFiles.find(f => (f.id || f.file_id) === selectedId);
        
        if (selectedFile) {
            const resourceObj = {
                id: selectedId,
                label: selectedFile.filename || selectedFile.label || selectedFile.name
            };
            
            this.addResourceToEditList(resourceObj);
            
            // Remove from select
            const optionToRemove = addResourceSelect.querySelector(`option[value="${selectedId}"]`);
            if (optionToRemove) optionToRemove.remove();
            addResourceSelect.value = '';
        }
    }

    /**
     * Save topic changes
     */
    async saveTopicChanges() {
        const { saveTopicChangesBtn, editTopicTitleInput, editTopicSummaryInput, editResourceList } = this.elements;
        const currentTopic = this.editingTopic;
        
        if (!currentTopic) {
            console.error('No topic being edited');
            return;
        }
        
        const newTitle = editTopicTitleInput.value.trim();
        const newSummary = editTopicSummaryInput.value.trim();
        
        // Gather resources
        const resourceItems = editResourceList.querySelectorAll('li');
        const resourceIds = [];
        resourceItems.forEach(li => {
            resourceIds.push(li.dataset.resourceId);
        });

        try {
            saveTopicChangesBtn.disabled = true;
            saveTopicChangesBtn.textContent = 'Saving...';

            const node_data = {
                id: currentTopic.id,
                topic: newTitle,
                summary: newSummary,
                files: resourceIds
            };
            
            await fetch('/api/edit-topic', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        playground_id: PLAYGROUND_ID,
                        node: node_data
                    })
                });

            if (!response.ok) {
                throw new Error('Failed to update topic');
            }
            
            // Reload the knowledge graph to get updated data
            await this.loadKnowledgeGraph();

            // Update the editing topic reference to the new object from the reloaded graph
            const updatedTopic = this.knowledgeGraph.kg_nodes.find(n => n.id === currentTopic.id);
            if (updatedTopic) {
                this.editingTopic = updatedTopic;
            }
            
            UIHelpers.showSuccess('Topic updated successfully!');
            
            // Close edit modal (which reopens view modal with updated data)
            this.closeEditTopicModal();

        } catch (error) {
            console.error('Error saving topic:', error);
            alert('Failed to save changes.');
        } finally {
            saveTopicChangesBtn.disabled = false;
            saveTopicChangesBtn.textContent = 'Save';
        }
    }

    /**
     * Initialize remove topic button handler
     */
    initRemoveTopicHandler() {
        const { removeTopicBtn } = this.elements;
        
        if (removeTopicBtn) {
            removeTopicBtn.addEventListener('click', () => this.handleRemoveTopic());
        }
    }

    /**
     * Initialize add topic modal handlers
     */
    initAddTopicHandlers() {
        const { addTopicBtn, addTopicModal, addTopicClose, addTopicCancel, addTopicSave } = this.elements;

        if (addTopicBtn) {
            addTopicBtn.addEventListener('click', () => this.openAddTopicModal());
        }
        
        if (addTopicClose) {
            addTopicClose.addEventListener('click', () => this.closeAddTopicModal());
        }
        
        if (addTopicCancel) {
            addTopicCancel.addEventListener('click', () => this.closeAddTopicModal());
        }
        
        if (addTopicSave) {
            addTopicSave.addEventListener('click', () => this.handleAddTopic());
        }
    }

    /**
     * Open add topic modal
     */
    openAddTopicModal() {
        const { addTopicModal } = this.elements;
        if (addTopicModal) {
            addTopicModal.classList.remove('hidden');
            setTimeout(() => addTopicModal.classList.add('show'), 10);
        }
    }

    /**
     * Close add topic modal
     */
    closeAddTopicModal() {
        const { addTopicModal } = this.elements;
        if (addTopicModal) {
            addTopicModal.classList.remove('show');
            setTimeout(() => addTopicModal.classList.add('hidden'), 300);
        }
    }

    /**
     * Handle adding a new topic
     */
    async handleAddTopic() {
        const { addTopicSave, newTopicName, newTopicSummary } = this.elements;
        
        const name = newTopicName.value.trim();
        const summary = newTopicSummary.value.trim();
        
        if (!name) {
            alert('Please enter a topic name');
            return;
        }
        
        console.log('Adding topic:', { name, summary });

        try {
            addTopicSave.disabled = true;
            addTopicSave.textContent = 'Adding...';
            
            await ApiClient.addTopic(this.playgroundId, name, summary);
            
            console.log('Topic added successfully');
            
            // Close modal and clear inputs
            this.closeAddTopicModal();
            newTopicName.value = '';
            newTopicSummary.value = '';
            
            // Reload the knowledge graph
            await this.loadKnowledgeGraph();
            
            UIHelpers.showSuccess(`Topic "${name}" added successfully!`);
            
        } catch (error) {
            console.error('Error adding topic:', error);
            alert(error.message || 'Failed to add topic. Please try again.');
        } finally {
            addTopicSave.disabled = false;
            addTopicSave.textContent = 'Save';
        }
    }

    /**
     * Handle removing the current topic
     */
    async handleRemoveTopic() {
        const { removeTopicBtn } = this.elements;
        const currentTopic = ModalManager.getCurrentTopic();
        
        if (!currentTopic) {
            alert('No topic selected');
            return;
        }
        
        const topicName = currentTopic.label;
        const confirmed = confirm(`Are you sure you want to remove the topic "${topicName}"?\n\nThis action cannot be undone.`);
        
        if (!confirmed) {
            return;
        }
        
        try {
            removeTopicBtn.disabled = true;
            removeTopicBtn.textContent = 'Removing...';
            
            await ApiClient.removeTopic(this.playgroundId, currentTopic.id);
            
            console.log('Topic removed successfully');
            
            // Close modal
            ModalManager.closeModal();
            
            // Reload the knowledge graph
            await this.loadKnowledgeGraph();
            
            UIHelpers.showSuccess(`Topic "${topicName}" removed successfully!`);
            
        } catch (error) {
            console.error('Error removing topic:', error);
            alert(error.message || 'Failed to remove topic. Please try again.');
        } finally {
            removeTopicBtn.disabled = false;
            removeTopicBtn.textContent = '🗑️ Remove Topic';
        }
    }
}

// Export for ES modules or attach to window
if (typeof window !== 'undefined') {
    window.TeacherView = TeacherView;
}
