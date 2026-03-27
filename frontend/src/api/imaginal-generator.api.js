import axiosInstance from './axios';

const API_BASE = 'http://127.0.0.1:8000';

// Helper: build the backend-proxied audio URL for a given script id
export const getAudioUrl = (scriptId) => `${API_BASE}/imaginal-generator/audio/${scriptId}`;

// POST /imaginal-generator/start
export const startImaginalRun = async (payload) => {
  try {
    const response = await axiosInstance.post('/imaginal-generator/start', payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to start imaginal script generation';
  }
};

// POST /imaginal-generator/review
export const reviewImaginalRun = async (payload) => {
  try {
    const response = await axiosInstance.post('/imaginal-generator/review', payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to submit review';
  }
};

// GET /imaginal-generator/patient/{patientId}/approved
export const listPatientApprovedScripts = async (patientId) => {
  try {
    const response = await axiosInstance.get(`/imaginal-generator/patient/${patientId}/approved`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch approved scripts';
  }
};

// GET /imaginal-generator/erp-item/{erpItemId}/approved
export const listApprovedByItem = async (erpItemId) => {
  try {
    const response = await axiosInstance.get(`/imaginal-generator/erp-item/${erpItemId}/approved`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch scripts for this item';
  }
};
