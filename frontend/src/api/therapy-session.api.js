import axiosInstance from './axios';

const API_BASE = '/sessions';

/**
 * Start a new therapy session
 */
export const startSession = async (therapistId, patientId) => {
  const response = await axiosInstance.post(`${API_BASE}/start`, {
    therapist_id: therapistId,
    patient_id: patientId
  });
  return response.data;
};

/**
 * Append transcript to a session
 */
export const appendTranscript = async (sessionId, speaker, text) => {
  const response = await axiosInstance.post(
    `${API_BASE}/${sessionId}/append-transcript`,
    {
      speaker,
      text
    }
  );
  return response.data;
};

/**
 * Get session with full transcript
 */
export const getSession = async (sessionId) => {
  const response = await axiosInstance.get(`${API_BASE}/${sessionId}`);
  return response.data;
};

/**
 * Get user call status
 */
export const getUserCallStatus = async (userId) => {
  const response = await axiosInstance.get(`/call/status/${userId}`);
  return response.data;
};

/**
 * Get all transcript entries for a session
 */
export const getSessionTranscripts = async (sessionId) => {
  const response = await axiosInstance.get(`${API_BASE}/${sessionId}/transcripts`);
  return response.data;
};

/**
 * Transcribe audio file
 */
export const transcribeAudio = async (audioBlob, options = {}) => {
  const formData = new FormData();
  
  const fileExtension = options.format || 'webm';
  formData.append('audio', audioBlob, `recording.${fileExtension}`);
  
  if (options.language) {
    formData.append('language', options.language);
  }
  
  if (options.sessionId) {
    formData.append('session_id', options.sessionId.toString());
  }
  
  if (options.speaker) {
    formData.append('speaker', options.speaker);
  }
  
  const response = await axiosInstance.post('/sessions/transcribe-audio', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
};
