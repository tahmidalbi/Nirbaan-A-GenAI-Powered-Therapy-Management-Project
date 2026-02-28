import axios from './axios';

/**
 * Create a new patient intake
 */
export const createIntake = async (intakeData) => {
    try {
        const response = await axios.post('/api/intakes', intakeData);
        return response.data;
    } catch (error) {
        throw error.response?.data?.detail || 'Failed to create intake';
    }
};

/**
 * Get current patient's intake
 */
export const getMyIntake = async () => {
    try {
        const response = await axios.get('/api/intakes/me');
        return response.data;
    } catch (error) {
        throw error.response?.data?.detail || 'Failed to get intake';
    }
};

/**
 * Update current patient's intake
 */
export const updateMyIntake = async (intakeData) => {
    try {
        const response = await axios.put('/api/intakes/me', intakeData);
        return response.data;
    } catch (error) {
        throw error.response?.data?.detail || 'Failed to update intake';
    }
};

/**
 * Get intake for a specific patient (Therapist only)
 */
export const getPatientIntake = async (patientId) => {
    try {
        const response = await axios.get(`/api/intakes/patient/${patientId}`);
        return response.data;
    } catch (error) {
        throw error.response?.data?.detail || 'Failed to get patient intake';
    }
};

/**
 * Get all intakes for therapist's patients
 */
export const getMyPatientsIntakes = async () => {
    try {
        const response = await axios.get('/api/intakes/my-patients');
        return response.data;
    } catch (error) {
        throw error.response?.data?.detail || 'Failed to get patients intakes';
    }
};
