import axiosInstance from './axios';

/**
 * Get the cached education content for the current patient
 * Returns 404 if no education has been generated yet
 */
export const getMyEducation = async () => {
  try {
    const response = await axiosInstance.get('/education/fear-ladder/patient/my-education');
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      return null; // No education generated yet
    }
    throw error.response?.data?.detail || 'Failed to fetch education';
  }
};

/**
 * Generate or get existing education for the current patient
 * @param {boolean} regenerate - If true, generates new education even if cache exists
 */
export const generateEducation = async (regenerate = false) => {
  try {
    const response = await axiosInstance.post(
      `/education/fear-ladder/patient/generate?regenerate=${regenerate}`
    );
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to generate education';
  }
};

/**
 * Therapist preview endpoint (for testing)
 */
export const previewEducation = async () => {
  try {
    const response = await axiosInstance.get('/education/fear-ladder/therapist/preview');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to preview education';
  }
};
