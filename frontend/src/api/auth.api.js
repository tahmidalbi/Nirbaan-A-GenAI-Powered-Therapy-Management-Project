import axiosInstance from './axios';

export const registerTherapist = async (therapistData) => {
  try {
    const response = await axiosInstance.post('/auth/register', therapistData);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Registration failed';
  }
};

export const loginTherapist = async (credentials) => {
  try {
    const response = await axiosInstance.post('/auth/login', credentials);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Login failed';
  }
};

export const getCurrentTherapist = async () => {
  try {
    const response = await axiosInstance.get('/auth/me');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch user data';
  }
};
