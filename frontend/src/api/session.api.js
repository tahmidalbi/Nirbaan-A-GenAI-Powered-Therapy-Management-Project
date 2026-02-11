/**
 * Session API Client Functions
 * Handles all API calls related to therapy session transcripts
 */
import axiosInstance from './axios';

/**
 * Therapist APIs
 */

// Create a new session
export const createSession = async (patientId, weekNumber, transcript, sessionDate = null) => {
  const response = await axiosInstance.post('/sessions/create', {
    patient_id: patientId,
    week_number: weekNumber,
    transcript: transcript,
    session_date: sessionDate
  });
  return response.data;
};

// Get all patients with sessions (for therapist sidebar)
export const getPatientsWithSessions = async () => {
  const response = await axiosInstance.get('/sessions/patients-with-sessions');
  return response.data;
};

// Get all sessions for a specific patient
export const getPatientSessions = async (patientId) => {
  const response = await axiosInstance.get(`/sessions/patient/${patientId}`);
  return response.data;
};

// Get specific session details
export const getSessionDetail = async (sessionId) => {
  const response = await axiosInstance.get(`/sessions/session/${sessionId}`);
  return response.data;
};

// Update session transcript
export const updateSession = async (sessionId, transcript) => {
  const response = await axiosInstance.put(`/sessions/session/${sessionId}`, {
    transcript: transcript
  });
  return response.data;
};

/**
 * Patient APIs
 */

// Get patient's own sessions
export const getMySessions = async () => {
  const response = await axiosInstance.get('/sessions/my-sessions');
  return response.data;
};
