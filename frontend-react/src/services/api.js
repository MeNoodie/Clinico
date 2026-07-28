import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to attach the JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const authService = {
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  register: async (name, email, phone, password) => {
    const response = await api.post('/auth/signup', { name, email, phone, password });
    return response.data;
  },
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

export const chatService = {
  startSession: async (intent) => {
    const response = await api.post('/chat/session/start', {
      intent: intent || null,
    });
    return response.data;
  },
  replySession: async (sessionId, message) => {
    const response = await api.post('/chat/session/reply', {
      session_id: sessionId,
      message: message,
    });
    return response.data;
  },
};

export default api;
