import axios from 'axios';

const DEV_API_URL = 'http://localhost:8000/api/v1';
const PROD_API_URL = import.meta.env.VITE_API_BASE_URL || DEV_API_URL;

console.log(`Using API Base URL: ${PROD_API_URL}`); 

const api = axios.create({ baseURL: PROD_API_URL, timeout: 30000 });

api.interceptors.request.use(cfg => {
    const token = localStorage.getItem('token');
    if (token) cfg.headers['Authorization'] = `Bearer ${token}`;
    return cfg;
});

api.interceptors.response.use(
    response => response,
    error => {
        console.error('API Error:', error);
        
        if (error.response) {
            const { status, data } = error.response;
            console.error(`Error ${status}:`, data?.message || 'Unknown error');
        }
        
        return Promise.reject(error);
    }
);

export default api;
