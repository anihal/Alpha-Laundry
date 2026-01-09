import axios from 'axios';
import { handleApiError } from './errorHandler';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(handleApiError(error));
  }
);

// Handle response errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError = handleApiError(error);
    
    // Handle authentication errors
    if (apiError.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    
    return Promise.reject(apiError);
  }
);

export default client; 