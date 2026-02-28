import api from './axios';

// ==================== PATIENT ENDPOINTS ====================

/**
 * Create a new monitoring day
 */
export const createMonitoringDay = async (dayNumber) => {
  const response = await api.post('/api/self-monitoring/days', {
    day_number: dayNumber
  });
  return response.data;
};

/**
 * Get all monitoring days for current patient
 */
export const getMyMonitoringDays = async () => {
  const response = await api.get('/api/self-monitoring/days');
  return response.data;
};

/**
 * Get a specific monitoring day with all entries
 */
export const getMonitoringDay = async (dayId) => {
  const response = await api.get(`/api/self-monitoring/days/${dayId}`);
  return response.data;
};

/**
 * Add a new entry to a monitoring day
 */
export const createMonitoringEntry = async (dayId, entryData) => {
  const response = await api.post(`/api/self-monitoring/days/${dayId}/entries`, {
    date: entryData.date,
    time: entryData.time,
    event: entryData.event,
    ritual: entryData.ritual,
    time_spent: parseFloat(entryData.timeSpent),
    anxiety_level: parseInt(entryData.anxietyLevel)
  });
  return response.data;
};

/**
 * Delete a monitoring entry
 */
export const deleteMonitoringEntry = async (entryId) => {
  await api.delete(`/api/self-monitoring/entries/${entryId}`);
};

// ==================== THERAPIST ENDPOINTS ====================

/**
 * Get monitoring summary for all patients (Therapist only)
 */
export const getAllPatientsMonitoring = async () => {
  const response = await api.get('/api/self-monitoring/patients');
  return response.data;
};

/**
 * Get all monitoring days for a specific patient (Therapist only)
 */
export const getPatientMonitoringDays = async (patientId) => {
  const response = await api.get(`/api/self-monitoring/patients/${patientId}/days`);
  return response.data;
};

/**
 * Get a specific monitoring day for a patient (Therapist only)
 */
export const getPatientMonitoringDay = async (patientId, dayId) => {
  const response = await api.get(`/api/self-monitoring/patients/${patientId}/days/${dayId}`);
  return response.data;
};
