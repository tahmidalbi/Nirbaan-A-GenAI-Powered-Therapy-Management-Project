import axiosInstance from './axios';

export const registerPatient = async (patientData) => {
  try {
    const response = await axiosInstance.post('/patients/register', patientData);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Patient registration failed';
  }
};

export const getPatients = async () => {
  try {
    const response = await axiosInstance.get('/patients/');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch patients';
  }
};

export const getPatient = async (patientId) => {
  try {
    const response = await axiosInstance.get(`/patients/${patientId}`);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch patient';
  }
};

export const updatePatient = async (patientId, patientData) => {
  try {
    const response = await axiosInstance.put(`/patients/${patientId}`, patientData);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to update patient';
  }
};

export const loginPatient = async (credentials) => {
  try {
    const response = await axiosInstance.post('/patients/login', credentials);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Patient login failed';
  }
};

export const getCurrentPatient = async () => {
  try {
    const response = await axiosInstance.get('/patients/me');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch patient data';
  }
};

// ── Invitation API ────────────────────────────────────────────────────────────

export const createPatientInvitation = async (invitedEmail = null) => {
  const response = await axiosInstance.post('/patients/invite', {
    invited_email: invitedEmail || null,
  });
  return response.data;
};

export const validateInvitation = async (token) => {
  const response = await axiosInstance.get(`/patients/invite/${token}`);
  return response.data;
};

export const registerViaInvitation = async (token, patientData) => {
  const response = await axiosInstance.post(`/patients/invite/${token}/register`, patientData);
  return response.data;
};

export const sendInviteEmail = async (token, recipientEmail) => {
  const response = await axiosInstance.post(`/patients/invite/${token}/send-email`, {
    recipient_email: recipientEmail,
  });
  return response.data;
};

