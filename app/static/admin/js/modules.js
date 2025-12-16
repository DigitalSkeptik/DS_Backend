class ModulesManager {
    constructor() {
        this.modulesList = document.getElementById('modules-list');
        this.courseSelector = document.getElementById('course-selector');
        this.addModuleBtn = document.getElementById('add-module-btn');
        this.moduleModal = document.getElementById('module-modal');
        this.moduleForm = document.getElementById('module-form');
        this.moduleModalTitle = document.getElementById('module-modal-title');
        this.testSection = document.getElementById('test-section');
        this.testContent = document.getElementById('test-content');
        this.addTestBtn = document.getElementById('add-test-btn');
        
        this.currentCourseId = null;
        this.currentModuleId = null;
        this.modules = [];
        this.courses = [];
        this.currentTest = null;
        
        this.init();
    }

    init() {
        // Setup event listeners
        this.courseSelector.addEventListener('change', () => this.handleCourseChange());
        this.addModuleBtn.addEventListener('click', () => this.showModuleModal());
        this.moduleForm.addEventListener('submit', (e) => this.handleModuleSubmit(e));
        this.addTestBtn.addEventListener('click', () => this.showTestModal());
        
        // Setup modal close buttons
        this.moduleModal.querySelector('.close-btn').addEventListener('click', () => this.hideModuleModal());
        this.moduleModal.querySelector('.cancel-btn').addEventListener('click', () => this.hideModuleModal());
        
        // Close modal when clicking outside
        this.moduleModal.addEventListener('click', (e) => {
            if (e.target === this.moduleModal) {
                this.hideModuleModal();
            }
        });
        
        // Load courses when tab is shown
        document.addEventListener('tabshown', (e) => {
            if (e.detail.tab === 'modules') {
                this.loadCourses();
            }
        });
    }

    async loadCourses() {
        try {
            this.courses = await window.api.getCourses();
            this.renderCourseSelector();
        } catch (error) {
            console.error('Failed to load courses:', error);
            window.app.showError('Failed to load courses: ' + error.message);
        }
    }

    renderCourseSelector() {
        this.courseSelector.innerHTML = '<option value="">Select a course...</option>';
        
        this.courses.forEach(course => {
            const option = document.createElement('option');
            option.value = course.unique_id;
            option.textContent = course.title;
            this.courseSelector.appendChild(option);
        });
        
        // If a course was pre-selected, maintain that selection
        if (this.currentCourseId) {
            this.courseSelector.value = this.currentCourseId;
            this.handleCourseChange();
        }
    }

    async handleCourseChange() {
        const courseId = this.courseSelector.value;
        
        if (!courseId) {
            this.currentCourseId = null;
            this.modulesList.innerHTML = '<div class="placeholder">Select a course to view modules</div>';
            this.addModuleBtn.disabled = true;
            this.testSection.classList.add('hidden');
            return;
        }
        
        this.currentCourseId = courseId;
        this.addModuleBtn.disabled = false;
        
        await this.loadModules(courseId);
    }

    async loadModules(courseId) {
        try {
            this.modulesList.innerHTML = '<div class="loading">Loading modules...</div>';
            
            this.modules = await window.api.getModules(courseId);
            
            if (this.modules.length === 0) {
                this.modulesList.innerHTML = '<div class="placeholder">No modules found for this course</div>';
                this.testSection.classList.add('hidden');
                return;
            }
            
            this.renderModules();
        } catch (error) {
            this.modulesList.innerHTML = '<div class="placeholder">Failed to load modules</div>';
            window.app.showError('Failed to load modules: ' + error.message);
        }
    }

    renderModules() {
        this.modulesList.innerHTML = '';
        
        // Sort modules by position
        const sortedModules = [...this.modules].sort((a, b) => a.position - b.position);
        
        sortedModules.forEach(module => {
            const moduleCard = document.createElement('div');
            moduleCard.className = 'data-card';
            
            moduleCard.innerHTML = `
                <div class="data-card-header">
                    <div>
                        <div class="data-card-title">${this.escapeHtml(module.title)}</div>
                        <div class="data-card-meta">
                            <span>Position: ${module.position}</span>
                            <span class="${module.has_test ? 'text-success' : 'text-muted'}">
                                ${module.has_test ? 'Has Test' : 'No Test'}
                            </span>
                        </div>
                        ${module.description ? `<p class="text-muted mt-2">${this.escapeHtml(module.description)}</p>` : ''}
                    </div>
                    <div class="data-card-actions">
                        <button class="btn btn-sm btn-secondary" onclick="modules.manageTest('${module.unique_id}')">
                            ${module.has_test ? 'Manage Test' : 'Add Test'}
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="modules.editModule('${module.unique_id}')">
                            Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="modules.deleteModule('${module.unique_id}')">
                            Delete
                        </button>
                    </div>
                </div>
            `;
            
            this.modulesList.appendChild(moduleCard);
        });
    }

    showModuleModal(moduleId = null) {
        this.currentModuleId = moduleId;
        
        if (moduleId) {
            this.moduleModalTitle.textContent = 'Edit Module';
            this.loadModuleData(moduleId);
        } else {
            this.moduleModalTitle.textContent = 'Add Module';
            this.moduleForm.reset();
            // Set next position
            const nextPosition = this.modules.length > 0 ? Math.max(...this.modules.map(m => m.position)) + 1 : 0;
            document.getElementById('module-position').value = nextPosition;
        }
        
        this.moduleModal.classList.add('active');
    }

    hideModuleModal() {
        this.moduleModal.classList.remove('active');
        this.moduleForm.reset();
        this.currentModuleId = null;
    }

    async loadModuleData(moduleId) {
        try {
            const module = await window.api.getModule(moduleId);
            
            document.getElementById('module-title').value = module.title;
            document.getElementById('module-description').value = module.description || '';
            document.getElementById('module-position').value = module.position;
            document.getElementById('module-content').value = module.content_json ? JSON.stringify(module.content_json, null, 2) : '';
            
        } catch (error) {
            window.app.showError('Failed to load module data: ' + error.message);
            this.hideModuleModal();
        }
    }

    async handleModuleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.moduleForm);
        
        let contentJson = null;
        const contentText = formData.get('content_json');
        if (contentText.trim()) {
            try {
                contentJson = JSON.parse(contentText);
            } catch (error) {
                window.app.showError('Invalid JSON in content field');
                return;
            }
        }
        
        const moduleData = {
            course_id: this.currentCourseId,
            title: formData.get('title'),
            description: formData.get('description') || null,
            position: parseInt(formData.get('position')),
            content_json: contentJson,
        };
        
        try {
            const submitBtn = this.moduleForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Saving...';
            submitBtn.disabled = true;
            
            if (this.currentModuleId) {
                await window.api.updateModule(this.currentModuleId, moduleData);
                window.app.showSuccess('Module updated successfully');
            } else {
                await window.api.createModule(moduleData);
                window.app.showSuccess('Module created successfully');
            }
            
            this.hideModuleModal();
            this.loadModules(this.currentCourseId);
            
        } catch (error) {
            window.app.showError('Failed to save module: ' + error.message);
        } finally {
            const submitBtn = this.moduleForm.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    editModule(moduleId) {
        this.showModuleModal(moduleId);
    }

    async deleteModule(moduleId) {
        const module = this.modules.find(m => m.unique_id === moduleId);
        if (!module) return;
        
        if (!confirm(`Are you sure you want to delete "${module.title}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            await window.api.deleteModule(moduleId);
            window.app.showSuccess('Module deleted successfully');
            this.loadModules(this.currentCourseId);
        } catch (error) {
            window.app.showError('Failed to delete module: ' + error.message);
        }
    }

    async manageTest(moduleId) {
        this.currentModuleId = moduleId;
        
        try {
            // Try to get existing test
            this.currentTest = await window.api.getModuleTest(moduleId);
            this.renderTestManagement();
        } catch (error) {
            // No test exists, show create test form
            this.currentTest = null;
            this.renderTestManagement();
        }
        
        this.testSection.classList.remove('hidden');
        
        // Scroll to test section
        this.testSection.scrollIntoView({ behavior: 'smooth' });
    }

    renderTestManagement() {
        if (this.currentTest) {
            this.testContent.innerHTML = `
                <div class="test-info">
                    <h4>${this.escapeHtml(this.currentTest.title)}</h4>
                    ${this.currentTest.description ? `<p>${this.escapeHtml(this.currentTest.description)}</p>` : ''}
                    <div class="test-actions">
                        <button class="btn btn-sm btn-secondary" onclick="modules.editTest()">Edit Test</button>
                        <button class="btn btn-sm btn-danger" onclick="modules.deleteTest()">Delete Test</button>
                    </div>
                </div>
                <div class="questions-section">
                    <h5>Questions</h5>
                    <button class="btn btn-sm btn-primary" onclick="window.tests.addQuestion()">Add Question</button>
                    <div id="questions-list">
                        ${this.renderQuestions()}
                    </div>
                </div>
            `;
            
            // Initialize tests manager with current test
            if (window.tests) {
                window.tests.setCurrentTest(this.currentTest);
            }
        } else {
            this.testContent.innerHTML = `
                <div class="no-test">
                    <p>No test exists for this module.</p>
                    <button class="btn btn-primary" onclick="modules.showTestModal()">Create Test</button>
                </div>
            `;
        }
    }

    renderQuestions() {
        if (!this.currentTest || !this.currentTest.questions.length) {
            return '<div class="placeholder">No questions yet</div>';
        }
        
        return this.currentTest.questions.map((question, index) => `
            <div class="question-item" data-question-id="${question.unique_id}">
                <div class="question-header" onclick="window.tests.toggleQuestion('${question.unique_id}')">
                    <span class="question-title">Question ${index + 1}: ${this.escapeHtml(question.question_text)}</span>
                    <span class="question-toggle">▼</span>
                </div>
                <div class="question-content">
                    <div class="answer-options">
                        ${question.answer_options.map(option => `
                            <div class="answer-option ${option.is_correct ? 'correct' : ''}">
                                <div class="answer-option-content">
                                    <span class="answer-option-text">${this.escapeHtml(option.answer_text)}</span>
                                    ${option.is_correct ? '<span class="answer-option-badge">Correct</span>' : ''}
                                    ${option.explanation ? `<div class="text-muted mt-1">${this.escapeHtml(option.explanation)}</div>` : ''}
                                </div>
                                <div class="answer-option-actions">
                                    <button class="btn btn-sm btn-secondary" onclick="window.tests.editAnswerOption('${question.unique_id}', '${option.unique_id}')">Edit</button>
                                    <button class="btn btn-sm btn-danger" onclick="window.tests.deleteAnswerOption('${question.unique_id}', '${option.unique_id}')">Delete</button>
                                </div>
                            </div>
                        `).join('')}
                        <div class="add-answer-option">
                            <button class="btn btn-sm btn-primary" onclick="window.tests.addAnswerOption('${question.unique_id}')">Add Answer Option</button>
                        </div>
                    </div>
                    <div class="question-actions mt-3">
                        <button class="btn btn-sm btn-secondary" onclick="window.tests.editQuestion('${question.unique_id}')">Edit Question</button>
                        <button class="btn btn-sm btn-danger" onclick="window.tests.deleteQuestion('${question.unique_id}')">Delete Question</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    showTestModal() {
        if (window.tests) {
            window.tests.showTestModal(this.currentModuleId, this.currentTest);
        }
    }

    editTest() {
        if (window.tests && this.currentTest) {
            window.tests.showTestModal(this.currentModuleId, this.currentTest);
        }
    }

    async deleteTest() {
        if (!this.currentTest) return;
        
        if (!confirm('Are you sure you want to delete this test? This action cannot be undone.')) {
            return;
        }
        
        try {
            await window.api.deleteTest(this.currentTest.unique_id);
            window.app.showSuccess('Test deleted successfully');
            this.currentTest = null;
            this.testSection.classList.add('hidden');
            this.loadModules(this.currentCourseId);
        } catch (error) {
            window.app.showError('Failed to delete test: ' + error.message);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create global modules manager instance
window.modules = new ModulesManager();