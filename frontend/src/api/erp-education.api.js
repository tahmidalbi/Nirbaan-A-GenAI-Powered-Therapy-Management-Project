import axiosInstance from './axios';

/**
 * Get the cached ERP education for the current patient.
 * Returns null if no education has been generated yet.
 */
export const getMyERPEducation = async () => {
  try {
    const response = await axiosInstance.get('/education/erp/patient/my-education');
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      return null;
    }
    throw error.response?.data?.detail || 'Failed to fetch ERP education';
  }
};

/**
 * Generate (or return cached) ERP education for the current patient.
 * @param {boolean} regenerate - If true, forces fresh generation even if cache exists.
 */
export const generateERPEducation = async (regenerate = false) => {
  try {
    const response = await axiosInstance.post(
      `/education/erp/patient/generate?regenerate=${regenerate}`
    );
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to generate ERP education';
  }
};
