import axiosInstance from './axios';

// Patient API calls
export const createFearLadder = async (ladderData) => {
  try {
    const response = await axiosInstance.post('/fear-ladders/', ladderData);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to create fear ladder';
  }
};

export const getMyFearLadder = async () => {
  try {
    const response = await axiosInstance.get('/fear-ladders/my-ladder');
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch fear ladder';
  }
};

export const updateMyFearLadder = async (ladderData) => {
  try {
    const response = await axiosInstance.put('/fear-ladders/my-ladder', ladderData);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update fear ladder';
  }
};

// Therapist API calls
export const getAllFearLadders = async () => {
  try {
    const response = await axiosInstance.get('/fear-ladders/all');
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch fear ladders';
  }
};

export const getPatientFearLadder = async (patientId) => {
  try {
    const response = await axiosInstance.get(`/fear-ladders/patient/${patientId}`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch patient fear ladder';
  }
};

export const updatePatientFearLadder = async (patientId, ladderData) => {
  try {
    const response = await axiosInstance.put(`/fear-ladders/patient/${patientId}`, ladderData);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update fear ladder';
  }
};

export const approveFearLadder = async (patientId) => {
  try {
    const response = await axiosInstance.post(`/fear-ladders/patient/${patientId}/approve`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to approve fear ladder';
  }
};
