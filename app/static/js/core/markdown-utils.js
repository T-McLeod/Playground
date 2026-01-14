/**
 * Markdown & Math Rendering Utilities
 * Shared utilities for rendering markdown with LaTeX math support
 */

/**
 * Render markdown with LaTeX math support
 * Supports inline math: $...$  and display math: $$...$$
 * @param {string} content - The markdown/math content to render
 * @returns {string} HTML string with rendered markdown and math
 */
function renderMarkdownWithMath(content) {
    if (!content) return '';
    
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

// Export for ES modules (if used) or attach to window for global access
if (typeof window !== 'undefined') {
    window.MarkdownUtils = {
        renderMarkdownWithMath
    };
}
