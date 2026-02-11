import axios from './axios';

export const createInitialCondition = async (initialCondition) => {
  const response = await axios.post('/progress/initial-condition', { 
    initial_condition: initialCondition 
  });
  return response.data;
};

export const addWeeklyProgress = async (weekNumber, progressText) => {
  const response = await axios.post('/progress/weekly-progress', {
    week_number: weekNumber,
    progress_text: progressText
  });
  return response.data;
};

export const updateProgress = async (weekNumber, progressText) => {
  const response = await axios.put('/progress/update-progress', {
    week_number: weekNumber,
    progress_text: progressText
  });
  return response.data;
};

export const getMyProgress = async () => {
  const response = await axios.get('/progress/my-progress');
  return response.data;
};

export const getAllPatientsProgress = async () => {
  const response = await axios.get('/progress/patients');
  return response.data;
};

export const getPatientProgress = async (patientId) => {
  const response = await axios.get(`/progress/patient/${patientId}`);
  return response.data;
};

export const createOrUpdateTherapistNote = async (patientId, weekKey, noteText) => {
  const response = await axios.post('/progress/therapist-note', {
    patient_id: patientId,
    week_key: weekKey,
    note_text: noteText
  });
  return response.data;
};

export const updateAIProtocol = async (patientId, aiProtocolInstruction) => {
  const response = await axios.post('/progress/ai-protocol', {
    patient_id: patientId,
    ai_protocol_instruction: aiProtocolInstruction
  });
  return response.data;
};
