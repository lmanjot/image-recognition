// Trichoscope Camera JavaScript

class TrichoscopeCamera {
    constructor() {
        this.videoElement = document.getElementById('videoElement');
        this.canvas = null;
        this.stream = null;
        this.currentSnapshot = null;
        this.cameraSettings = {
            deviceId: null,
            resolution: '1280x720',
            quality: 0.8
        };
        
        this.initializeCamera();
        this.setupEventListeners();
        this.loadCameraDevices();
    }

    async initializeCamera() {
        try {
            // Request camera access
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment' // Use back camera if available
                }
            });
            
            this.videoElement.srcObject = this.stream;
            this.updateStatus('Camera On', 'recording');
            this.hideNoCameraMessage();
            
            // Create hidden canvas for snapshots
            this.canvas = document.createElement('canvas');
            this.canvas.width = 1280;
            this.canvas.height = 720;
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            this.showNoCameraMessage();
            this.updateStatus('Camera Error', '');
        }
    }

    async loadCameraDevices() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            
            const cameraSelect = document.getElementById('cameraSelect');
            cameraSelect.innerHTML = '<option value="">Select Camera...</option>';
            
            videoDevices.forEach((device, index) => {
                const option = document.createElement('option');
                option.value = device.deviceId;
                option.textContent = device.label || `Camera ${index + 1}`;
                cameraSelect.appendChild(option);
            });
            
            // Auto-select first camera if only one available
            if (videoDevices.length === 1) {
                cameraSelect.value = videoDevices[0].deviceId;
                this.cameraSettings.deviceId = videoDevices[0].deviceId;
            }
            
        } catch (error) {
            console.error('Error loading camera devices:', error);
        }
    }

    setupEventListeners() {
        // Capture button
        document.getElementById('captureBtn').addEventListener('click', () => {
            this.captureSnapshot();
        });

        // Settings button
        document.getElementById('settingsBtn').addEventListener('click', () => {
            this.toggleSettings();
        });

        // Apply settings button
        document.getElementById('applySettingsBtn').addEventListener('click', () => {
            this.applyCameraSettings();
        });

        // Camera selection
        document.getElementById('cameraSelect').addEventListener('change', (e) => {
            this.cameraSettings.deviceId = e.target.value;
        });

        // Resolution selection
        document.getElementById('resolutionSelect').addEventListener('change', (e) => {
            this.cameraSettings.resolution = e.target.value;
        });

        // Quality slider
        document.getElementById('qualitySlider').addEventListener('input', (e) => {
            document.getElementById('qualityValue').textContent = e.target.value;
            this.cameraSettings.quality = parseFloat(e.target.value);
        });

        // Save snapshot button
        document.getElementById('saveSnapshotBtn').addEventListener('click', () => {
            this.saveSnapshot();
        });

        // Retry camera button
        document.getElementById('retryCameraBtn').addEventListener('click', () => {
            this.retryCameraAccess();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !e.target.matches('input, textarea')) {
                e.preventDefault();
                this.captureSnapshot();
            }
        });
    }

    async applyCameraSettings() {
        if (!this.cameraSettings.deviceId) {
            this.showError('Please select a camera device');
            return;
        }

        try {
            // Stop current stream
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }

            // Parse resolution
            const [width, height] = this.cameraSettings.resolution.split('x').map(Number);

            // Start new stream with selected settings
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    deviceId: { exact: this.cameraSettings.deviceId },
                    width: { ideal: width },
                    height: { ideal: height }
                }
            });

            this.videoElement.srcObject = this.stream;
            
            // Update canvas size
            this.canvas.width = width;
            this.canvas.height = height;
            
            this.updateStatus('Camera On', 'recording');
            this.showSuccess('Camera settings applied successfully');
            
        } catch (error) {
            console.error('Error applying camera settings:', error);
            this.showError('Failed to apply camera settings: ' + error.message);
        }
    }

    captureSnapshot() {
        if (!this.stream || !this.canvas) {
            this.showError('Camera not available');
            return;
        }

        try {
            const context = this.canvas.getContext('2d');
            
            // Draw current video frame to canvas
            context.drawImage(this.videoElement, 0, 0, this.canvas.width, this.canvas.height);
            
            // Convert to blob with quality setting
            this.canvas.toBlob((blob) => {
                this.currentSnapshot = blob;
                this.showSnapshotPreview(blob);
            }, 'image/jpeg', this.cameraSettings.quality);
            
        } catch (error) {
            console.error('Error capturing snapshot:', error);
            this.showError('Failed to capture snapshot');
        }
    }

    showSnapshotPreview(blob) {
        const url = URL.createObjectURL(blob);
        const previewImg = document.getElementById('snapshotPreview');
        previewImg.src = url;
        
        const modal = new bootstrap.Modal(document.getElementById('snapshotModal'));
        modal.show();
        
        // Clean up URL when modal is hidden
        document.getElementById('snapshotModal').addEventListener('hidden.bs.modal', () => {
            URL.revokeObjectURL(url);
        }, { once: true });
    }

    async saveSnapshot() {
        if (!this.currentSnapshot) {
            this.showError('No snapshot to save');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('image', this.currentSnapshot, 'trichoscope_snapshot.jpg');

            const response = await fetch('/snapshot', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Snapshot saved successfully!');
                this.addSnapshotToGallery(result);
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('snapshotModal'));
                modal.hide();
                
            } else {
                this.showError(result.error || 'Failed to save snapshot');
            }

        } catch (error) {
            console.error('Error saving snapshot:', error);
            this.showError('Network error while saving snapshot');
        }
    }

    addSnapshotToGallery(snapshotData) {
        const container = document.getElementById('snapshotsContainer');
        
        // Remove "no snapshots" message if present
        const noSnapshotsMsg = container.querySelector('.text-muted');
        if (noSnapshotsMsg) {
            noSnapshotsMsg.remove();
        }

        // Create snapshot item
        const snapshotItem = document.createElement('div');
        snapshotItem.className = 'snapshot-item';
        
        const timestamp = new Date().toLocaleString();
        snapshotItem.innerHTML = `
            <img src="${snapshotData.filepath}" alt="Trichoscope snapshot" loading="lazy">
            <div class="snapshot-info">
                <div><strong>${snapshotData.filename}</strong></div>
                <div>${timestamp}</div>
            </div>
        `;

        // Add click handler to view full size
        snapshotItem.addEventListener('click', () => {
            this.showSnapshotPreview(this.currentSnapshot);
        });

        // Insert at the beginning
        container.insertBefore(snapshotItem, container.firstChild);
        
        // Limit to 10 most recent snapshots
        const items = container.querySelectorAll('.snapshot-item');
        if (items.length > 10) {
            items[items.length - 1].remove();
        }
    }

    async retryCameraAccess() {
        this.hideNoCameraMessage();
        this.updateStatus('Connecting...', '');
        await this.initializeCamera();
    }

    toggleSettings() {
        const settingsCard = document.querySelector('.col-lg-4 .card:first-child');
        settingsCard.style.display = settingsCard.style.display === 'none' ? 'block' : 'none';
    }

    updateStatus(message, className) {
        const statusIndicator = document.getElementById('statusIndicator');
        statusIndicator.textContent = message;
        statusIndicator.className = `status-indicator ${className}`;
    }

    showNoCameraMessage() {
        document.getElementById('noCameraMessage').style.display = 'block';
        document.getElementById('cameraContainer').style.display = 'none';
    }

    hideNoCameraMessage() {
        document.getElementById('noCameraMessage').style.display = 'none';
        document.getElementById('cameraContainer').style.display = 'block';
    }

    showError(message) {
        const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
        document.getElementById('errorMessage').textContent = message;
        errorModal.show();
    }

    showSuccess(message) {
        // Create a temporary success toast
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-check-circle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    // Clean up when page is unloaded
    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
}

// Initialize camera when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.trichoscopeCamera = new TrichoscopeCamera();
});

// Clean up when page is unloaded
window.addEventListener('beforeunload', function() {
    if (window.trichoscopeCamera) {
        window.trichoscopeCamera.cleanup();
    }
});

// Handle page visibility changes to pause/resume camera
document.addEventListener('visibilitychange', function() {
    if (window.trichoscopeCamera) {
        if (document.hidden) {
            // Page is hidden, could pause camera here if needed
        } else {
            // Page is visible again
        }
    }
});