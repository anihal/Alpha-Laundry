import CONFIG from './config.js';

// API Service Module
// Handles all communication with the backend API

class APIService {
    constructor() {
        this.baseURL = CONFIG.API_BASE_URL;
    }

    // Get authentication token from localStorage
    getToken() {
        return localStorage.getItem(CONFIG.TOKEN_KEY);
    }

    // Build URL with token if authenticated
    buildURL(endpoint, params = {}) {
        const url = new URL(`${this.baseURL}${endpoint}`);

        // Add token to query params if available
        const token = this.getToken();
        if (token) {
            url.searchParams.append('token', token);
        }

        // Add additional params
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });

        return url.toString();
    }

    // Generic fetch wrapper with error handling
    async request(endpoint, options = {}, params = {}) {
        const url = this.buildURL(endpoint, params);

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                // Handle error responses
                throw new APIError(
                    data.error || data.detail || 'Request failed',
                    response.status,
                    data
                );
            }

            return data;
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            // Network or other errors
            throw new APIError('Network error. Please check your connection.', 0, error);
        }
    }

    // Authentication endpoints
    async login(username, password, userType = 'student') {
        return await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                username,
                password,
                user_type: userType
            })
        });
    }

    async verifyToken(token) {
        return await this.request('/auth/verify', {}, { token });
    }

    async logout() {
        return await this.request('/auth/logout', { method: 'POST' });
    }

    // Student endpoints
    async getStudentDashboard() {
        return await this.request('/student/dashboard');
    }

    async submitLaundryRequest(numClothes, priority = 'normal', notes = '') {
        return await this.request('/student/submit', {
            method: 'POST',
            body: JSON.stringify({
                num_clothes: numClothes,
                priority,
                notes
            })
        });
    }

    async getStudentHistory(page = 1, pageSize = CONFIG.DEFAULT_PAGE_SIZE) {
        return await this.request('/student/history', {}, { page, page_size: pageSize });
    }

    async getJobDetails(jobId) {
        return await this.request(`/student/job/${jobId}`);
    }

    // Admin endpoints
    async getAdminDashboard() {
        return await this.request('/admin/dashboard');
    }

    async updateJobStatus(requestId, status) {
        return await this.request('/admin/update-status', {
            method: 'PATCH',
            body: JSON.stringify({
                request_id: requestId,
                status
            })
        });
    }

    async getAdminAnalytics(days = 7) {
        return await this.request('/admin/analytics', {}, { days });
    }

    async getAdminJobs(status = null, page = 1, pageSize = CONFIG.DEFAULT_PAGE_SIZE) {
        const params = { page, page_size: pageSize };
        if (status) {
            params.status = status;
        }
        return await this.request('/admin/jobs', {}, params);
    }

    // Health check
    async healthCheck() {
        return await this.request('/health', {}, {});
    }
}

// Custom error class for API errors
class APIError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }
}

// Export singleton instance
const api = new APIService();
export default api;
export { APIError };
