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

// ─── ERP Coach (LangGraph) ────────────────────────────────────────────────────

export const coachSendMessage = async (sessionId, message) => {
  try {
    const response = await axiosInstance.post(`/erp/sessions/${sessionId}/coach/message`, { message });
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to send message to coach';
  }
};

export const coachEndClick = async (sessionId) => {
  try {
    const response = await axiosInstance.post(`/erp/sessions/${sessionId}/coach/end-click`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to trigger end-session flow';
  }
};

export const coachDebriefSubmit = async (sessionId, patientDebriefText) => {
  try {
    const response = await axiosInstance.post(`/erp/sessions/${sessionId}/coach/debrief-submit`, {
      patient_debrief_text: patientDebriefText,
    });
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to submit debrief';
  }
};

// ─── Session Transcript ───────────────────────────────────────────────────────

export const getSessionTranscript = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/erp/sessions/${sessionId}/transcript`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch transcript';
  }
};

// ─── Patient Session History ──────────────────────────────────────────────────

export const listItemSessions = async (itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/items/${itemId}/sessions`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch session list';
  }
};

export const getSession = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/erp/sessions/${sessionId}`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch session';
  }
};

export const getSessionDetail = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/erp/sessions/${sessionId}/detail`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch session detail';
  }
};

export const getSessionSUDS = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/erp/sessions/${sessionId}/suds`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch session SUDS';
  }
};

// ─── Therapist Session Endpoints ──────────────────────────────────────────────

export const therapistListItemSessions = async (patientId, itemId) => {
  try {
    const response = await axiosInstance.get(`/erp/therapist/patients/${patientId}/items/${itemId}/sessions`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch sessions';
  }
};

export const therapistGetSessionDetail = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/erp/therapist/sessions/${sessionId}`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch session detail';
  }
};

export const therapistGetSessionTranscript = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/erp/therapist/sessions/${sessionId}/transcript`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch transcript';
  }
};

export const therapistGetSessionReport = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/erp/therapist/sessions/${sessionId}/report`);
    return { data: response.data };
  } catch (error) {
    if (error.response?.status === 404) return { data: null };
    throw error.response?.data?.detail || 'Failed to fetch session report';
  }
};

export const therapistGenerateCrossSessionOverview = async (sessionId) => {
  try {
    const response = await axiosInstance.post(`/erp/therapist/sessions/${sessionId}/cross-session-overview`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to generate cross-session overview';
  }
};
