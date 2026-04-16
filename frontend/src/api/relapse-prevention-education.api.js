import axiosInstance from './axios';

/**
 * Get cached relapse prevention education for the current patient.
 * Returns null if none has been generated yet.
 */
export const getMyEducation = async () => {
  try {
    const response = await axiosInstance.get('/education/relapse-prevention/patient/my-education');
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      return null;
    }
    throw error.response?.data?.detail || 'Failed to fetch education';
  }
};

/**
 * Generate (or return cached) relapse prevention education for the current patient.
 * @param {boolean} regenerate - If true, always generates fresh content.
 */
export const generateEducation = async (regenerate = false) => {
  try {
    const response = await axiosInstance.post(
      `/education/relapse-prevention/patient/generate?regenerate=${regenerate}`
    );
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to generate education';
  }
};
