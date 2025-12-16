class UsersManager {
    constructor() {
        this.usersList = document.getElementById('users-list');
        this.roleFilter = document.getElementById('role-filter');
        this.userRoleModal = document.getElementById('user-role-modal');
        this.userRoleForm = document.getElementById('user-role-form');
        this.userEmailDisplay = document.getElementById('user-email-display');
        
        this.currentUserId = null;
        this.users = [];
        
        this.init();
    }

    init() {
        // Setup event listeners
        this.roleFilter.addEventListener('change', () => this.loadUsers());
        this.userRoleForm.addEventListener('submit', (e) => this.handleRoleSubmit(e));
        
        // Setup modal close buttons
        this.userRoleModal.querySelector('.close-btn').addEventListener('click', () => this.hideUserRoleModal());
        this.userRoleModal.querySelector('.cancel-btn').addEventListener('click', () => this.hideUserRoleModal());
        
        // Close modal when clicking outside
        this.userRoleModal.addEventListener('click', (e) => {
            if (e.target === this.userRoleModal) {
                this.hideUserRoleModal();
            }
        });
        
        // Load users when tab is shown
        document.addEventListener('tabshown', (e) => {
            if (e.detail.tab === 'users') {
                this.loadUsers();
            }
        });
    }

    async loadUsers() {
        try {
            this.usersList.innerHTML = '<div class="loading">Loading users...</div>';
            
            const role = this.roleFilter.value || null;
            this.users = await window.api.getUsers(0, 100, role);
            
            if (this.users.length === 0) {
                this.usersList.innerHTML = '<div class="placeholder">No users found</div>';
                return;
            }
            
            this.renderUsers();
        } catch (error) {
            this.usersList.innerHTML = '<div class="placeholder">Failed to load users</div>';
            window.app.showError('Failed to load users: ' + error.message);
        }
    }

    renderUsers() {
        this.usersList.innerHTML = '';
        
        this.users.forEach(user => {
            const userCard = document.createElement('div');
            userCard.className = 'data-card';
            
            userCard.innerHTML = `
                <div class="data-card-header">
                    <div>
                        <div class="data-card-title">${this.escapeHtml(user.username)}</div>
                        <div class="data-card-meta">
                            <span>${this.escapeHtml(user.email)}</span>
                            <span class="${user.role === 'admin' ? 'text-success' : 'text-muted'}">
                                ${user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                            </span>
                            <span>Joined: ${new Date(user.create_time).toLocaleDateString()}</span>
                        </div>
                    </div>
                    <div class="data-card-actions">
                        <button class="btn btn-sm btn-secondary" onclick="users.editUserRole('${user.unique_id}')">
                            Change Role
                        </button>
                    </div>
                </div>
            `;
            
            this.usersList.appendChild(userCard);
        });
    }

    showUserRoleModal(userId) {
        this.currentUserId = userId;
        
        const user = this.users.find(u => u.unique_id === userId);
        if (!user) return;
        
        this.userEmailDisplay.value = user.email;
        document.getElementById('user-role').value = user.role;
        
        this.userRoleModal.classList.add('active');
    }

    hideUserRoleModal() {
        this.userRoleModal.classList.remove('active');
        this.userRoleForm.reset();
        this.currentUserId = null;
    }

    async handleRoleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.userRoleForm);
        const newRole = formData.get('role');
        
        try {
            const submitBtn = this.userRoleForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Updating...';
            submitBtn.disabled = true;
            
            await window.api.updateUserRole(this.currentUserId, newRole);
            
            window.app.showSuccess('User role updated successfully');
            this.hideUserRoleModal();
            this.loadUsers();
            
        } catch (error) {
            window.app.showError('Failed to update user role: ' + error.message);
        } finally {
            const submitBtn = this.userRoleForm.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    editUserRole(userId) {
        this.showUserRoleModal(userId);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create global users manager instance
window.users = new UsersManager();