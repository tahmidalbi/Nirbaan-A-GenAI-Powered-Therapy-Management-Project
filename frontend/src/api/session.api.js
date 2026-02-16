import axiosInstance from './axios';

/**
 * Create a new therapy session
 * @param {number} therapistId - ID of the therapist
 * @param {number} patientId - ID of the patient
 * @returns {Promise} - Created session object
 */
export const createSession = async (therapistId, patientId) => {
  try {
    const response = await axiosInstance.post('/sessions/', {
      therapist_id: therapistId,
      patient_id: patientId,
    });
    return response.data;
  } catch (error) {
    console.error('Error creating session:', error);
    throw error.response?.data?.detail || 'Failed to create therapy session';
  }
};

/**
 * Get a therapy session by ID
 * @param {number} sessionId - ID of the session
 * @returns {Promise} - Session object with transcript
 */
export const getSession = async (sessionId) => {
  try {
    const response = await axiosInstance.get(`/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching session:', error);
    throw error.response?.data?.detail || 'Failed to fetch therapy session';
  }
};

/**
 * List therapy sessions with optional filtering
 * @param {Object} params - Query parameters
 * @param {number} params.therapistId - Filter by therapist ID
 * @param {number} params.patientId - Filter by patient ID
 * @returns {Promise} - Array of session objects
 */
export const listSessions = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.therapistId) queryParams.append('therapist_id', params.therapistId);
    if (params.patientId) queryParams.append('patient_id', params.patientId);

    const response = await axiosInstance.get(`/sessions/?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error listing sessions:', error);
    throw error.response?.data?.detail || 'Failed to list therapy sessions';
  }
};

/**
 * Append a transcript entry to a therapy session
 * @param {number} sessionId - ID of the session
 * @param {Object} transcriptEntry - Transcript entry object
 * @param {string} transcriptEntry.speaker - Speaker identifier (e.g., 'therapist', 'patient')
 * @param {string} transcriptEntry.text - Text content
 * @param {string} transcriptEntry.emotion - Detected emotion (optional)
 * @param {string} transcriptEntry.timestamp - ISO timestamp
 * @returns {Promise} - Updated session object
 */
export const appendTranscript = async (sessionId, transcriptEntry) => {
  try {
    const response = await axiosInstance.post(
      `/sessions/${sessionId}/append-transcript`,
      {
        transcript_entry: transcriptEntry,
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error appending transcript:', error);
    throw error.response?.data?.detail || 'Failed to append transcript';
  }
};

/**
 * End a therapy session (update ended_at)
 * @param {number} sessionId - ID of the session
 * @returns {Promise} - Updated session object
 */
export const endSession = async (sessionId) => {
  try {
    const response = await axiosInstance.patch(`/sessions/${sessionId}/end`);
    return response.data;
  } catch (error) {
    console.error('Error ending session:', error);
    throw error.response?.data?.detail || 'Failed to end therapy session';
  }
};
