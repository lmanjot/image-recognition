// Vertex AI Image Recognition Tester - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initializeApp();
});

function initializeApp() {
    // Set up event listeners
    setupEventListeners();
    
    // Initialize range slider displays
    updateRangeDisplays();
}

function setupEventListeners() {
    // Form submission
    const uploadForm = document.getElementById('uploadForm');
    uploadForm.addEventListener('submit', handleFormSubmit);
    
    // Range slider updates
    const confidenceSlider = document.getElementById('confidenceThreshold');
    const iouSlider = document.getElementById('iouThreshold');
    
    confidenceSlider.addEventListener('input', function() {
        document.getElementById('confidenceValue').textContent = parseFloat(this.value).toFixed(2);
    });
    
    iouSlider.addEventListener('input', function() {
        document.getElementById('iouValue').textContent = parseFloat(this.value).toFixed(2);
    });
    
    // Image preview
    const imageInput = document.getElementById('imageInput');
    imageInput.addEventListener('change', handleImagePreview);
}

function updateRangeDisplays() {
    // Update initial values
    const confidenceSlider = document.getElementById('confidenceThreshold');
    const iouSlider = document.getElementById('iouThreshold');
    
    document.getElementById('confidenceValue').textContent = parseFloat(confidenceSlider.value).toFixed(2);
    document.getElementById('iouValue').textContent = parseFloat(iouSlider.value).toFixed(2);
}

function handleImagePreview(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            displayImage(e.target.result);
        };
        reader.readAsDataURL(file);
    }
}

function displayImage(imageData) {
    const container = document.getElementById('imageContainer');
    container.innerHTML = `<img src="${imageData}" alt="Uploaded image" class="img-fluid">`;
}

function handleFormSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const imageFile = document.getElementById('imageInput').files[0];
    
    if (!imageFile) {
        showError('Please select an image file.');
        return;
    }
    
    // Show loading state
    showLoading(true);
    
    // Record start time for processing time calculation
    const startTime = Date.now();
    
    // Submit form data
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        
        if (data.success) {
            // Calculate processing time
            const processingTime = ((Date.now() - startTime) / 1000).toFixed(2);
            
            // Display results
            displayResults(data, processingTime);
        } else {
            showError(data.error || 'An error occurred during processing.');
        }
    })
    .catch(error => {
        showLoading(false);
        console.error('Error:', error);
        showError('Network error occurred. Please try again.');
    });
}

function displayResults(data, processingTime) {
    // Display annotated image
    const container = document.getElementById('imageContainer');
    container.innerHTML = `<img src="${data.annotated_image}" alt="Annotated image with detections" class="img-fluid">`;
    
    // Update results summary
    document.getElementById('totalPredictions').textContent = data.total_predictions;
    document.getElementById('processingTime').textContent = processingTime + 's';
    
    // Display class counts
    displayClassCounts(data.class_counts);
    
    // Show results card
    document.getElementById('resultsCard').style.display = 'block';
    
    // Scroll to results
    document.getElementById('resultsCard').scrollIntoView({ 
        behavior: 'smooth', 
        block: 'nearest' 
    });
}

function displayClassCounts(classCounts) {
    const container = document.getElementById('classCounts');
    container.innerHTML = '';
    
    if (Object.keys(classCounts).length === 0) {
        container.innerHTML = '<p class="text-muted">No objects detected</p>';
        return;
    }
    
    // Sort by count (descending)
    const sortedClasses = Object.entries(classCounts)
        .sort(([,a], [,b]) => b - a);
    
    sortedClasses.forEach(([className, count]) => {
        const classItem = document.createElement('div');
        classItem.className = 'class-count-item';
        classItem.innerHTML = `
            <span class="class-name">${className}</span>
            <span class="class-count">${count}</span>
        `;
        container.appendChild(classItem);
    });
}

function showLoading(show) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const submitBtn = document.getElementById('submitBtn');
    
    if (show) {
        loadingIndicator.style.display = 'block';
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    } else {
        loadingIndicator.style.display = 'none';
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-play"></i> Run Detection';
    }
}

function showError(message) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    document.getElementById('errorMessage').textContent = message;
    errorModal.show();
}

// Utility function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Add drag and drop functionality for images
function setupDragAndDrop() {
    const dropZone = document.getElementById('imageContainer');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight(e) {
        dropZone.classList.add('drag-over');
    }
    
    function unhighlight(e) {
        dropZone.classList.remove('drag-over');
    }
    
    dropZone.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('image/')) {
                // Update file input
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                document.getElementById('imageInput').files = dataTransfer.files;
                
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                document.getElementById('imageInput').dispatchEvent(event);
            } else {
                showError('Please select an image file.');
            }
        }
    }
}

// Initialize drag and drop when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupDragAndDrop();
});