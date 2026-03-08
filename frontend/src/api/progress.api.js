import api from './axios';

// ==================== PATIENT ENDPOINTS ====================

/**
 * Submit a weekly progress update
 */
export const createWeeklyProgress = async (progressData) => {
  const response = await api.post('/api/progress/', progressData);
  return response.data;
};

/**
 * Get all weekly progress updates for the current patient
 */
export const getMyProgress = async () => {
  const response = await api.get('/api/progress/my-progress');
  return response.data;
};

// ==================== THERAPIST ENDPOINTS ====================

/**
 * Get all weekly progress updates for a specific patient (Therapist only)
 */
export const getPatientProgress = async (patientId) => {
  const response = await api.get(`/api/progress/patient/${patientId}`);
  return response.data;
};
