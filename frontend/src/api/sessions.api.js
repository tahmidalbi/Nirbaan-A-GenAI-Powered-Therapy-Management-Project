import axiosInstance from './axios';

// ── Therapist ──────────────────────────────────────────────────────────────

export const createTherapySession = async (data) => {
  try {
    const response = await axiosInstance.post('/api/therapy-sessions/', data);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to create therapy session';
  }
};

export const getPatientSessionsTherapist = async (patientId) => {
  try {
    const response = await axiosInstance.get(`/api/therapy-sessions/patient/${patientId}`);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch sessions';
  }
};

export const updateTherapySession = async (sessionId, data) => {
  try {
    const response = await axiosInstance.put(`/api/therapy-sessions/${sessionId}`, data);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update session';
  }
};

export const deleteTherapySession = async (sessionId) => {
  try {
    await axiosInstance.delete(`/api/therapy-sessions/${sessionId}`);
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to delete session';
  }
};

// ── Live Sessions (video calls) ─────────────────────────────────────────────

export const startLiveSession = async (data) => {
  try {
    const response = await axiosInstance.post('/sessions/start', data);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to start live session';
  }
};

export const endLiveSession = async (sessionId) => {
  try {
    const response = await axiosInstance.post(`/sessions/${sessionId}/end`);
    return response.data;
  } catch (error) {
    // "already ended" is not a real error — ignore it silently
    const detail = error.response?.data?.detail || '';
    if (!detail.toLowerCase().includes('already ended')) {
      throw detail || 'Failed to end live session';
    }
  }
};

// ── Patient ────────────────────────────────────────────────────────────────

export const getMyTherapySessions = async () => {
  try {
    const response = await axiosInstance.get('/api/therapy-sessions/my-sessions');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch sessions';
  }
};
