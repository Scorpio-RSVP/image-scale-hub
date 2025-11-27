// Main JavaScript file for Scorpio Image Resizer

// Global variables
window.ScorpioApp = {
    user: null,
    settings: {},
    loaded: false
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Load app settings
    loadSettings();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // Mark app as loaded
    ScorpioApp.loaded = true;
    
    console.log('Scorpio Image Resizer initialized');
}

// Load application settings
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const result = await response.json();
        
        if (result.success) {
            ScorpioApp.settings = result.settings;
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            showTooltip(e.target, e.target.dataset.tooltip);
        });
        
        element.addEventListener('mouseleave', function() {
            hideTooltip();
        });
    });
}

function showTooltip(element, text) {
    // Remove existing tooltip
    hideTooltip();
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    
    document.body.appendChild(tooltip);
    
    // Position tooltip
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
    
    // Show with animation
    setTimeout(() => tooltip.classList.add('show'), 10);
}

function hideTooltip() {
    const existingTooltip = document.querySelector('.tooltip');
    if (existingTooltip) {
        existingTooltip.remove();
    }
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            showFieldError(input, 'This field is required');
            isValid = false;
        } else {
            clearFieldError(input);
        }
    });
    
    // Email validation
    const emailInputs = form.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        if (input.value && !isValidEmail(input.value)) {
            showFieldError(input, 'Please enter a valid email address');
            isValid = false;
        }
    });
    
    // Password validation
    const passwordInputs = form.querySelectorAll('input[data-validate-password]');
    passwordInputs.forEach(input => {
        if (input.value && !isStrongPassword(input.value)) {
            showFieldError(input, 'Password is too weak');
            isValid = false;
        }
    });
    
    return isValid;
}

function showFieldError(field, message) {
    clearFieldError(field);
    
    field.classList.add('error');
    
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    
    field.parentNode.appendChild(errorElement);
}

function clearFieldError(field) {
    field.classList.remove('error');
    
    const errorElement = field.parentNode.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isStrongPassword(password) {
    // At least 8 characters, contains uppercase, lowercase, and number
    return password.length >= 8 && 
           /[a-z]/.test(password) && 
           /[A-Z]/.test(password) && 
           /\d/.test(password);
}

// Keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for quick search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            openQuickSearch();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            closeAllModals();
        }
        
        // Ctrl/Cmd + / for keyboard shortcuts help
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            showKeyboardShortcuts();
        }
    });
}

function openQuickSearch() {
    // Implementation for quick search
    console.log('Quick search opened');
}

function closeAllModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

function showKeyboardShortcuts() {
    // Implementation for keyboard shortcuts help
    console.log('Keyboard shortcuts help');
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// API helpers
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, mergedOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Image processing helpers
function validateImageFile(file) {
    // Check file type
    if (!file.type.startsWith('image/')) {
        throw new Error('File must be an image');
    }
    
    // Check file size (default 10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        throw new Error('File size must be less than 10MB');
    }
    
    return true;
}

function createImagePreview(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                resolve({
                    src: e.target.result,
                    width: img.width,
                    height: img.height,
                    size: file.size,
                    name: file.name
                });
            };
            img.onerror = reject;
            img.src = e.target.result;
        };
        
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// Download helpers
function downloadFile(data, filename, mimeType) {
    const blob = new Blob([data], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function downloadImageAsBase64(base64Data, filename) {
    // Convert base64 to binary
    const byteCharacters = atob(base64Data.split(',')[1]);
    const byteNumbers = new Array(byteCharacters.length);
    
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'image/png' });
    
    downloadFile(blob, filename, 'image/png');
}

// Local storage helpers
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
        return false;
    }
}

function loadFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    } catch (error) {
        console.error('Failed to load from localStorage:', error);
        return null;
    }
}

function removeFromLocalStorage(key) {
    try {
        localStorage.removeItem(key);
        return true;
    } catch (error) {
        console.error('Failed to remove from localStorage:', error);
        return false;
    }
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add to container or create one
    let container = document.querySelector('.notification-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    // Auto-remove
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, duration);
    }
    
    return notification;
}

// Copy to clipboard
async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            textArea.remove();
        }
        
        showNotification('Copied to clipboard!', 'success', 2000);
        return true;
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        showNotification('Failed to copy to clipboard', 'error', 3000);
        return false;
    }
}

// Theme switcher
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    body.setAttribute('data-theme', newTheme);
    saveToLocalStorage('theme', newTheme);
    
    // Update theme toggle button
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = newTheme === 'dark' ? 
            '<i class="fas fa-sun"></i>' : 
            '<i class="fas fa-moon"></i>';
    }
}

function loadTheme() {
    const savedTheme = loadFromLocalStorage('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    
    document.body.setAttribute('data-theme', theme);
}

// Initialize theme on load
loadTheme();

// Export functions for global use
window.ScorpioApp.utils = {
    formatFileSize,
    formatDateTime,
    debounce,
    throttle,
    apiRequest,
    validateImageFile,
    createImagePreview,
    downloadFile,
    downloadImageAsBase64,
    saveToLocalStorage,
    loadFromLocalStorage,
    removeFromLocalStorage,
    showNotification,
    copyToClipboard,
    toggleTheme,
    loadTheme
};

// Add CSS for tooltips and notifications
const style = document.createElement('style');
style.textContent = `
    .tooltip {
        position: absolute;
        background: #333;
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 14px;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
        white-space: nowrap;
    }
    
    .tooltip.show {
        opacity: 1;
    }
    
    .field-error {
        color: #dc3545;
        font-size: 14px;
        margin-top: 5px;
    }
    
    .input.error {
        border-color: #dc3545 !important;
    }
    
    .notification-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
    }
    
    .notification {
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        animation: slideIn 0.3s ease;
    }
    
    .notification-success {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .notification-error {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .notification-warning {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    
    .notification-info {
        background: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }
    
    .notification-close {
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        opacity: 0.7;
        padding: 0;
        margin-left: 10px;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);
