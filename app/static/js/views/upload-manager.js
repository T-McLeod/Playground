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
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
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

        // Use CSS classes for styling
        let statusClass = 'status-unknown';
        if (['up_to_date', 'out_of_date', 'missing'].includes(file.status)) {
            statusClass = `status-${file.status}`;
        }
        statusSpan.className = `status-badge ${statusClass}`;

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
            actionBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>Reload';
            actionBtn.className = 'btn-action-reload btn-sm';
            actionBtn.title = 'Refresh file content';
            actionBtn.onclick = () => refreshCanvasFile(actionBtn, file.id);
        } else if (file.status === 'missing') {
            actionBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>Add';
            actionBtn.className = 'btn-action-add btn-sm';
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
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
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
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
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
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            if (loading) loading.style.display = 'none';
            currentFiles = data.files || [];

            // Handle Canvas Files button state
            const canvasFilesBtn = document.getElementById('open-canvas-files-btn');
            if (canvasFilesBtn) {
                if (data.is_canvas_course) {
                    canvasFilesBtn.disabled = false;
                    canvasFilesBtn.title = "Manage Canvas Files";
                    canvasFilesBtn.style.opacity = '1';
                    canvasFilesBtn.style.cursor = 'pointer';
                } else {
                    canvasFilesBtn.disabled = true;
                    canvasFilesBtn.title = "This is not a Canvas-linked course";
                    canvasFilesBtn.style.opacity = '0.5';
                    canvasFilesBtn.style.cursor = 'not-allowed';
                }
            }

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
        const trashIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
        const text = checkboxes.length > 0 ? `Delete Selected (${checkboxes.length})` : 'Delete Selected';
        deleteBtn.innerHTML = trashIcon + ' ' + text;
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

    const deleteBtn = document.getElementById('delete-files-btn');
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="spin">
            <line x1="12" y1="2" x2="12" y2="6"></line>
            <line x1="12" y1="18" x2="12" y2="22"></line>
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
            <line x1="2" y1="12" x2="6" y2="12"></line>
            <line x1="18" y1="12" x2="22" y2="12"></line>
            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
        </svg>
        Deleting...
    `;

    fetch(`/api/playgrounds/${PLAYGROUND_ID}/files/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_ids: fileIds })
    })
        .then(res => res.json())
        .then(data => {
            // Reset button to clean state with icon
            const trashIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
            deleteBtn.innerHTML = trashIcon + ' Delete Selected';
            deleteBtn.disabled = true;

            if (data.success) {
                // Refresh list
                loadFiles();
                // Also refresh the graph as files are removed
                document.dispatchEvent(new CustomEvent('files-uploaded'));
            } else {
                alert('Error deleting files: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(err => {
            console.error('Error deleting files:', err);
            alert('Error deleting files.');
            const trashIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
            deleteBtn.innerHTML = trashIcon + ' Delete Selected';
            deleteBtn.disabled = true;
        });
}


// --- Dropzone Logic ---

// Update the queued file count display
function updateQueuedFileCount() {
    const countSpan = document.getElementById('queued-file-count');
    const uploadBtn = document.getElementById('upload-files-confirm-btn');
    const clearBtn = document.getElementById('clear-queue-btn');

    if (!fileDropzone) return;

    // Count files that can be uploaded (not success, error, or canceled)
    const count = fileDropzone.files.filter(f =>
        f.status !== Dropzone.SUCCESS &&
        f.status !== Dropzone.ERROR &&
        f.status !== Dropzone.CANCELED
    ).length;

    if (countSpan) countSpan.textContent = count;
    if (uploadBtn) uploadBtn.disabled = count === 0;
    if (clearBtn) clearBtn.disabled = fileDropzone.files.length === 0;
}

// Upload all queued files
async function uploadQueuedFiles() {
    if (!fileDropzone) {
        console.log('No dropzone');
        return;
    }

    // Debug: log all files and their statuses
    console.log('All files in dropzone:', fileDropzone.files.map(f => ({
        name: f.name,
        status: f.status
    })));

    // Get all files that haven't been successfully uploaded or errored
    const filesToUpload = fileDropzone.files.filter(f =>
        f.status !== Dropzone.SUCCESS &&
        f.status !== Dropzone.ERROR &&
        f.status !== Dropzone.CANCELED
    );

    if (filesToUpload.length === 0) {
        console.log('No files to upload - all files:', fileDropzone.files.length);
        return;
    }

    console.log('Starting upload for', filesToUpload.length, 'files');

    const uploadBtn = document.getElementById('upload-files-confirm-btn');
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="spin">
                <line x1="12" y1="2" x2="12" y2="6"></line>
                <line x1="12" y1="18" x2="12" y2="22"></line>
                <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                <line x1="2" y1="12" x2="6" y2="12"></line>
                <line x1="18" y1="12" x2="22" y2="12"></line>
                <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
            </svg>
            Uploading...
        `;
    }

    // Upload each file manually
    for (const file of filesToUpload) {
        try {
            // 1. Get signed upload URL
            const urlResponse = await fetch(`/api/playgrounds/${PLAYGROUND_ID}/generate-upload-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: file.name,
                    content_type: file.type || 'application/pdf',
                    size: file.size
                })
            });

            if (!urlResponse.ok) {
                const errorData = await urlResponse.json();
                throw new Error(errorData.message || errorData.error || 'Failed to get upload URL');
            }

            const urlData = await urlResponse.json();
            console.log('Got upload URL for', file.name);

            // 2. Upload file to GCS
            const uploadResponse = await fetch(urlData.upload_url, {
                method: 'PUT',
                headers: { 'Content-Type': file.type || 'application/pdf' },
                body: file
            });

            if (!uploadResponse.ok) {
                throw new Error('Failed to upload to storage');
            }

            console.log('Uploaded', file.name, 'to GCS');

            // 3. Register file in Firestore
            const registerResponse = await fetch(`/api/playgrounds/${PLAYGROUND_ID}/files/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: urlData.file_id,
                    filename: file.name,
                    content_type: file.type || 'application/pdf',
                    size: file.size,
                    gcs_uri: urlData.gcs_uri
                })
            });

            if (!registerResponse.ok) {
                throw new Error('Failed to register file');
            }

            console.log('Registered', file.name);

            // Mark file as success in dropzone
            file.status = Dropzone.SUCCESS;
            fileDropzone.emit('success', file);
            fileDropzone.emit('complete', file);

        } catch (error) {
            console.error('Upload failed for', file.name, ':', error);
            file.status = Dropzone.ERROR;
            fileDropzone.emit('error', file, error.message);
            fileDropzone.emit('complete', file);
        }
    }

    // All done - clear dropzone and refresh
    console.log('All uploads complete');
    fileDropzone.removeAllFiles(true);
    loadFiles(); // Refresh file list
    document.dispatchEvent(new CustomEvent('files-uploaded'));

    // Reset button
    if (uploadBtn) {
        uploadBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            Upload Files (<span id="queued-file-count">0</span>)
        `;
        uploadBtn.disabled = true;
    }
}

// Clear all queued files
function clearFileQueue() {
    if (!fileDropzone) return;

    fileDropzone.removeAllFiles(true);
    updateQueuedFileCount();
}

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
            autoProcessQueue: false, // Don't auto-upload - wait for confirm button

            // Update file count when files are added/removed
            init: function () {
                this.on('addedfile', updateQueuedFileCount);
                this.on('removedfile', updateQueuedFileCount);
                this.on('complete', updateQueuedFileCount);
            },

            // Get signed URL before each upload
            accept: function (file, done) {
                fetch(`/api/playgrounds/${PLAYGROUND_ID}/generate-upload-url`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filename: file.name,
                        content_type: file.type || 'application/octet-stream',
                        size: file.size
                    })
                })
                    .then(res => {
                        if (!res.ok) {
                            return res.json().then(data => {
                                throw new Error(data.message || data.error || `HTTP ${res.status}`);
                            });
                        }
                        return res.json();
                    })
                    .then(data => {
                        if (data.error) {
                            throw new Error(data.message || data.error);
                        }
                        if (!data.upload_url) {
                            throw new Error('No upload URL received from server');
                        }
                        file.uploadUrl = data.upload_url;
                        file.gcsUri = data.gcs_uri;
                        file.fileId = data.file_id;
                        done();
                    })
                    .catch(err => {
                        console.error('Upload URL generation failed:', err);
                        done(err.message || 'Failed to upload file, please try again later.');
                    });
            },

            // Use the signed URL for this specific file
            processing: function (file) {
                this.options.url = file.uploadUrl;
            },

            // Send raw file body (not form data) for GCS signed URLs
            sending: function (file, xhr, formData) {
                // Override to send raw file
                const _send = xhr.send;
                xhr.send = function () {
                    _send.call(xhr, file);
                };
                xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
            },

            // Register file in Firestore after successful GCS upload
            success: function (file, response) {
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

            error: function (file, errorMessage) {
                console.error('Upload error:', errorMessage);
            }
        });

        // Helper to check if all files are fully processed (uploaded AND registered)
        function checkAllComplete() {
            if (fileDropzone.getUploadingFiles().length === 0 &&
                fileDropzone.getQueuedFiles().length === 0 &&
                activeRegistrations === 0) {

                console.log('All uploads and registrations complete. Refreshing graph...');

                // Reset the upload button
                const uploadBtn = document.getElementById('upload-files-confirm-btn');
                if (uploadBtn) {
                    uploadBtn.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="17 8 12 3 7 8"></polyline>
                            <line x1="12" y1="3" x2="12" y2="15"></line>
                        </svg>
                        Upload Files (<span id="queued-file-count">0</span>)
                    `;
                    uploadBtn.disabled = true;
                }

                // Clear completed files from dropzone
                fileDropzone.removeAllFiles(true);

                // Dispatch event to refresh graph
                document.dispatchEvent(new CustomEvent('files-uploaded'));
            }
        }
    }
});
