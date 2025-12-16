class AdminApp {
    constructor() {
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.errorToast = document.getElementById('error-toast');
        this.successToast = document.getElementById('success-toast');
        this.errorMessage = document.getElementById('error-message');
        this.successMessage = document.getElementById('success-message');
        
        this.init();
    }

    init() {
        // Setup tab navigation
        this.setupTabNavigation();
        
        // Setup toast notifications
        this.setupToastNotifications();
        
        // Check authentication on load
        if (!window.auth.isAuthenticated()) {
            // Show login screen (already visible by default)
            return;
        }
        
        // Show first tab by default
        this.showTab('courses');
    }

    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                this.showTab(tabName);
            });
        });
    }

    showTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update tab panes
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Trigger tab shown event
        document.dispatchEvent(new CustomEvent('tabshown', { detail: { tab: tabName } }));
    }

    setupToastNotifications() {
        // Setup error toast
        const errorCloseBtn = this.errorToast.querySelector('.toast-close');
        errorCloseBtn.addEventListener('click', () => {
            this.hideErrorToast();
        });
        
        // Setup success toast
        const successCloseBtn = this.successToast.querySelector('.toast-close');
        successCloseBtn.addEventListener('click', () => {
            this.hideSuccessToast();
        });
        
        // Auto-hide after 5 seconds
        this.errorToast.addEventListener('mouseenter', () => {
            clearTimeout(this.errorToast.hideTimeout);
        });
        
        this.errorToast.addEventListener('mouseleave', () => {
            this.errorToast.hideTimeout = setTimeout(() => {
                this.hideErrorToast();
            }, 2000);
        });
        
        this.successToast.addEventListener('mouseenter', () => {
            clearTimeout(this.successToast.hideTimeout);
        });
        
        this.successToast.addEventListener('mouseleave', () => {
            this.successToast.hideTimeout = setTimeout(() => {
                this.hideSuccessToast();
            }, 2000);
        });
    }

    showLoading() {
        this.loadingOverlay.classList.remove('hidden');
    }

    hideLoading() {
        this.loadingOverlay.classList.add('hidden');
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorToast.classList.remove('hidden');
        
        // Auto-hide after 5 seconds
        clearTimeout(this.errorToast.hideTimeout);
        this.errorToast.hideTimeout = setTimeout(() => {
            this.hideErrorToast();
        }, 5000);
    }

    hideErrorToast() {
        this.errorToast.classList.add('hidden');
        clearTimeout(this.errorToast.hideTimeout);
    }

    showSuccess(message) {
        this.successMessage.textContent = message;
        this.successToast.classList.remove('hidden');
        
        // Auto-hide after 3 seconds
        clearTimeout(this.successToast.hideTimeout);
        this.successToast.hideTimeout = setTimeout(() => {
            this.hideSuccessToast();
        }, 3000);
    }

    hideSuccessToast() {
        this.successToast.classList.add('hidden');
        clearTimeout(this.successToast.hideTimeout);
    }

    // Utility method to format dates
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    // Utility method to format currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    // Utility method to escape HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Utility method to validate JSON
    isValidJson(jsonString) {
        try {
            JSON.parse(jsonString);
            return true;
        } catch (e) {
            return false;
        }
    }

    // Utility method to format JSON for display
    formatJson(jsonString) {
        try {
            const parsed = JSON.parse(jsonString);
            return JSON.stringify(parsed, null, 2);
        } catch (e) {
            return jsonString;
        }
    }

    // Method to handle API errors globally
    handleApiError(error, context = '') {
        console.error(`API Error ${context}:`, error);
        
        if (error.message.includes('401') || error.message.includes('unauthorized')) {
            this.showError('Your session has expired. Please log in again.');
            window.auth.handleLogout();
        } else if (error.message.includes('403') || error.message.includes('forbidden')) {
            this.showError('You do not have permission to perform this action.');
        } else if (error.message.includes('404') || error.message.includes('not found')) {
            this.showError('The requested resource was not found.');
        } else if (error.message.includes('422') || error.message.includes('validation')) {
            this.showError('Invalid data provided. Please check your input.');
        } else if (error.message.includes('500') || error.message.includes('server')) {
            this.showError('Server error. Please try again later.');
        } else {
            this.showError(error.message || 'An unexpected error occurred.');
        }
    }

    // Method to confirm destructive actions
    confirmAction(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }

    // Method to debounce function calls
    debounce(func, wait) {
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

    // Method to throttle function calls
    throttle(func, limit) {
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
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AdminApp();
    
    // Add some global utility functions
    window.confirmAction = (message, callback) => {
        window.app.confirmAction(message, callback);
    };
    
    window.escapeHtml = (text) => {
        return window.app.escapeHtml(text);
    };
    
    window.formatDate = (dateString) => {
        return window.app.formatDate(dateString);
    };
    
    window.formatCurrency = (amount) => {
        return window.app.formatCurrency(amount);
    };
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape key closes modals
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                modal.classList.remove('active');
            });
        }
        
        // Ctrl+L focuses on search/filter inputs
        if (e.ctrlKey && e.key === 'l') {
            e.preventDefault();
            const activeTab = document.querySelector('.tab-pane.active');
            if (activeTab) {
                const filterInput = activeTab.querySelector('select, input[type="search"]');
                if (filterInput) {
                    filterInput.focus();
                }
            }
        }
    });
    
    // Add form validation helpers
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                
                // Re-enable after a short delay in case of validation errors
                setTimeout(() => {
                    if (submitBtn.disabled) {
                        submitBtn.disabled = false;
                    }
                }, 1000);
            }
        });
    });
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminApp;
}