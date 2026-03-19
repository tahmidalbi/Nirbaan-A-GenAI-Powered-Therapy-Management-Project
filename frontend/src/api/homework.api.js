import axiosInstance from './axios';

// ============ THERAPIST API ============

/**
 * Get all active sessions with AI-generated homeworks
 */
export const getActiveSessionsWithHomeworks = async () => {
  try {
    const response = await axiosInstance.get('/homeworks/therapist/active-sessions');
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch active sessions';
  }
};

/**
 * Edit homeworks in session analysis
 */
export const updateSessionHomeworks = async (sessionId, homeworks) => {
  try {
    const response = await axiosInstance.put(
      `/homeworks/sessions/${sessionId}/analysis/homeworks`,
      { homeworks }
    );
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update homeworks';
  }
};

/**
 * Approve homeworks and create PatientHomework records
 */
export const approveSessionHomeworks = async (sessionId, homeworks) => {
  try {
    const response = await axiosInstance.post(
      `/homeworks/sessions/${sessionId}/approve`,
      { homeworks }
    );
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to approve homeworks';
  }
};

// ============ PATIENT API ============

/**
 * Get patient's homeworks by week
 */
export const getMyHomeworks = async () => {
  try {
    const response = await axiosInstance.get('/homeworks/me');
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch homeworks';
  }
};

/**
 * Mark homework as completed
 */
export const markHomeworkComplete = async (homeworkId, notes = null) => {
  try {
    const response = await axiosInstance.post(
      `/homeworks/me/${homeworkId}/complete`,
      { notes }
    );
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to mark homework complete';
  }
};
