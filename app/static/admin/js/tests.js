class TestsManager {
    constructor() {
        this.currentTest = null;
        this.currentModuleId = null;
        this.testModal = null;
        this.testForm = null;
        this.questionModal = null;
        this.questionForm = null;
        this.answerOptionModal = null;
        this.answerOptionForm = null;
        
        this.init();
    }

    init() {
        // Create test modal dynamically
        this.createTestModal();
        this.createQuestionModal();
        this.createAnswerOptionModal();
    }

    createTestModal() {
        const modalHtml = `
            <div id="test-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="test-modal-title">Add Test</h3>
                        <button class="close-btn">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="test-form">
                            <div class="form-group">
                                <label for="test-title">Title</label>
                                <input type="text" id="test-title" name="title" required>
                            </div>
                            <div class="form-group">
                                <label for="test-description">Description</label>
                                <textarea id="test-description" name="description" rows="4"></textarea>
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="btn btn-primary">Save</button>
                                <button type="button" class="btn btn-secondary cancel-btn">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        this.testModal = document.getElementById('test-modal');
        this.testForm = document.getElementById('test-form');
        this.testModalTitle = document.getElementById('test-modal-title');
        
        // Setup event listeners
        this.testForm.addEventListener('submit', (e) => this.handleTestSubmit(e));
        this.testModal.querySelector('.close-btn').addEventListener('click', () => this.hideTestModal());
        this.testModal.querySelector('.cancel-btn').addEventListener('click', () => this.hideTestModal());
        
        this.testModal.addEventListener('click', (e) => {
            if (e.target === this.testModal) {
                this.hideTestModal();
            }
        });
    }

    createQuestionModal() {
        const modalHtml = `
            <div id="question-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="question-modal-title">Add Question</h3>
                        <button class="close-btn">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="question-form">
                            <div class="form-group">
                                <label for="question-text">Question Text</label>
                                <textarea id="question-text" name="question_text" rows="4" required></textarea>
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="btn btn-primary">Save</button>
                                <button type="button" class="btn btn-secondary cancel-btn">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        this.questionModal = document.getElementById('question-modal');
        this.questionForm = document.getElementById('question-form');
        this.questionModalTitle = document.getElementById('question-modal-title');
        
        // Setup event listeners
        this.questionForm.addEventListener('submit', (e) => this.handleQuestionSubmit(e));
        this.questionModal.querySelector('.close-btn').addEventListener('click', () => this.hideQuestionModal());
        this.questionModal.querySelector('.cancel-btn').addEventListener('click', () => this.hideQuestionModal());
        
        this.questionModal.addEventListener('click', (e) => {
            if (e.target === this.questionModal) {
                this.hideQuestionModal();
            }
        });
    }

    createAnswerOptionModal() {
        const modalHtml = `
            <div id="answer-option-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="answer-option-modal-title">Add Answer Option</h3>
                        <button class="close-btn">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="answer-option-form">
                            <div class="form-group">
                                <label for="answer-text">Answer Text</label>
                                <input type="text" id="answer-text" name="answer_text" required>
                            </div>
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="is-correct" name="is_correct">
                                    Correct Answer
                                </label>
                            </div>
                            <div class="form-group">
                                <label for="explanation">Explanation (optional)</label>
                                <textarea id="explanation" name="explanation" rows="3"></textarea>
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="btn btn-primary">Save</button>
                                <button type="button" class="btn btn-secondary cancel-btn">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        this.answerOptionModal = document.getElementById('answer-option-modal');
        this.answerOptionForm = document.getElementById('answer-option-form');
        this.answerOptionModalTitle = document.getElementById('answer-option-modal-title');
        
        // Setup event listeners
        this.answerOptionForm.addEventListener('submit', (e) => this.handleAnswerOptionSubmit(e));
        this.answerOptionModal.querySelector('.close-btn').addEventListener('click', () => this.hideAnswerOptionModal());
        this.answerOptionModal.querySelector('.cancel-btn').addEventListener('click', () => this.hideAnswerOptionModal());
        
        this.answerOptionModal.addEventListener('click', (e) => {
            if (e.target === this.answerOptionModal) {
                this.hideAnswerOptionModal();
            }
        });
    }

    setCurrentTest(test) {
        this.currentTest = test;
    }

    showTestModal(moduleId, test = null) {
        this.currentModuleId = moduleId;
        
        if (test) {
            this.testModalTitle.textContent = 'Edit Test';
            this.testForm.querySelector('#test-title').value = test.title;
            this.testForm.querySelector('#test-description').value = test.description || '';
        } else {
            this.testModalTitle.textContent = 'Add Test';
            this.testForm.reset();
        }
        
        this.testModal.classList.add('active');
    }

    hideTestModal() {
        this.testModal.classList.remove('active');
        this.testForm.reset();
    }

    async handleTestSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.testForm);
        const testData = {
            module_id: this.currentModuleId,
            title: formData.get('title'),
            description: formData.get('description') || null,
        };
        
        try {
            const submitBtn = this.testForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Saving...';
            submitBtn.disabled = true;
            
            if (this.currentTest) {
                await window.api.updateTest(this.currentTest.unique_id, testData);
                window.app.showSuccess('Test updated successfully');
            } else {
                await window.api.createTest(this.currentModuleId, testData);
                window.app.showSuccess('Test created successfully');
            }
            
            this.hideTestModal();
            
            // Refresh the test management section
            if (window.modules) {
                await window.modules.manageTest(this.currentModuleId);
            }
            
        } catch (error) {
            window.app.showError('Failed to save test: ' + error.message);
        } finally {
            const submitBtn = this.testForm.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    showQuestionModal(question = null) {
        if (question) {
            this.questionModalTitle.textContent = 'Edit Question';
            this.questionForm.querySelector('#question-text').value = question.question_text;
        } else {
            this.questionModalTitle.textContent = 'Add Question';
            this.questionForm.reset();
        }
        
        this.questionModal.classList.add('active');
    }

    hideQuestionModal() {
        this.questionModal.classList.remove('active');
        this.questionForm.reset();
    }

    async handleQuestionSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.questionForm);
        const questionData = {
            test_id: this.currentTest.unique_id,
            question_text: formData.get('question_text'),
        };
        
        try {
            const submitBtn = this.questionForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Saving...';
            submitBtn.disabled = true;
            
            if (this.currentQuestion) {
                await window.api.updateQuestion(this.currentQuestion.unique_id, questionData);
                window.app.showSuccess('Question updated successfully');
            } else {
                await window.api.createQuestion(this.currentTest.unique_id, questionData);
                window.app.showSuccess('Question created successfully');
            }
            
            this.hideQuestionModal();
            await this.refreshTest(this.currentQuestion ? this.currentQuestion.unique_id : null);
            
        } catch (error) {
            window.app.showError('Failed to save question: ' + error.message);
        } finally {
            const submitBtn = this.questionForm.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    addQuestion() {
        this.currentQuestion = null;
        this.showQuestionModal();
    }

    editQuestion(questionId) {
        const question = this.currentTest.questions.find(q => q.unique_id === questionId);
        if (question) {
            this.currentQuestion = question;
            this.showQuestionModal(question);
        }
    }

    async deleteQuestion(questionId) {
        const question = this.currentTest.questions.find(q => q.unique_id === questionId);
        if (!question) return;
        
        if (!confirm('Are you sure you want to delete this question? This action cannot be undone.')) {
            return;
        }
        
        try {
            await window.api.deleteQuestion(questionId);
            window.app.showSuccess('Question deleted successfully');
            await this.refreshTest(this.currentQuestionId);
        } catch (error) {
            window.app.showError('Failed to delete question: ' + error.message);
        }
    }

    toggleQuestion(questionId) {
        const questionItem = document.querySelector(`[data-question-id="${questionId}"]`);
        if (questionItem) {
            questionItem.classList.toggle('expanded');
        }
    }

    showAnswerOptionModal(questionId, option = null) {
        this.currentQuestionId = questionId;
        
        if (option) {
            this.answerOptionModalTitle.textContent = 'Edit Answer Option';
            this.answerOptionForm.querySelector('#answer-text').value = option.answer_text;
            this.answerOptionForm.querySelector('#is-correct').checked = option.is_correct;
            this.answerOptionForm.querySelector('#explanation').value = option.explanation || '';
        } else {
            this.answerOptionModalTitle.textContent = 'Add Answer Option';
            this.answerOptionForm.reset();
        }
        
        this.answerOptionModal.classList.add('active');
    }

    hideAnswerOptionModal() {
        this.answerOptionModal.classList.remove('active');
        this.answerOptionForm.reset();
    }

    async handleAnswerOptionSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.answerOptionForm);
        const optionData = {
            question_id: this.currentQuestionId,
            answer_text: formData.get('answer_text'),
            is_correct: formData.has('is_correct'),
            explanation: formData.get('explanation') || null,
        };
        
        try {
            const submitBtn = this.answerOptionForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Saving...';
            submitBtn.disabled = true;
            
            if (this.currentAnswerOption) {
                await window.api.updateAnswerOption(this.currentAnswerOption.unique_id, optionData);
                window.app.showSuccess('Answer option updated successfully');
            } else {
                await window.api.createAnswerOption(this.currentQuestionId, optionData);
                window.app.showSuccess('Answer option created successfully');
            }
            
            this.hideAnswerOptionModal();
            await this.refreshTest(this.currentQuestionId);
            
        } catch (error) {
            window.app.showError('Failed to save answer option: ' + error.message);
        } finally {
            const submitBtn = this.answerOptionForm.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    addAnswerOption(questionId) {
        this.currentQuestionId = questionId;
        this.currentAnswerOption = null;
        this.showAnswerOptionModal(questionId);
    }

    editAnswerOption(questionId, optionId) {
        this.currentQuestionId = questionId;
        const question = this.currentTest.questions.find(q => q.unique_id === questionId);
        if (question) {
            const option = question.answer_options.find(o => o.unique_id === optionId);
            if (option) {
                this.currentAnswerOption = option;
                this.showAnswerOptionModal(questionId, option);
            }
        }
    }

    async deleteAnswerOption(questionId, optionId) {
        const question = this.currentTest.questions.find(q => q.unique_id === questionId);
        if (!question) return;
        
        const option = question.answer_options.find(o => o.unique_id === optionId);
        if (!option) return;
        
        if (!confirm(`Are you sure you want to delete this answer option? This action cannot be undone.`)) {
            return;
        }
        
        try {
            await window.api.deleteAnswerOption(optionId);
            window.app.showSuccess('Answer option deleted successfully');
            await this.refreshTest(this.currentQuestionId);
        } catch (error) {
            window.app.showError('Failed to delete answer option: ' + error.message);
        }
    }

    async refreshTest(expandedQuestionId = null) {
        try {
            // 1. Get the fresh data
            this.currentTest = await window.api.getTest(this.currentTest.unique_id);
            
            // 2. Update the test management section
            if (window.modules) {
                window.modules.currentTest = this.currentTest;
                
                // 3. Re-render the UI
                await window.modules.renderTestManagement();
                
                // 4. RESTORE STATE: If we have an ID to keep open, re-open it
                if (expandedQuestionId) {
                    const questionItem = document.querySelector(`[data-question-id="${expandedQuestionId}"]`);
                    if (questionItem) {
                        questionItem.classList.add('expanded');
                        
                        // Optional: Scroll to the question so the user doesn't lose their place
                        questionItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }
        } catch (error) {
            window.app.showError('Failed to refresh test: ' + error.message);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create global tests manager instance
window.tests = new TestsManager();