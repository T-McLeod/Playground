/**
 * UI Helper Utilities
 * Shared utilities for loading states, error handling, and animations
 */

/**
 * Show loading overlay with a message
 * @param {string} message - The loading message to display
 */
function showLoading(message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    
    const p = overlay.querySelector('p');
    if (p) p.textContent = message;
    overlay.classList.remove('hidden');
}

/**
 * Hide the loading overlay
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
}

/**
 * Show a toast error notification
 * @param {string} message - The error message to display
 * @param {number} duration - How long to show the toast (ms)
 */
function showError(message, duration = 5000) {
    const toast = document.createElement('div');
    toast.className = 'toast-error';
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
    }, duration);
}

/**
 * Show a toast success notification
 * @param {string} message - The success message to display
 * @param {number} duration - How long to show the toast (ms)
 */
function showSuccess(message, duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast-success';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
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
    }, duration);
}

/**
 * Initialize animation styles (call once on page load)
 */
function initAnimationStyles() {
    const style = document.createElement('style');
    style.id = 'ui-helper-animations';
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
    
    // Only add if not already present
    if (!document.getElementById('ui-helper-animations')) {
        document.head.appendChild(style);
    }
}

// Initialize animations on load
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAnimationStyles);
    } else {
        initAnimationStyles();
    }
}

// Export for ES modules or attach to window
if (typeof window !== 'undefined') {
    window.UIHelpers = {
        showLoading,
        hideLoading,
        showError,
        showSuccess,
        initAnimationStyles
    };
}
