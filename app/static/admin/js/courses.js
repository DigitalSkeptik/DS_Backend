class CoursesManager {
    constructor() {
        this.coursesList = document.getElementById('courses-list');
        this.addCourseBtn = document.getElementById('add-course-btn');
        this.courseModal = document.getElementById('course-modal');
        this.courseForm = document.getElementById('course-form');
        this.courseModalTitle = document.getElementById('course-modal-title');
        this.courseTagsSelect = document.getElementById('course-tags');
        
        this.currentCourseId = null;
        this.courses = [];
        this.tags = [];
        
        this.init();
    }

    init() {
        // Setup event listeners
        this.addCourseBtn.addEventListener('click', () => this.showCourseModal());
        this.courseForm.addEventListener('submit', (e) => this.handleCourseSubmit(e));
        
        // Setup modal close buttons
        this.courseModal.querySelector('.close-btn').addEventListener('click', () => this.hideCourseModal());
        this.courseModal.querySelector('.cancel-btn').addEventListener('click', () => this.hideCourseModal());
        
        // Close modal when clicking outside
        this.courseModal.addEventListener('click', (e) => {
            if (e.target === this.courseModal) {
                this.hideCourseModal();
            }
        });
        
        // Load courses when tab is shown
        document.addEventListener('tabshown', (e) => {
            if (e.detail.tab === 'courses') {
                this.loadCourses();
                this.loadTags();
            }
        });
    }

    async loadCourses() {
        try {
            this.coursesList.innerHTML = '<div class="loading">Loading courses...</div>';
            
            this.courses = await window.api.getCourses();
            
            if (this.courses.length === 0) {
                this.coursesList.innerHTML = '<div class="placeholder">No courses found</div>';
                return;
            }
            
            this.renderCourses();
        } catch (error) {
            this.coursesList.innerHTML = '<div class="placeholder">Failed to load courses</div>';
            window.app.showError('Failed to load courses: ' + error.message);
        }
    }

    async loadTags() {
        try {
            this.tags = await window.api.getTags();
            this.renderTagsSelect();
        } catch (error) {
            console.error('Failed to load tags:', error);
        }
    }

    renderTagsSelect() {
        this.courseTagsSelect.innerHTML = '';
        
        this.tags.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag.unique_id;
            option.textContent = tag.content;
            this.courseTagsSelect.appendChild(option);
        });
    }

    renderCourses() {
        this.coursesList.innerHTML = '';
        
        this.courses.forEach(course => {
            const courseCard = document.createElement('div');
            courseCard.className = 'data-card';
            
            const tagsHtml = course.tags.map(tag => 
                `<span class="tag">${tag.content}</span>`
            ).join(' ');
            
            courseCard.innerHTML = `
                <div class="data-card-header">
                    <div>
                        <div class="data-card-title">${this.escapeHtml(course.title)}</div>
                        <div class="data-card-meta">
                            <span>Price: $${course.price}</span>
                            <span>Modules: ${course.modules_count || 0}</span>
                            <span class="${course.is_active ? 'text-success' : 'text-danger'}">
                                ${course.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                        ${course.description ? `<p class="text-muted mt-2">${this.escapeHtml(course.description)}</p>` : ''}
                        ${tagsHtml ? `<div class="mt-2">${tagsHtml}</div>` : ''}
                    </div>
                    <div class="data-card-actions">
                        <button class="btn btn-sm btn-secondary" onclick="courses.viewModules('${course.unique_id}')">
                            View Modules
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="courses.editCourse('${course.unique_id}')">
                            Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="courses.deleteCourse('${course.unique_id}')">
                            Delete
                        </button>
                    </div>
                </div>
            `;
            
            this.coursesList.appendChild(courseCard);
        });
    }

    viewModules(courseId) {
        // Switch to modules tab and set the course selector
        const modulesTab = document.getElementById('modules-tab');
        const courseSelector = document.getElementById('course-selector');
        
        // Switch to modules tab
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector('[data-tab="modules"]').classList.add('active');
        
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        modulesTab.classList.add('active');
        
        // Set course selector and trigger change
        courseSelector.value = courseId;
        courseSelector.dispatchEvent(new Event('change'));
        
        // Trigger tab shown event
        document.dispatchEvent(new CustomEvent('tabshown', { detail: { tab: 'modules' } }));
    }

    showCourseModal(courseId = null) {
        this.currentCourseId = courseId;
        
        if (courseId) {
            this.courseModalTitle.textContent = 'Edit Course';
            this.loadCourseData(courseId);
        } else {
            this.courseModalTitle.textContent = 'Add Course';
            this.courseForm.reset();
            // Set default values
            document.getElementById('course-is-active').checked = true;
        }
        
        this.courseModal.classList.add('active');
    }

    hideCourseModal() {
        this.courseModal.classList.remove('active');
        this.courseForm.reset();
        this.currentCourseId = null;
    }

    async loadCourseData(courseId) {
        try {
            const course = await window.api.getCourse(courseId);
            
            document.getElementById('course-title').value = course.title;
            document.getElementById('course-description').value = course.description || '';
            document.getElementById('course-price').value = course.price;
            document.getElementById('course-img-id').value = course.img_id || '';
            document.getElementById('course-is-active').checked = course.is_active;
            
            // Set selected tags
            Array.from(this.courseTagsSelect.options).forEach(option => {
                option.selected = course.tags.some(tag => tag.unique_id === option.value);
            });
            
        } catch (error) {
            window.app.showError('Failed to load course data: ' + error.message);
            this.hideCourseModal();
        }
    }

    async handleCourseSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.courseForm);
        const courseData = {
            title: formData.get('title'),
            description: formData.get('description') || null,
            price: parseFloat(formData.get('price')),
            img_id: formData.get('img_id') || null,
            is_active: formData.has('is_active'),
            tag_ids: Array.from(this.courseTagsSelect.selectedOptions).map(option => option.value),
        };
        
        try {
            const submitBtn = this.courseForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Saving...';
            submitBtn.disabled = true;
            
            if (this.currentCourseId) {
                await window.api.updateCourse(this.currentCourseId, courseData);
                window.app.showSuccess('Course updated successfully');
            } else {
                await window.api.createCourse(courseData);
                window.app.showSuccess('Course created successfully');
            }
            
            this.hideCourseModal();
            this.loadCourses();
            
        } catch (error) {
            window.app.showError('Failed to save course: ' + error.message);
        } finally {
            const submitBtn = this.courseForm.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    editCourse(courseId) {
        this.showCourseModal(courseId);
    }

    async deleteCourse(courseId) {
        const course = this.courses.find(c => c.unique_id === courseId);
        if (!course) return;
        
        if (!confirm(`Are you sure you want to delete "${course.title}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            await window.api.deleteCourse(courseId);
            window.app.showSuccess('Course deleted successfully');
            this.loadCourses();
        } catch (error) {
            window.app.showError('Failed to delete course: ' + error.message);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create global courses manager instance
window.courses = new CoursesManager();