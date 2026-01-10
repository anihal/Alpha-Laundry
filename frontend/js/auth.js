import CONFIG from './config.js';
import api from './api.js';

// Authentication Module
// Handles user authentication, token management, and session

class AuthService {
    // Check if user is authenticated
    isAuthenticated() {
        return !!localStorage.getItem(CONFIG.TOKEN_KEY);
    }

    // Get current user type (student or admin)
    getUserType() {
        return localStorage.getItem(CONFIG.USER_TYPE_KEY);
    }

    // Get current user ID
    getUserId() {
        return localStorage.getItem(CONFIG.USER_ID_KEY);
    }

    // Get current username
    getUsername() {
        return localStorage.getItem(CONFIG.USERNAME_KEY);
    }

    // Store authentication data
    storeAuthData(token, userType, userId, username) {
        localStorage.setItem(CONFIG.TOKEN_KEY, token);
        localStorage.setItem(CONFIG.USER_TYPE_KEY, userType);
        localStorage.setItem(CONFIG.USER_ID_KEY, userId);
        localStorage.setItem(CONFIG.USERNAME_KEY, username);
    }

    // Clear authentication data
    clearAuthData() {
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_TYPE_KEY);
        localStorage.removeItem(CONFIG.USER_ID_KEY);
        localStorage.removeItem(CONFIG.USERNAME_KEY);
    }

    // Login
    async login(username, password, userType = 'student') {
        try {
            const response = await api.login(username, password, userType);

            // Store authentication data
            this.storeAuthData(
                response.access_token,
                response.user_type,
                response.user_id,
                response.username
            );

            return {
                success: true,
                userType: response.user_type
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Logout
    async logout() {
        try {
            await api.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear auth data regardless of API response
            this.clearAuthData();
            // Redirect to login page
            window.location.href = '/index.html';
        }
    }

    // Verify token validity
    async verifyToken() {
        const token = localStorage.getItem(CONFIG.TOKEN_KEY);
        if (!token) {
            return false;
        }

        try {
            const response = await api.verifyToken(token);
            return response.valid === true;
        } catch (error) {
            // Token is invalid
            this.clearAuthData();
            return false;
        }
    }

    // Require authentication (redirect to login if not authenticated)
    async requireAuth(requiredUserType = null) {
        if (!this.isAuthenticated()) {
            window.location.href = '/index.html';
            return false;
        }

        // Verify token is still valid
        const isValid = await this.verifyToken();
        if (!isValid) {
            window.location.href = '/index.html';
            return false;
        }

        // Check user type if specified
        if (requiredUserType && this.getUserType() !== requiredUserType) {
            alert('Access denied. Insufficient permissions.');
            this.logout();
            return false;
        }

        return true;
    }

    // Redirect to appropriate dashboard based on user type
    redirectToDashboard() {
        const userType = this.getUserType();
        if (userType === 'admin') {
            window.location.href = '/admin-dashboard.html';
        } else {
            window.location.href = '/student-dashboard.html';
        }
    }
}

// Export singleton instance
const auth = new AuthService();
export default auth;
