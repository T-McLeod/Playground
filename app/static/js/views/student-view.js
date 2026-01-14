/**
 * Student View
 * Extends BaseView with student-specific chat functionality
 */

class StudentView extends BaseView {
    constructor(playgroundId, userId) {
        super(playgroundId, userId);
        this.chatMessages = [];
        this.isChatExpanded = false;
        this.showModalIcon = false; // Students see simpler modal
    }

    /**
     * Cache additional student-specific DOM elements
     */
    cacheDOMElements() {
        super.cacheDOMElements();
        
        // Chat-specific elements
        this.elements.chatPrompt = document.getElementById('chat-prompt');
        this.elements.promptInput = document.getElementById('prompt-input');
        this.elements.chatExpandFab = document.getElementById('chat-expand-fab');
        this.elements.chatContainer = document.getElementById('chat-container');
        this.elements.chatCollapseBtn = document.getElementById('chat-collapse');
        this.elements.chatHeader = document.querySelector('.chat-header');
        this.elements.chatMessagesContainer = document.getElementById('chat-messages');
        this.elements.chatInput = document.getElementById('chat-input');
        this.elements.sendBtn = document.getElementById('send-btn');
        this.elements.typingIndicator = document.getElementById('typing-indicator');
        
        // Modal chat elements
        this.elements.modalChatInput = document.getElementById('modal-chat-input');
        this.elements.modalSendBtn = document.getElementById('modal-send-btn');
        this.elements.modalChatMessages = document.getElementById('modal-chat-messages');
    }

    /**
     * Initialize student-specific event listeners
     */
    initializeEventListeners() {
        super.initializeEventListeners();
        
        this.initChatInterface();
        this.initModalChat();
    }

    /**
     * Initialize the main chat interface
     */
    initChatInterface() {
        const { promptInput, chatExpandFab, chatCollapseBtn, chatHeader, 
                sendBtn, chatInput } = this.elements;

        // Chat prompt input handler
        if (promptInput) {
            promptInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && promptInput.value.trim()) {
                    e.preventDefault();
                    const query = promptInput.value.trim();
                    chatInput.value = query;
                    promptInput.value = '';
                    this.sendMessage();
                }
            });
        }

        // Floating expand button
        if (chatExpandFab) {
            chatExpandFab.addEventListener('click', () => this.expandChat());
        }

        // Chat collapse/expand toggle
        if (chatCollapseBtn) {
            chatCollapseBtn.addEventListener('click', () => this.toggleChat());
        }
        if (chatHeader) {
            chatHeader.addEventListener('click', () => this.toggleChat());
        }

        // Chat input handlers
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        if (chatInput) {
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // Auto-resize textarea
            chatInput.addEventListener('input', () => {
                chatInput.style.height = 'auto';
                chatInput.style.height = chatInput.scrollHeight + 'px';
            });
        }

        // Escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isChatExpanded) {
                this.collapseChat();
            }
        });
    }

    /**
     * Initialize modal chat handlers
     */
    initModalChat() {
        const { modalSendBtn, modalChatInput } = this.elements;
        
        if (modalSendBtn && modalChatInput) {
            modalSendBtn.addEventListener('click', () => this.sendModalMessage());
            modalChatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendModalMessage();
                }
            });
            modalChatInput.addEventListener('input', () => {
                modalChatInput.style.height = 'auto';
                modalChatInput.style.height = modalChatInput.scrollHeight + 'px';
            });
        }
    }

    /**
     * Override openTopicModal to clear modal chat
     */
    openTopicModal(topic) {
        // Clear modal chat when opening
        if (this.elements.modalChatMessages) {
            this.elements.modalChatMessages.innerHTML = '';
        }
        if (this.elements.modalChatInput) {
            this.elements.modalChatInput.value = '';
            this.elements.modalChatInput.style.height = 'auto';
        }
        this.hideModalTypingIndicator();
        
        super.openTopicModal(topic);
    }

    // ===========================
    // CHAT TOGGLE
    // ===========================

    toggleChat() {
        if (this.isChatExpanded) {
            this.collapseChat();
        } else {
            this.expandChat();
        }
    }

    expandChat() {
        this.isChatExpanded = true;
        this.elements.chatContainer.classList.remove('collapsed');
        this.elements.chatContainer.classList.add('expanded');
        
        if (this.elements.chatExpandFab) {
            this.elements.chatExpandFab.classList.remove('visible');
        }
        
        const collapseIcon = document.getElementById('collapse-icon');
        if (collapseIcon) {
            collapseIcon.style.transform = 'rotate(180deg)';
        }
        
        setTimeout(() => this.elements.chatInput.focus(), 300);
    }

    collapseChat() {
        this.isChatExpanded = false;
        this.elements.chatContainer.classList.remove('expanded');
        this.elements.chatContainer.classList.add('collapsed');
        
        if (this.elements.chatExpandFab) {
            this.elements.chatExpandFab.classList.add('visible');
        }
        
        const collapseIcon = document.getElementById('collapse-icon');
        if (collapseIcon) {
            collapseIcon.style.transform = 'rotate(0deg)';
        }
    }

    // ===========================
    // MAIN CHAT
    // ===========================

    async sendMessage() {
        const { chatInput, sendBtn, typingIndicator, chatMessagesContainer } = this.elements;
        const query = chatInput.value.trim();
        if (!query) return;

        // Expand chat if not already expanded
        if (!this.isChatExpanded) {
            this.expandChat();
        }

        // Disable input while sending
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // Add user message to chat
        this.addMessage({ role: 'user', content: query });

        // Clear input
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Show typing indicator
        typingIndicator.classList.remove('hidden');

        try {
            const data = await ApiClient.sendChatMessage(this.playgroundId, query);

            this.addMessage({
                role: 'assistant',
                content: data.answer || data.response || 'I received your question but had trouble generating an answer.',
                sources: data.sources || [],
                log_doc_id: data.log_doc_id
            });

        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage({
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

    addMessage(message) {
        this.chatMessages.push(message);
        const { chatMessagesContainer } = this.elements;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role === 'user' ? 'user-message' : 'bot-message'}`;

        const content = document.createElement('div');
        content.className = 'message-content';

        const text = document.createElement('div');
        if (message.role === 'user') {
            text.textContent = message.content;
        } else {
            text.innerHTML = MarkdownUtils.renderMarkdownWithMath(message.content);
        }
        content.appendChild(text);

        // Add sources if available
        if (message.sources && message.sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';
            sourcesDiv.innerHTML = '<strong>Sources:</strong>';
            
            message.sources.forEach(source => {
                if (typeof source === 'string') {
                    const sourceTag = document.createElement('span');
                    sourceTag.className = 'source-tag';
                    sourceTag.textContent = source;
                    sourcesDiv.appendChild(sourceTag);
                } else if (source.filename && source.source_uri) {
                    const sourceLink = document.createElement('a');
                    sourceLink.className = 'source-tag source-link';
                    sourceLink.textContent = source.filename;
                    sourceLink.href = '#';
                    sourceLink.title = `Download ${source.filename}`;
                    
                    sourceLink.addEventListener('click', async (e) => {
                        e.preventDefault();
                        try {
                            const downloadUrl = await ApiClient.getDownloadUrl(source.source_uri);
                            window.open(downloadUrl, '_blank');
                        } catch (error) {
                            console.error('Error downloading source:', error);
                            alert(`Failed to download ${source.filename}. Please try again.`);
                        }
                    });
                    
                    sourcesDiv.appendChild(sourceLink);
                }
            });

            content.appendChild(sourcesDiv);
        }

        // Add rating buttons for bot messages
        if (message.role === 'assistant' && message.log_doc_id) {
            const ratingDiv = document.createElement('div');
            ratingDiv.className = 'message-rating';
            
            const likeBtn = document.createElement('button');
            likeBtn.className = 'rating-btn like-btn';
            likeBtn.textContent = 'Helpful';
            likeBtn.onclick = () => this.rateAnswer(message.log_doc_id, 'helpful', ratingDiv);
            
            const dislikeBtn = document.createElement('button');
            dislikeBtn.className = 'rating-btn dislike-btn';
            dislikeBtn.textContent = 'Not Helpful';
            dislikeBtn.onclick = () => this.rateAnswer(message.log_doc_id, 'not_helpful', ratingDiv);
            
            ratingDiv.appendChild(likeBtn);
            ratingDiv.appendChild(dislikeBtn);
            content.appendChild(ratingDiv);
        }

        messageDiv.appendChild(content);
        chatMessagesContainer.appendChild(messageDiv);
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    async rateAnswer(logDocId, rating, ratingDiv) {
        try {
            await ApiClient.rateAnswer(logDocId, rating);
            ratingDiv.innerHTML = `<span class="rating-feedback">Thanks for your feedback!</span>`;
        } catch (error) {
            console.error('Error rating answer:', error);
            alert('Failed to submit rating. Please try again.');
        }
    }

    // ===========================
    // MODAL CHAT
    // ===========================

    async sendModalMessage() {
        const { modalChatInput, modalSendBtn } = this.elements;
        if (!modalChatInput || !modalSendBtn) return;
        
        const query = modalChatInput.value.trim();
        if (!query) return;

        // Include topic context
        const currentTopic = ModalManager.getCurrentTopic();
        let contextualQuery = query;
        if (currentTopic) {
            contextualQuery = `About "${currentTopic.label}": ${query}`;
        }

        modalChatInput.disabled = true;
        modalSendBtn.disabled = true;

        this.addModalMessage({ role: 'user', content: query });

        modalChatInput.value = '';
        modalChatInput.style.height = 'auto';

        this.showModalTypingIndicator();

        try {
            const data = await ApiClient.sendChatMessage(this.playgroundId, contextualQuery);

            this.hideModalTypingIndicator();

            this.addModalMessage({
                role: 'assistant',
                content: data.answer || data.response || 'I received your question but had trouble generating an answer.',
                sources: data.sources || []
            });

        } catch (error) {
            console.error('Error sending modal message:', error);
            this.hideModalTypingIndicator();
            
            this.addModalMessage({
                role: 'assistant',
                content: 'Sorry, I encountered an error processing your question. Please try again.',
                sources: []
            });
        } finally {
            modalChatInput.disabled = false;
            modalSendBtn.disabled = false;
            modalChatInput.focus();
        }
    }

    showModalTypingIndicator() {
        const { modalChatMessages } = this.elements;
        if (!modalChatMessages) return;
        
        this.hideModalTypingIndicator();
        
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'modal-typing-indicator';
        typingIndicator.id = 'modal-typing-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'typing-avatar';
        avatar.textContent = '🤖';
        
        const dotsContainer = document.createElement('div');
        dotsContainer.className = 'typing-dots';
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dotsContainer.appendChild(dot);
        }
        
        typingIndicator.appendChild(avatar);
        typingIndicator.appendChild(dotsContainer);
        modalChatMessages.appendChild(typingIndicator);
        
        setTimeout(() => {
            modalChatMessages.scrollTop = modalChatMessages.scrollHeight;
        }, 100);
    }

    hideModalTypingIndicator() {
        const typingIndicator = document.getElementById('modal-typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    addModalMessage(message) {
        const { modalChatMessages } = this.elements;
        if (!modalChatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `modal-chat-message ${message.role === 'user' ? 'user' : 'bot'}`;

        const avatar = document.createElement('div');
        avatar.className = 'modal-chat-avatar';
        avatar.textContent = message.role === 'user' ? '👤' : '🤖';

        const content = document.createElement('div');
        content.className = 'modal-chat-content';
        
        if (message.role === 'user') {
            content.textContent = message.content;
        } else {
            content.innerHTML = MarkdownUtils.renderMarkdownWithMath(message.content);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        modalChatMessages.appendChild(messageDiv);

        modalChatMessages.scrollTop = modalChatMessages.scrollHeight;
    }
}

// Export for ES modules or attach to window
if (typeof window !== 'undefined') {
    window.StudentView = StudentView;
}
