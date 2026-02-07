import axiosInstance from './axios';

// Register new emergency personnel (therapist only)
export const registerEmergencyPersonnel = async (personnelData) => {
  try {
    const response = await axiosInstance.post('/emergency-personnel/register', personnelData);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to register emergency personnel';
  }
};

// Get all emergency personnel for therapist
export const getEmergencyPersonnel = async () => {
  try {
    const response = await axiosInstance.get('/emergency-personnel/');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch emergency personnel';
  }
};

// Get single emergency personnel by ID
export const getEmergencyPersonnelById = async (id) => {
  try {
    const response = await axiosInstance.get(`/emergency-personnel/${id}`);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch emergency personnel';
  }
};

// Update emergency personnel
export const updateEmergencyPersonnel = async (id, personnelData) => {
  try {
    const response = await axiosInstance.put(`/emergency-personnel/${id}`, personnelData);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update emergency personnel';
  }
};

// Login emergency personnel
export const loginEmergencyPersonnel = async (credentials) => {
  try {
    const response = await axiosInstance.post('/emergency-personnel/login', credentials);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Login failed';
  }
};

// Get current emergency personnel profile
export const getCurrentEmergencyPersonnel = async () => {
  try {
    const response = await axiosInstance.get('/emergency-personnel/me');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch profile';
  }
};
