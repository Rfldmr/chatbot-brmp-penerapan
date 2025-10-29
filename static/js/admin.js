// Admin Dashboard JavaScript

let trainingInterval;
let trainingStartTime;
const TRAINING_TIMEOUT = 300000; // 5 minutes timeout

// Load model information
function loadModelInfo() {
    // Add loading state for all statistics cards
    const totalIntentsEl = document.getElementById('total-intents');
    const totalPatternsEl = document.getElementById('total-patterns');
    const totalUsersEl = document.getElementById('total-users');
    
    if (totalIntentsEl) totalIntentsEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    if (totalPatternsEl) totalPatternsEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    if (totalUsersEl) totalUsersEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    fetch('/api/admin/model-info')
        .then(response => response.json())
        .then(data => {
            // Update statistics cards
            if (totalIntentsEl) animateNumber(totalIntentsEl, 0, data.total_intents || 0, 1000);
            if (totalPatternsEl) animateNumber(totalPatternsEl, 0, data.total_patterns || 0, 1000);
            if (totalUsersEl) animateNumber(totalUsersEl, 0, data.total_users || 0, 1000);
            
            // Update model information section
            const accuracyEl = document.getElementById('model-accuracy');
            const lastUploadedEl = document.getElementById('dataset-last-uploaded');
            const sizeEl = document.getElementById('model-size');
            const filenameEl = document.getElementById('dataset-filename');
            
            if (accuracyEl) accuracyEl.textContent = data.accuracy || 'N/A';
            if (lastUploadedEl) lastUploadedEl.textContent = data.dataset_update || 'N/A';
            if (sizeEl) sizeEl.textContent = data.model_size || 'N/A';
            if (filenameEl) filenameEl.textContent = 'intents.json';
        })
        .catch(error => {
            console.error('Error loading model info:', error);
            
            // Show error state for all elements
            if (totalIntentsEl) totalIntentsEl.textContent = 'Error';
            if (totalPatternsEl) totalPatternsEl.textContent = 'Error';
            if (totalUsersEl) totalUsersEl.textContent = 'Error';
            
            const accuracyEl = document.getElementById('model-accuracy');
            const lastUploadedEl = document.getElementById('dataset-last-uploaded');
            const sizeEl = document.getElementById('model-size');
            const filenameEl = document.getElementById('dataset-filename');
            
            if (accuracyEl) accuracyEl.textContent = 'Error';
            if (lastUploadedEl) lastUploadedEl.textContent = 'Error';
            if (sizeEl) sizeEl.textContent = 'Error';
            if (filenameEl) filenameEl.textContent = 'Error';
        });
}

// Load initial data when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the dashboard or admin management page
    const isAdminManagementPage = window.location.pathname.includes('/admin/management');
    
    if (isAdminManagementPage) {
        // Admin Management page - only load admin-related functions
        loadCurrentUser()
            .then(() => {
                loadAdminList();
            })
            .catch(error => {
                console.error('Failed to load current user, loading admin list anyway:', error);
                loadAdminList();
            });
        
        // Set up admin form handlers only
        setupAdminFormHandlers();
    } else {
        // Dashboard page - load model info and setup upload functionality
        loadModelInfo();
        
        loadCurrentUser()
            .then(() => {
                // Only load admin list if admin-list element exists (removed from dashboard)
                if (document.getElementById('admin-list')) {
                    loadAdminList();
                }
            })
            .catch(error => {
                console.error('Failed to load current user:', error);
                if (document.getElementById('admin-list')) {
                    loadAdminList();
                }
            });
        
        // Set up form handlers
        setupFormHandlers();
        setupAdminFormHandlers();
        
        // Set up drag and drop
        setupDragAndDrop();
    }
    
    // Auto-refresh dihapus untuk mengurangi beban server dan memberikan kontrol penuh ke user
});

// Load admin list
function loadAdminList() {
    fetch('/api/admin/list')
        .then(response => response.json())
        .then(data => {
            const adminList = document.getElementById('admin-list');
            if (adminList) {
                adminList.innerHTML = '';
                if (data.length === 0) {
                    adminList.innerHTML = `
                        <tr>
                            <td colspan="5" class="px-6 py-4 text-center text-gray-500">
                                <i class="fas fa-inbox mr-2"></i>Belum ada admin
                            </td>
                        </tr>
                    `;
                } else {
                    data.forEach((admin, index) => {
                        const row = createAdminRow(admin, index + 1);
                        adminList.appendChild(row);
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error loading admin list:', error);
            const adminList = document.getElementById('admin-list');
            if (adminList) {
                adminList.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-6 py-4 text-center text-red-500">
                            <i class="fas fa-exclamation-triangle mr-2"></i>Error loading admin list
                        </td>
                    </tr>
                `;
            }
        });
}

// Create admin table row
function createAdminRow(admin, index) {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-gray-50 transition-colors';
    
    const createdDate = new Date(admin.created_at).toLocaleDateString('id-ID');
    const currentUser = getCurrentUsername();
    const isCurrentUser = currentUser && admin.username === currentUser;
    
    tr.innerHTML = `
        <td class="px-6 py-4 text-sm text-gray-900">${index}</td>
        <td class="px-6 py-4 text-sm font-medium text-gray-900">
            ${admin.username}
        </td>
        <td class="px-6 py-4 text-sm text-gray-500">${createdDate}</td>
        <td class="px-6 py-4">
            <span class="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">Aktif</span>
        </td>
        <td class="px-6 py-4 text-center">
            ${!isCurrentUser ? `
                <button onclick="deleteAdmin('${admin.username}')" 
                        class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded-lg text-sm transition-colors">
                    <i class="fas fa-trash mr-1"></i>Hapus
                </button>
            ` : `
                <span class="text-gray-400 text-sm">Akun Saat Ini</span>
            `}
        </td>
    `;
    
    return tr;
}

// Get current username (from session)
let currentUsername = localStorage.getItem('admin_username'); // Initialize from localStorage

function getCurrentUsername() {
    // Try to get from memory first, then localStorage as backup
    const username = currentUsername || localStorage.getItem('admin_username');
    return username;
}

// Load current user
function loadCurrentUser() {
    return fetch('/api/admin/current-user')
        .then(response => response.json())
        .then(data => {
            currentUsername = data.username;
            localStorage.setItem('admin_username', data.username);
            console.log('Current user loaded:', currentUsername);
            return currentUsername;
        })
        .catch(error => {
            console.error('Error loading current user:', error);
            throw error;
        });
}

// Setup admin form handlers
function setupAdminFormHandlers() {
    const addAdminForm = document.getElementById('add-admin-form');
    
    if (addAdminForm) {
        addAdminForm.addEventListener('submit', handleAddAdmin);
    }
}

// Handle add admin
function handleAddAdmin(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Menambahkan...';
    
    fetch('/api/admin/add', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert(data.message, 'success');
            e.target.reset();
            loadAdminList(); // Reload admin list
        } else {
            showAlert(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Terjadi kesalahan saat menambah admin', 'error');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    });
}

// Delete admin function
function deleteAdmin(username) {
    if (!confirm(`Apakah Anda yakin ingin menghapus admin "${username}"?`)) {
        return;
    }
    
    fetch('/api/admin/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: username })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert(data.message, 'success');
            loadAdminList(); // Reload admin list
        } else {
            showAlert(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Terjadi kesalahan saat menghapus admin', 'error');
    });
}

// Update model status display
function updateModelStatus(status) {
    const statusElement = document.getElementById('model-status');
    const iconElement = document.getElementById('model-status-icon');
    
    if (!statusElement || !iconElement) return;
    
    // Add transition class for smooth animation
    statusElement.style.transition = 'all 0.3s ease';
    iconElement.style.transition = 'all 0.3s ease';
    
    switch(status) {
        case 'ready':
            statusElement.textContent = 'Ready';
            statusElement.className = 'text-3xl font-bold text-success-600 group-hover:scale-105 transition-transform';
            iconElement.className = 'fas fa-brain text-success-600 text-xl';
            break;
        case 'training':
            statusElement.textContent = 'Training';
            statusElement.className = 'text-3xl font-bold text-secondary-600 group-hover:scale-105 transition-transform';
            iconElement.className = 'fas fa-cog fa-spin text-secondary-600 text-xl';
            break;
        case 'error':
            statusElement.textContent = 'Error';
            statusElement.className = 'text-3xl font-bold text-danger-600 group-hover:scale-105 transition-transform';
            iconElement.className = 'fas fa-exclamation-triangle text-danger-600 text-xl';
            break;
        default:
            statusElement.textContent = 'Unknown';
            statusElement.className = 'text-3xl font-bold text-gray-600 group-hover:scale-105 transition-transform';
            iconElement.className = 'fas fa-question text-gray-600 text-xl';
    }
}

// Setup form handlers
function setupFormHandlers() {
    const uploadForm = document.getElementById('upload-form');
    const previewBtn = document.getElementById('preview-btn');
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleUpload);
    }
    
    if (previewBtn) {
        previewBtn.addEventListener('click', handlePreview);
    }
}

// Setup drag and drop
function setupDragAndDrop() {
    const dropZone = document.querySelector('.border-dashed');
    const fileInput = document.getElementById('file');
    
    if (dropZone && fileInput) {
        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            dropZone.classList.add('border-primary', 'bg-blue-50');
        });
        
        dropZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            dropZone.classList.remove('border-primary', 'bg-blue-50');
        });
        
        dropZone.addEventListener('drop', function(e) {
            e.preventDefault();
            dropZone.classList.remove('border-primary', 'bg-blue-50');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                updateFileName(fileInput);
            }
        });
    }
}

// Handle file upload
function handleUpload(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('file');
    const formData = new FormData();
    
    if (fileInput.files.length === 0) {
        showAlert('Silakan pilih file terlebih dahulu!', 'error');
        return;
    }
    
    formData.append('file', fileInput.files[0]);
    
    // Show loading modal
    showLoadingModal(true);
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert(data.message, 'success');
            startTrainingMonitor();
        } else {
            showAlert(data.message, 'error');
            showLoadingModal(false);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Terjadi kesalahan saat upload file', 'error');
        showLoadingModal(false);
    });
}

// Handle file preview
function handlePreview() {
    const fileInput = document.getElementById('file');
    
    if (fileInput.files.length === 0) {
        showAlert('Silakan pilih file terlebih dahulu!', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    fetch('/api/admin/preview', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showPreviewModal(data.data);
        } else {
            showAlert(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Terjadi kesalahan saat preview file', 'error');
    });
}

// Start training monitor
function startTrainingMonitor() {
    // Clear any existing interval first
    if (trainingInterval) {
        clearInterval(trainingInterval);
        trainingInterval = null;
    }
    
    // Reset retry counter and set start time
    trainingStatusRetries = 0;
    trainingStartTime = Date.now();
    
    console.log('Starting training monitor'); // Debug log
    trainingInterval = setInterval(checkTrainingStatus, 2000);
    
    // Set a timeout as safety net
    setTimeout(() => {
        if (trainingInterval) {
            console.warn('Training timeout reached, stopping monitor');
            clearInterval(trainingInterval);
            trainingInterval = null;
            showLoadingModal(false);
            updateModelStatus('error');
            showAlert('Training timeout - proses terlalu lama', 'warning');
        }
    }, TRAINING_TIMEOUT);
}

// Check training status
let trainingStatusRetries = 0;
const MAX_RETRIES = 3;

function checkTrainingStatus() {
    // Check for timeout
    if (Date.now() - trainingStartTime > TRAINING_TIMEOUT) {
        console.warn('Training timeout reached in checkTrainingStatus');
        if (trainingInterval) {
            clearInterval(trainingInterval);
            trainingInterval = null;
        }
        showLoadingModal(false);
        updateModelStatus('error');
        showAlert('Training timeout - proses terlalu lama', 'warning');
        return;
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    fetch('/api/admin/training-status', {
        signal: controller.signal
    })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            trainingStatusRetries = 0; // Reset retry counter on success
            console.log('Training status:', data); // Debug log
            
            if (data.status === 'training') {
                updateLoadingModal(data);
                updateModelStatus('training');
            } else if (data.status === 'completed') {
                console.log('Training completed, clearing interval and closing modal'); // Debug log
                if (trainingInterval) {
                    clearInterval(trainingInterval);
                    trainingInterval = null;
                }
                // Immediately close modal without any delay
                const modal = document.getElementById('loading-modal');
                if (modal) {
                    modal.classList.add('hidden');
                    modal.classList.remove('flex');
                    // Clean up any progress bars
                    const progressContainer = modal.querySelector('.progress-container');
                    if (progressContainer) {
                        progressContainer.remove();
                    }
                }
                updateModelStatus('ready');
                loadModelInfo();
                showAlert('Model berhasil dilatih ulang!', 'success');
                return; // Stop polling immediately after completion
            } else if (data.status === 'error') {
                console.log('Training error, clearing interval and closing modal'); // Debug log
                if (trainingInterval) {
                    clearInterval(trainingInterval);
                    trainingInterval = null;
                }
                // Immediately close modal without any delay
                const modal = document.getElementById('loading-modal');
                if (modal) {
                    modal.classList.add('hidden');
                    modal.classList.remove('flex');
                    // Clean up any progress bars
                    const progressContainer = modal.querySelector('.progress-container');
                    if (progressContainer) {
                        progressContainer.remove();
                    }
                }
                updateModelStatus('error');
                showAlert(data.message || 'Terjadi kesalahan saat training model', 'error');
                return; // Stop polling immediately after error
            } else if (data.status === 'ready') {
                // Handle ready status - training completed and reset
                console.log('Training status is ready - cleaning up'); // Debug log
                if (trainingInterval) {
                    clearInterval(trainingInterval);
                    trainingInterval = null;
                    // Force close modal if still open
                    const modal = document.getElementById('loading-modal');
                    if (modal && !modal.classList.contains('hidden')) {
                        modal.classList.add('hidden');
                        modal.classList.remove('flex');
                        // Clean up any progress bars
                        const progressContainer = modal.querySelector('.progress-container');
                        if (progressContainer) {
                            progressContainer.remove();
                        }
                        console.log('Modal force closed on ready status');
                    }
                    updateModelStatus('ready');
                }
            } else {
                // Handle unknown status
                console.warn('Unknown training status:', data.status);
                updateLoadingModal(data);
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error('Error checking training status:', error);
            
            trainingStatusRetries++;
            
            if (trainingStatusRetries >= MAX_RETRIES) {
                console.log('Max retries reached, clearing interval'); // Debug log
                if (trainingInterval) {
                    clearInterval(trainingInterval);
                    trainingInterval = null;
                }
                showLoadingModal(false);
                updateModelStatus('error');
                showAlert('Gagal mengecek status training setelah beberapa percobaan', 'error');
            } else {
                // Retry silently
                console.log(`Retrying training status check (${trainingStatusRetries}/${MAX_RETRIES})`);
            }
        });
}

// Show/hide loading modal
function showLoadingModal(show, title = 'Memproses File...', message = 'Mohon tunggu, model sedang dilatih ulang') {
    const modal = document.getElementById('loading-modal');
    const titleEl = modal.querySelector('h3');
    const messageEl = modal.querySelector('p');
    
    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;
    
    if (show) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    } else {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        
        // Hapus progress bar jika ada
        const progressContainer = modal.querySelector('.progress-container');
        if (progressContainer) {
            progressContainer.remove();
        }
    }
}

// Update loading modal with progress
function updateLoadingModal(data) {
    const modal = document.getElementById('loading-modal');
    const messageEl = modal.querySelector('p');
    
    if (messageEl && data.message) {
        let progressText = `${data.message}`;
        if (data.progress !== undefined) {
            progressText += ` (${data.progress}%)`;
        }
        messageEl.textContent = progressText;
    }
    
    // Tambah progress bar jika belum ada
    let progressContainer = modal.querySelector('.progress-container');
    if (!progressContainer && data.progress !== undefined) {
        progressContainer = document.createElement('div');
        progressContainer.className = 'progress-container mt-4';
        progressContainer.innerHTML = `
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" id="progress-bar" style="width: ${data.progress}%"></div>
            </div>
            <p class="text-sm text-gray-600 mt-2 text-center">${data.progress}% Complete</p>
        `;
        modal.querySelector('.bg-white').appendChild(progressContainer);
    } else if (progressContainer && data.progress !== undefined) {
        const progressBar = progressContainer.querySelector('#progress-bar');
        const progressText = progressContainer.querySelector('p');
        if (progressBar) progressBar.style.width = `${data.progress}%`;
        if (progressText) progressText.textContent = `${data.progress}% Complete`;
    }
}

// Show preview modal
function showPreviewModal(data) {
    const modalHTML = `
        <div id="preview-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white p-8 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">Preview File Intents</h3>
                <div class="space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-blue-50 p-4 rounded-lg">
                            <p class="text-sm text-gray-600">Total Intents</p>
                            <p class="text-2xl font-bold text-blue-600">${data.total_intents}</p>
                        </div>
                        <div class="bg-green-50 p-4 rounded-lg">
                            <p class="text-sm text-gray-600">Total Patterns</p>
                            <p class="text-2xl font-bold text-green-600">${data.total_patterns}</p>
                        </div>
                    </div>
                    <div>
                        <h4 class="font-medium text-gray-700 mb-2">Sample Intents:</h4>
                        <div class="space-y-2">
                            ${data.intents.map(intent => `
                                <div class="flex justify-between items-center p-2 bg-gray-50 rounded">
                                    <span class="font-medium">${intent.tag}</span>
                                    <span class="text-sm text-gray-600">${intent.patterns_count} patterns</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                <div class="mt-6 flex justify-end">
                    <button onclick="closePreviewModal()" class="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg">
                        Tutup
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// Close preview modal
function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    if (modal) {
        modal.remove();
    }
}

// Show alert
function showAlert(message, type = 'info') {
    const alertConfigs = {
        success: {
            bg: 'bg-gradient-to-r from-success-50 to-success-100',
            border: 'border-success-400',
            text: 'text-success-800',
            icon: 'fas fa-check-circle text-success-600',
            progressBar: 'bg-success-500'
        },
        error: {
            bg: 'bg-gradient-to-r from-danger-50 to-danger-100',
            border: 'border-danger-400',
            text: 'text-danger-800',
            icon: 'fas fa-exclamation-circle text-danger-600',
            progressBar: 'bg-danger-500'
        },
        info: {
            bg: 'bg-gradient-to-r from-info-50 to-info-100',
            border: 'border-info-400',
            text: 'text-info-800',
            icon: 'fas fa-info-circle text-info-600',
            progressBar: 'bg-info-500'
        },
        warning: {
            bg: 'bg-gradient-to-r from-secondary-50 to-secondary-100',
            border: 'border-secondary-400',
            text: 'text-secondary-800',
            icon: 'fas fa-exclamation-triangle text-secondary-600',
            progressBar: 'bg-secondary-500'
        }
    };
    
    const config = alertConfigs[type] || alertConfigs.info;
    const alertId = 'alert-' + Date.now();
    
    const alertHTML = `
        <div id="${alertId}" class="fixed top-6 right-6 z-[60] max-w-sm w-full transform translate-x-full opacity-0 transition-all duration-300 ease-out">
            <div class="${config.bg} ${config.text} p-4 rounded-xl shadow-lg border-l-4 ${config.border} backdrop-blur-sm border border-white/20">
                <div class="flex items-start">
                    <div class="flex-shrink-0 mr-3">
                        <i class="${config.icon} text-lg"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="font-medium text-sm leading-5">${message}</p>
                        <div class="mt-2 w-full bg-white/30 rounded-full h-1">
                            <div class="${config.progressBar} h-1 rounded-full transition-all duration-5000 ease-linear" style="width: 0%"></div>
                        </div>
                    </div>
                    <button onclick="closeAlert('${alertId}')" class="flex-shrink-0 ml-3 text-gray-400 hover:text-gray-600 transition-colors">
                        <i class="fas fa-times text-sm"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing alerts to prevent stacking
    const existingAlerts = document.querySelectorAll('[id^="alert-"]');
    existingAlerts.forEach(alert => {
        alert.style.transform = 'translateX(100%)';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    });
    
    // Add new alert
    document.body.insertAdjacentHTML('beforeend', alertHTML);
    
    // Trigger slide-in animation
    const alertElement = document.getElementById(alertId);
    setTimeout(() => {
        alertElement.style.transform = 'translateX(0)';
        alertElement.style.opacity = '1';
        
        // Start progress bar animation
        const progressBar = alertElement.querySelector('.transition-all.duration-5000');
        setTimeout(() => {
            progressBar.style.width = '100%';
        }, 100);
    }, 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        closeAlert(alertId);
    }, 5000);
    
    return alertId;
}

// Close alert
function closeAlert(alertId = null) {
    if (alertId) {
        const alert = document.getElementById(alertId);
        if (alert) {
            alert.style.transform = 'translateX(100%)';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }
    } else {
        // Fallback for backward compatibility - close all alerts
        const alerts = document.querySelectorAll('[id^="alert-"]');
        alerts.forEach(alert => {
            alert.style.transform = 'translateX(100%)';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    }
}

// Update filename display
function updateFileName(input) {
    const label = document.getElementById('file-label');
    if (input.files.length > 0) {
        label.innerHTML = `<i class="fas fa-file-code mr-2"></i>${input.files[0].name}`;
    } else {
        label.innerHTML = 'Klik untuk memilih file atau drag & drop';
    }
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('id-ID');
}

// Animate number counting up
function animateNumber(element, start, end, duration) {
    if (!element) return;
    
    const range = end - start;
    const increment = range / (duration / 16); // 60fps
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= end) {
            element.textContent = end.toString();
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current).toString();
        }
    }, 16);
}

// Add loading skeleton
function createLoadingSkeleton() {
    return `
        <div class="animate-pulse">
            <div class="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
            <div class="h-3 bg-gray-300 rounded w-1/2"></div>
        </div>
    `;
}

// Add smooth scroll to element
function smoothScrollTo(element) {
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }
}

// Logout function
function logout() {
    if (confirm('Apakah Anda yakin ingin logout?')) {
        // Clear any stored session data
        localStorage.removeItem('admin_username');
        
        // Redirect to logout endpoint
        window.location.href = '/admin/logout';
    }
}

// Auto-refresh page every 1 minute
let autoRefreshInterval = null;

function startAutoRefresh() {
    // Clear any existing interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Set up full page refresh every 1 minute
    autoRefreshInterval = setInterval(() => {
        console.log('Auto-refreshing entire page...');
        
        // Reload the entire page
        location.reload();
    }, 60000); // 1 minute (60 seconds)
    
    console.log('Auto-refresh enabled (full page reload every 1 minute)');
    updateLastRefreshTime();
}

function updateLastRefreshTime() {
    const lastRefreshEl = document.getElementById('last-refresh-time');
    if (lastRefreshEl) {
        const now = new Date();
        const timeString = now.toLocaleTimeString('id-ID');
        lastRefreshEl.textContent = `Terakhir diperbarui: ${timeString}`;
    }
}

// Start auto-refresh when page loads
window.addEventListener('load', () => {
    startAutoRefresh();
});

// Stop auto-refresh when user leaves the page
window.addEventListener('beforeunload', () => {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

