/**
 * Upload Manager & File Manager
 * Handles file uploads using Dropzone.js and file management (list/delete)
 */

// Disable Dropzone auto-discover
Dropzone.autoDiscover = false;

let fileDropzone = null;
let currentFiles = []; // Store current files for reference

// Open/close upload modal
function openUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) {
        modal.style.display = 'flex';
        loadFiles(); // Load files when modal opens
    }
}

function closeUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    if (fileDropzone) {
        fileDropzone.removeAllFiles(true);
    }
}

// --- Canvas Files Modal Logic ---

function openCanvasFilesModal() {
    // Close the file manager modal first
    closeUploadModal();
    
    const modal = document.getElementById('canvas-files-modal');
    if (modal) {
        modal.style.display = 'flex';
        loadCanvasFiles();
    }
}

function closeCanvasFilesModal() {
    const modal = document.getElementById('canvas-files-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    // Re-open the file manager modal
    openUploadModal();
}

function loadCanvasFiles() {
    const loading = document.getElementById('canvas-file-list-loading');
    const empty = document.getElementById('canvas-file-list-empty');
    const table = document.getElementById('canvas-file-table');
    const tbody = document.getElementById('canvas-file-list-body');

    if (loading) loading.style.display = 'block';
    if (empty) empty.style.display = 'none';
    if (table) table.style.display = 'none';
    if (tbody) tbody.innerHTML = '';

    fetch(`/api/playgrounds/${PLAYGROUND_ID}/canvas-files/statuses`)
        .then(res => res.json())
        .then(data => {
            if (loading) loading.style.display = 'none';
            const files = data.file_statuses || [];
            
            if (files.length === 0) {
                if (empty) empty.style.display = 'block';
            } else {
                if (table) table.style.display = 'table';
                renderCanvasFiles(files);
            }
        })
        .catch(err => {
            console.error('Error loading Canvas files:', err);
            if (loading) {
                loading.innerText = 'Error loading Canvas files.';
                loading.style.color = 'red';
            }
        });
}

function renderCanvasFiles(files) {
    const tbody = document.getElementById('canvas-file-list-body');
    if (!tbody) return;

    tbody.innerHTML = '';

    files.forEach(file => {
        const tr = document.createElement('tr');
        
        // Name
        const tdName = document.createElement('td');
        tdName.textContent = file.name || file.filename || 'Unknown';
        tr.appendChild(tdName);

        // Status
        const tdStatus = document.createElement('td');
        const statusSpan = document.createElement('span');
        statusSpan.textContent = formatStatus(file.status);
        statusSpan.className = `status-badge status-${file.status}`;
        // Add some basic styling for status badges
        statusSpan.style.padding = '4px 8px';
        statusSpan.style.borderRadius = '4px';
        statusSpan.style.fontSize = '0.85em';
        statusSpan.style.fontWeight = '600';
        
        if (file.status === 'up_to_date') {
            statusSpan.style.backgroundColor = '#d1fae5';
            statusSpan.style.color = '#065f46';
        } else if (file.status === 'out_of_date') {
            statusSpan.style.backgroundColor = '#fef3c7';
            statusSpan.style.color = '#92400e';
        } else if (file.status === 'missing') {
            statusSpan.style.backgroundColor = '#fee2e2';
            statusSpan.style.color = '#b91c1c';
        } else {
            statusSpan.style.backgroundColor = '#f3f4f6';
            statusSpan.style.color = '#374151';
        }
        
        tdStatus.appendChild(statusSpan);
        tr.appendChild(tdStatus);

        // Last Updated
        const tdUpdated = document.createElement('td');
        tdUpdated.textContent = file.last_updated ? new Date(file.last_updated).toLocaleDateString() : '-';
        tr.appendChild(tdUpdated);

        // Action
        const tdAction = document.createElement('td');
        const actionBtn = document.createElement('button');
        
        // Standardize button style
        actionBtn.style.width = '100px';
        actionBtn.style.justifyContent = 'center';

        if (file.status === 'up_to_date') {
            actionBtn.textContent = 'Synced';
            actionBtn.disabled = true;
            actionBtn.className = 'btn-secondary btn-sm';
            actionBtn.style.opacity = '0.6';
            actionBtn.style.cursor = 'not-allowed';
        } else if (file.status === 'out_of_date') {
            actionBtn.innerHTML = '🔄 Reload';
            actionBtn.className = 'btn-primary btn-sm';
            actionBtn.title = 'Refresh file content';
            actionBtn.onclick = () => refreshCanvasFile(actionBtn, file.id);
        } else if (file.status === 'missing') {
            actionBtn.innerHTML = '➕ Add';
            actionBtn.className = 'btn-primary btn-sm';
            actionBtn.title = 'Add file to playground';
            actionBtn.onclick = () => addCanvasFile(actionBtn, file.canvas_id);
        } else {
            actionBtn.textContent = '-';
            actionBtn.disabled = true;
        }
        
        tdAction.appendChild(actionBtn);
        tr.appendChild(tdAction);

        tbody.appendChild(tr);
    });
}

function formatStatus(status) {
    if (!status) return 'Unknown';
    return status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function refreshCanvasFile(btn, fileId) {
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Refreshing...';

    fetch(`/api/playgrounds/${PLAYGROUND_ID}/canvas-files/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: fileId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            loadCanvasFiles();
            document.dispatchEvent(new CustomEvent('files-uploaded'));
        } else {
            alert('Error refreshing file: ' + (data.message || 'Unknown error'));
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    })
    .catch(err => {
        console.error('Error refreshing file:', err);
        alert('Error refreshing file.');
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
}

function addCanvasFile(btn, canvasFileId) {
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Adding...';

    fetch(`/api/playgrounds/${PLAYGROUND_ID}/canvas-files/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ canvas_file_id: canvasFileId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            loadCanvasFiles();
            document.dispatchEvent(new CustomEvent('files-uploaded'));
        } else {
            alert('Error adding file: ' + (data.message || 'Unknown error'));
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    })
    .catch(err => {
        console.error('Error adding file:', err);
        alert('Error adding file.');
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
}

// --- File Manager Logic ---

function loadFiles() {
    const loading = document.getElementById('file-list-loading');
    const empty = document.getElementById('file-list-empty');
    const table = document.getElementById('file-manager-table');
    const deleteBtn = document.getElementById('delete-files-btn');
    const selectAll = document.getElementById('select-all-files');

    if (loading) loading.style.display = 'block';
    if (empty) empty.style.display = 'none';
    if (table) table.style.display = 'none';
    if (deleteBtn) deleteBtn.disabled = true;
    if (selectAll) selectAll.checked = false;

    fetch(`/api/playgrounds/${PLAYGROUND_ID}/files`)
        .then(res => res.json())
        .then(data => {
            if (loading) loading.style.display = 'none';
            currentFiles = data.files || [];
            
            if (currentFiles.length === 0) {
                if (empty) empty.style.display = 'block';
            } else {
                if (table) table.style.display = 'table';
                renderFiles(currentFiles);
            }
        })
        .catch(err => {
            console.error('Error loading files:', err);
            if (loading) {
                loading.innerText = 'Error loading files.';
                loading.style.color = 'red';
            }
        });
}

function renderFiles(files) {
    const tbody = document.getElementById('file-list-body');
    if (!tbody) return;

    tbody.innerHTML = '';

    files.forEach(file => {
        const tr = document.createElement('tr');
        
        // Checkbox
        const tdSelect = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'file-select-checkbox';
        checkbox.value = file.id; // Assuming file object has 'id'
        checkbox.onchange = updateDeleteButton;
        tdSelect.appendChild(checkbox);
        tr.appendChild(tdSelect);

        // Name
        const tdName = document.createElement('td');
        tdName.textContent = file.filename || file.name || 'Unknown';
        tr.appendChild(tdName);

        // Type
        const tdType = document.createElement('td');
        // Map type to user-friendly text/color if needed
        tdType.textContent = file.content_type || 'Unknown'; 
        tr.appendChild(tdType);
        // Size
        const tdSize = document.createElement('td');
        tdSize.textContent = formatFileSize(file.size);
        tr.appendChild(tdSize);

        tbody.appendChild(tr);
    });
}

function formatFileSize(bytes) {
    if (!bytes) return '-';
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Byte';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
}

function updateDeleteButton() {
    const checkboxes = document.querySelectorAll('.file-select-checkbox:checked');
    const deleteBtn = document.getElementById('delete-files-btn');
    if (deleteBtn) {
        deleteBtn.disabled = checkboxes.length === 0;
        deleteBtn.textContent = checkboxes.length > 0 ? `Delete Selected (${checkboxes.length})` : 'Delete Selected';
    }
}

function toggleSelectAll() {
    const selectAll = document.getElementById('select-all-files');
    const checkboxes = document.querySelectorAll('.file-select-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
    updateDeleteButton();
}

function deleteSelectedFiles() {
    const checkboxes = document.querySelectorAll('.file-select-checkbox:checked');
    const fileIds = Array.from(checkboxes).map(cb => cb.value);

    if (fileIds.length === 0) return;

    if (!confirm(`Are you sure you want to delete ${fileIds.length} file(s)?`)) {
        return;
    }

    const deleteBtn = document.getElementById('delete-files-btn');
    const originalText = deleteBtn.textContent;
    deleteBtn.disabled = true;
    deleteBtn.textContent = 'Deleting...';

    fetch(`/api/playgrounds/${PLAYGROUND_ID}/files/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_ids: fileIds })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // Refresh list
            loadFiles();
            // Also refresh the graph as files are removed
            document.dispatchEvent(new CustomEvent('files-uploaded')); 
        } else {
            alert('Error deleting files: ' + (data.message || 'Unknown error'));
            deleteBtn.disabled = false;
            deleteBtn.textContent = originalText;
        }
    })
    .catch(err => {
        console.error('Error deleting files:', err);
        alert('Error deleting files.');
        deleteBtn.disabled = false;
        deleteBtn.textContent = originalText;
    });
}


// --- Dropzone Logic ---

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Upload button handler
    const uploadBtn = document.getElementById('upload-files-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', openUploadModal);
    }

    // Select All handler
    const selectAll = document.getElementById('select-all-files');
    if (selectAll) {
        selectAll.addEventListener('change', toggleSelectAll);
    }
    
    // Initialize Dropzone with signed URL pattern
    const dropzoneElement = document.getElementById('file-dropzone');
    if (dropzoneElement) {
        // Track active registrations to prevent race condition
        let activeRegistrations = 0;

        fileDropzone = new Dropzone('#file-dropzone', {
            url: '/placeholder', // Will be overridden per file
            method: 'put',
            parallelUploads: 3,
            maxFilesize: 500, // MB
            acceptedFiles: '.pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.html,.png,.jpg,.jpeg,.gif',
            addRemoveLinks: true,
            
            // Get signed URL before each upload
            accept: function(file, done) {
                fetch(`/api/playgrounds/${PLAYGROUND_ID}/generate-upload-url`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filename: file.name,
                        content_type: file.type || 'application/octet-stream',
                        size: file.size
                    })
                })
                .then(res => res.json())
                .then(data => {
                    file.uploadUrl = data.upload_url;
                    file.gcsUri = data.gcs_uri;
                    file.fileId = data.file_id;
                    done();
                })
                .catch(err => {
                    done('Failed to upload file, please try again later.');
                });
            },
            
            // Use the signed URL for this specific file
            processing: function(file) {
                this.options.url = file.uploadUrl;
            },
            
            // Send raw file body (not form data) for GCS signed URLs
            sending: function(file, xhr, formData) {
                // Override to send raw file
                const _send = xhr.send;
                xhr.send = function() {
                    _send.call(xhr, file);
                };
                xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
            },
            
            // Register file in Firestore after successful GCS upload
            success: function(file, response) {
                activeRegistrations++;
                fetch(`/api/playgrounds/${PLAYGROUND_ID}/files/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        file_id: file.fileId,
                        filename: file.name,
                        content_type: file.type || 'application/octet-stream',
                        size: file.size,
                        gcs_uri: file.gcsUri
                    })
                })
                .then((res) => {
                    if (!res.ok) {
                        throw new Error('Registration failed');
                    }
                    return res.json();
                })
                .then(data => {
                    console.log('File registered:', data);
                    // Refresh the file list immediately to show the new file
                    loadFiles();
                })
                .catch(err => {
                    console.error('Error registering file:', err);
                    file.status = Dropzone.ERROR;
                    fileDropzone.emit("error", file, "Failed to register file");
                })
                .finally(() => {
                    activeRegistrations--;
                    checkAllComplete();
                });
            },
            
            error: function(file, errorMessage) {
                console.error('Upload error:', errorMessage);
            }
        });

        // Helper to check if all files are fully processed (uploaded AND registered)
        function checkAllComplete() {
            if (fileDropzone.getUploadingFiles().length === 0 && 
                fileDropzone.getQueuedFiles().length === 0 && 
                activeRegistrations === 0) {
                
                console.log('All uploads and registrations complete. Refreshing graph...');
                // Dispatch event to refresh graph
                document.dispatchEvent(new CustomEvent('files-uploaded'));
            }
        }
    }
});
