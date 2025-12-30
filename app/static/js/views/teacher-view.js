/**
 * Teacher View
 * Extends BaseView with teacher-specific topic management functionality
 */

class TeacherView extends BaseView {
    constructor(playgroundId, userId) {
        super(playgroundId, userId);
        this.showModalIcon = true; // Teachers see icons in modal
    }

    /**
     * Cache additional teacher-specific DOM elements
     */
    cacheDOMElements() {
        super.cacheDOMElements();
        
        // Topic management elements
        this.elements.removeTopicBtn = document.getElementById('remove-topic-btn');
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
        this.initAddTopicHandlers();
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
