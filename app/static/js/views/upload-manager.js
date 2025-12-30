/**
 * Upload Manager
 * Handles file uploads using Dropzone.js
 */

// Disable Dropzone auto-discover
Dropzone.autoDiscover = false;

let fileDropzone = null;

// Open/close upload modal
function openUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) {
        modal.style.display = 'flex';
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

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Upload button handler
    const uploadBtn = document.getElementById('upload-files-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', openUploadModal);
    }
    
    // Initialize Dropzone with signed URL pattern
    const dropzoneElement = document.getElementById('file-dropzone');
    if (dropzoneElement) {
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
                    done('Failed to get upload URL');
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
                .then(() => {
                    console.log('File registered:', file.name);
                })
                .catch(err => {
                    console.error('Failed to register file:', err);
                });
            },
            
            error: function(file, message) {
                console.error('Upload error:', file.name, message);
            },
            
            queuecomplete: function() {
                if (typeof UIHelpers !== 'undefined') {
                    UIHelpers.showSuccess('Upload complete!');
                } else {
                    alert('Upload complete!');
                }
            }
        });
    }
});
