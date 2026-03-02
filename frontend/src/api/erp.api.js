import axiosInstance from './axios';

// ─── ERP Items ────────────────────────────────────────────────────────────────

export const listERPItems = async () => {
  try {
    const response = await axiosInstance.get('/erp/items');
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch ERP items';
  }
};

export const getERPItem = async (itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/items/${itemId}`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch ERP item';
  }
};

export const createERPItem = async (payload) => {
  try {
    const response = await axiosInstance.post('/erp/items', payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to create ERP item';
  }
};

export const updateERPItem = async (itemId, payload) => {
  try {
    const response = await axiosInstance.put(`/erp/items/${itemId}`, payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update ERP item';
  }
};

export const deleteERPItem = async (itemId) => {
  try {
    await axiosInstance.delete(`/erp/items/${itemId}`);
    return { success: true };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to delete ERP item';
  }
};

// ─── Session Note ─────────────────────────────────────────────────────────────

export const updateSessionNote = async (itemId, sessionExerciseNote) => {
  try {
    const response = await axiosInstance.patch(`/erp/items/${itemId}/session-note`, {
      session_exercise_note: sessionExerciseNote,
    });
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to save session note';
  }
};

// ─── Imaginal Cards ───────────────────────────────────────────────────────────

export const listImaginalCards = async (itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/items/${itemId}/imaginal-cards`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch imaginal cards';
  }
};

export const createImaginalCard = async (itemId, payload = { content: '' }) => {
  try {
    const response = await axiosInstance.post(`/erp/items/${itemId}/imaginal-cards`, payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to create imaginal card';
  }
};

export const updateImaginalCard = async (cardId, payload) => {
  try {
    const response = await axiosInstance.put(`/erp/imaginal-cards/${cardId}`, payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update imaginal card';
  }
};

export const deleteImaginalCard = async (cardId) => {
  try {
    await axiosInstance.delete(`/erp/imaginal-cards/${cardId}`);
    return { success: true };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to delete imaginal card';
  }
};

// ─── Live Sessions ────────────────────────────────────────────────────────────

export const getActiveSession = async (itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/items/${itemId}/sessions/active`);
    return { data: response.data };
  } catch (error) {
    if (error.response?.status === 404) return { data: null };
    throw error.response?.data?.detail || 'Failed to fetch active session';
  }
};

export const startSession = async (itemId) => {
  try {
    const response = await axiosInstance.post(`/erp/items/${itemId}/sessions/start`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to start session';
  }
};

export const pauseSession = async (sessionId) => {
  try {
    const response = await axiosInstance.patch(`/erp/sessions/${sessionId}/pause`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to pause session';
  }
};

export const resumeSession = async (sessionId) => {
  try {
    const response = await axiosInstance.patch(`/erp/sessions/${sessionId}/resume`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to resume session';
  }
};

export const endSession = async (sessionId) => {
  try {
    const response = await axiosInstance.patch(`/erp/sessions/${sessionId}/end`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to end session';
  }
};

// ─── SUDS ─────────────────────────────────────────────────────────────────────

export const recordSUDS = async (sessionId, sudsValue, elapsedSeconds) => {
  try {
    const response = await axiosInstance.post(`/erp/sessions/${sessionId}/suds`, {
      suds_value: sudsValue,
      elapsed_seconds: elapsedSeconds,
    });
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to record SUDS';
  }
};

export const getSUDSHistory = async (itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/items/${itemId}/suds-history`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch SUDS history';
  }
};

// ─── Therapist ERP ────────────────────────────────────────────────────────────

export const therapistListERPPatients = async () => {
  try {
    const response = await axiosInstance.get('/erp/therapist/patients');
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch ERP patients';
  }
};

export const therapistListPatientERPItems = async (patientId) => {
  try {
    const response = await axiosInstance.get(`/erp/therapist/patients/${patientId}/items`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch patient ERP items';
  }
};

export const therapistGetERPItemDetail = async (patientId, itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/therapist/patients/${patientId}/items/${itemId}`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch ERP item detail';
  }
};

// ─── Exercise Notes ───────────────────────────────────────────────────────────

export const getLatestExerciseNote = async (itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/items/${itemId}/exercise-notes/latest`);
    return { data: response.data }; // data may be null
  } catch (error) {
    if (error.response?.status === 404) return { data: null };
    throw error.response?.data?.detail || 'Failed to fetch exercise note';
  }
};

export const createExerciseNote = async (itemId, content) => {
  try {
    const response = await axiosInstance.post(`/erp/items/${itemId}/exercise-notes`, { content });
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to save exercise note';
  }
};

export const updateExerciseNote = async (noteId, content) => {
  try {
    const response = await axiosInstance.patch(`/erp/exercise-notes/${noteId}`, { content });
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update exercise note';
  }
};
