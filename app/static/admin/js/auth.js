class AuthManager {
    constructor() {
        this.loginForm = document.getElementById('login-form');
        this.loginError = document.getElementById('login-error');
        this.loginScreen = document.getElementById('login-screen');
        this.adminPanel = document.getElementById('admin-panel');
        this.logoutBtn = document.getElementById('logout-btn');
        this.userEmail = document.getElementById('user-email');
        
        this.init();
    }

    init() {
        // Check if user is already logged in
        if (window.api.accessToken) {
            this.showAdminPanel();
        }

        // Setup event listeners
        this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        this.logoutBtn.addEventListener('click', () => this.handleLogout());
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const formData = new FormData(this.loginForm);
        const email = formData.get('email');
        const password = formData.get('password');
        
        // Clear previous errors
        this.loginError.textContent = '';
        
        try {
            // Show loading state
            const submitBtn = this.loginForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Logging in...';
            submitBtn.disabled = true;
            
            await window.api.login(email, password);
            
            // Show admin panel
            this.showAdminPanel();
            
            // Reset form
            this.loginForm.reset();
            
        } catch (error) {
            this.loginError.textContent = error.message || 'Login failed';
        } finally {
            // Reset button state
            const submitBtn = this.loginForm.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    handleLogout() {
        window.api.clearTokens();
        this.showLoginScreen();
    }

    showLoginScreen() {
        this.loginScreen.classList.remove('hidden');
        this.adminPanel.classList.add('hidden');
    }

    showAdminPanel() {
        this.loginScreen.classList.add('hidden');
        this.adminPanel.classList.remove('hidden');
        
        // Extract email from JWT token (simple parsing)
        if (window.api.accessToken) {
            try {
                const payload = JSON.parse(atob(window.api.accessToken.split('.')[1]));
                this.userEmail.textContent = payload.email || 'Admin';
            } catch (error) {
                console.error('Failed to parse token:', error);
                this.userEmail.textContent = 'Admin';
            }
        }
    }

    isAuthenticated() {
        return !!window.api.accessToken;
    }
}

// Create global auth manager instance
window.auth = new AuthManager();