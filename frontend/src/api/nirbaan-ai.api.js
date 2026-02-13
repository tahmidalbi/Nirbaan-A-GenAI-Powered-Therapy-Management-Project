/**
 * Nirbaan AI API Client Functions
 * Handles all API calls related to AI protocol generation
 */
import axiosInstance from './axios';

/**
 * Generate a therapy protocol for a patient
 * 
 * @param {number} patientId - The patient's ID
 * @param {string|null} sessionFocus - Optional specific focus for the session
 * @param {boolean} useMock - Use mock endpoint for testing (default: false - use real LangGraph)
 * @returns {Promise<Object>} The generated protocol response
 */
export const generateProtocol = async (patientId, sessionFocus = null, useMock = false) => {
  try {
    const endpoint = useMock ? '/nirbaan-ai/generate-protocol-mock' : '/nirbaan-ai/generate-protocol';
    console.log(`[Nirbaan AI] Calling ${endpoint} for patient ${patientId}`);
    
    const payload = {
      patient_id: patientId,
      session_focus: sessionFocus
    };
    
    console.log('🔍🔍🔍 [API CLIENT] Payload being sent:', payload);
    console.log('🔍 [API CLIENT] patient_id type:', typeof patientId, 'value:', patientId);
    
    const response = await axiosInstance.post(endpoint, payload);
    console.log(`[Nirbaan AI] Response status: ${response.data.status}`);
    return response.data;
  } catch (error) {
    console.error('[Nirbaan AI] Error:', error.response?.data || error.message);
    throw error.response?.data?.detail || 'Failed to generate protocol';
  }
};

/**
 * Resume protocol generation after providing clarification answers
 * 
 * @param {string} threadId - The thread ID from the initial generation
 * @param {Object} answers - Answers to clarification questions
 * @returns {Promise<Object>} The resumed protocol response
 */
export const resumeAfterClarification = async (threadId, answers) => {
  try {
    const response = await axiosInstance.post('/nirbaan-ai/resume-clarification', {
      thread_id: threadId,
      answers: answers
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to resume protocol generation';
  }
};

/**
 * Get list of patients available for protocol generation
 * 
 * @returns {Promise<Object>} List of patients with session counts
 */
export const getPatientsForProtocol = async () => {
  try {
    const response = await axiosInstance.get('/nirbaan-ai/patients-for-protocol');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch patients';
  }
};
