class ApiClient {
    constructor() {
        this.baseURL = '/api/v2';
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }

    setTokens(accessToken, refreshToken) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    }

    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        if (this.accessToken) {
            config.headers.Authorization = `Bearer ${this.accessToken}`;
        }

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Try to refresh token
                if (this.refreshToken) {
                    const refreshed = await this.refreshAccessToken();
                    if (refreshed) {
                        // Retry the original request with new token
                        config.headers.Authorization = `Bearer ${this.accessToken}`;
                        return fetch(url, config);
                    }
                }
                // If refresh fails, clear tokens and redirect to login
                this.clearTokens();
                window.location.reload();
                return;
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }

            return response;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async refreshAccessToken() {
        try {
            const response = await fetch(`${this.baseURL}/auth/refresh-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    refresh_token: this.refreshToken,
                }),
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();
            this.setTokens(data.access_token, data.refresh_token);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            this.clearTokens();
            return false;
        }
    }

    // Authentication endpoints
    async login(email, password) {
        const response = await this.request('/auth/access-token', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();
        this.setTokens(data.access_token, data.refresh_token);
        return data;
    }

    // Courses endpoints
    async getCourses(skip = 0, limit = 100) {
        const response = await this.request(`/admin/courses?skip=${skip}&limit=${limit}`);
        return response.json();
    }

    async getCourse(courseId) {
        const response = await this.request(`/admin/courses/${courseId}`);
        return response.json();
    }

    async createCourse(courseData) {
        const response = await this.request('/admin/courses', {
            method: 'POST',
            body: JSON.stringify(courseData),
        });
        return response.json();
    }

    async updateCourse(courseId, courseData) {
        const response = await this.request(`/admin/courses/${courseId}`, {
            method: 'PUT',
            body: JSON.stringify(courseData),
        });
        return response.json();
    }

    async deleteCourse(courseId) {
        await this.request(`/admin/courses/${courseId}`, {
            method: 'DELETE',
        });
    }

    // Modules endpoints
    async getModules(courseId) {
        const response = await this.request(`/admin/courses/${courseId}/modules`);
        return response.json();
    }

    async getModule(moduleId) {
        const response = await this.request(`/admin/modules/${moduleId}`);
        return response.json();
    }

    async createModule(moduleData) {
        const response = await this.request(`/admin/courses/${moduleData.course_id}/modules`, {
            method: 'POST',
            body: JSON.stringify(moduleData),
        });
        return response.json();
    }

    async updateModule(moduleId, moduleData) {
        const response = await this.request(`/admin/modules/${moduleId}`, {
            method: 'PUT',
            body: JSON.stringify(moduleData),
        });
        return response.json();
    }

    async deleteModule(moduleId) {
        await this.request(`/admin/modules/${moduleId}`, {
            method: 'DELETE',
        });
    }

    async reorderModules(courseId, modulePositions) {
        const response = await this.request(`/admin/courses/${courseId}/modules/reorder`, {
            method: 'POST',
            body: JSON.stringify({ module_positions: modulePositions }),
        });
        return response.json();
    }

    // Tests endpoints
    async getModuleTest(moduleId) {
        const response = await this.request(`/admin/modules/${moduleId}/test`);
        return response.json();
    }

    async getTest(testId) {
        const response = await this.request(`/admin/tests/${testId}`);
        return response.json();
    }

    async createTest(moduleId, testData) {
        const response = await this.request(`/admin/modules/${moduleId}/test`, {
            method: 'POST',
            body: JSON.stringify(testData),
        });
        return response.json();
    }

    async updateTest(testId, testData) {
        const response = await this.request(`/admin/tests/${testId}`, {
            method: 'PUT',
            body: JSON.stringify(testData),
        });
        return response.json();
    }

    async deleteTest(testId) {
        await this.request(`/admin/tests/${testId}`, {
            method: 'DELETE',
        });
    }

    // Questions endpoints
    async getTestQuestions(testId) {
        const response = await this.request(`/admin/tests/${testId}/questions`);
        return response.json();
    }

    async getQuestion(questionId) {
        const response = await this.request(`/admin/questions/${questionId}`);
        return response.json();
    }

    async createQuestion(testId, questionData) {
        const response = await this.request(`/admin/tests/${testId}/questions`, {
            method: 'POST',
            body: JSON.stringify(questionData),
        });
        return response.json();
    }

    async updateQuestion(questionId, questionData) {
        const response = await this.request(`/admin/questions/${questionId}`, {
            method: 'PUT',
            body: JSON.stringify(questionData),
        });
        return response.json();
    }

    async deleteQuestion(questionId) {
        await this.request(`/admin/questions/${questionId}`, {
            method: 'DELETE',
        });
    }

    // Answer Options endpoints
    async createAnswerOption(questionId, optionData) {
        const response = await this.request(`/admin/questions/${questionId}/answer-options`, {
            method: 'POST',
            body: JSON.stringify(optionData),
        });
        return response.json();
    }

    async updateAnswerOption(optionId, optionData) {
        const response = await this.request(`/admin/answer-options/${optionId}`, {
            method: 'PUT',
            body: JSON.stringify(optionData),
        });
        return response.json();
    }

    async deleteAnswerOption(optionId) {
        await this.request(`/admin/answer-options/${optionId}`, {
            method: 'DELETE',
        });
    }

    // Users endpoints
    async getUsers(skip = 0, limit = 100, role = null) {
        let url = `/admin/users?skip=${skip}&limit=${limit}`;
        if (role) {
            url += `&role=${role}`;
        }
        const response = await this.request(url);
        return response.json();
    }

    async getUser(userId) {
        const response = await this.request(`/admin/users/${userId}`);
        return response.json();
    }

    async updateUserRole(userId, role) {
        const response = await this.request(`/admin/users/${userId}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role }),
        });
        return response.json();
    }

    // Tags endpoints
    async getTags(skip = 0, limit = 100) {
        const response = await this.request(`/admin/tags?skip=${skip}&limit=${limit}`);
        return response.json();
    }

    async getTag(tagId) {
        const response = await this.request(`/admin/tags/${tagId}`);
        return response.json();
    }

    async createTag(tagData) {
        const response = await this.request('/admin/tags', {
            method: 'POST',
            body: JSON.stringify(tagData),
        });
        return response.json();
    }

    async updateTag(tagId, tagData) {
        const response = await this.request(`/admin/tags/${tagId}`, {
            method: 'PUT',
            body: JSON.stringify(tagData),
        });
        return response.json();
    }

    async deleteTag(tagId) {
        await this.request(`/admin/tags/${tagId}`, {
            method: 'DELETE',
        });
    }
}

// Create global API client instance
window.api = new ApiClient();