import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include token
axiosInstance.interceptors.request.use(
  (config) => {
    const authStorage = localStorage.getItem('auth-storage');
    console.log('[AXIOS] Auth storage:', authStorage);
    
    if (authStorage) {
      const { state } = JSON.parse(authStorage);
      console.log('[AXIOS] Parsed state:', state);
      console.log('[AXIOS] Token:', state?.token);
      
      if (state?.token) {
        config.headers.Authorization = `Bearer ${state.token}`;
        console.log('[AXIOS] Added Authorization header:', config.headers.Authorization);
      } else {
        console.log('[AXIOS] No token found in state');
      }
    } else {
      console.log('[AXIOS] No auth-storage in localStorage');
    }
    
    console.log('[AXIOS] Request URL:', config.url);
    console.log('[AXIOS] Request headers:', config.headers);
    return config;
  },
  (error) => {
    console.error('[AXIOS] Request error:', error);
    return Promise.reject(error);
  }
);

export default axiosInstance;
