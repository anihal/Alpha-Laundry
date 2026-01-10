// API Configuration
// Change this URL based on your environment
const CONFIG = {
    // Development API URL
    API_BASE_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8000/api'
        : '/api',

    // Token storage key
    TOKEN_KEY: 'laundry_auth_token',
    USER_TYPE_KEY: 'laundry_user_type',
    USER_ID_KEY: 'laundry_user_id',
    USERNAME_KEY: 'laundry_username',

    // Pagination
    DEFAULT_PAGE_SIZE: 20,

    // Auto-refresh intervals (in milliseconds)
    DASHBOARD_REFRESH_INTERVAL: 30000, // 30 seconds
};

// You can override the API URL by setting it in localStorage
// Example: localStorage.setItem('api_override', 'http://your-server.com/api')
if (localStorage.getItem('api_override')) {
    CONFIG.API_BASE_URL = localStorage.getItem('api_override');
}

export default CONFIG;
