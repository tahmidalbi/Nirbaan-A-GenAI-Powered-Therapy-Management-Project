import axiosInstance from './axios';

/**
 * Get the OCD core education status + content for the current patient.
 * Returns 404 if generation has never been triggered.
 */
export const getMyOCDEducation = async () => {
  try {
    const response = await axiosInstance.get('/education/ocd-core/patient/my-education');
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      return null; // Not yet triggered
    }
    throw error.response?.data?.detail || 'Failed to fetch OCD education';
  }
};

/**
 * Trigger (or re-trigger) async Celery generation of OCD core education.
 * @param {boolean} regenerate - If true, forces a fresh generation even if already completed.
 * Returns immediately with { status, message } — content comes later via polling.
 */
export const triggerOCDEducationGeneration = async (regenerate = false) => {
  try {
    const response = await axiosInstance.post(
      `/education/ocd-core/patient/generate?regenerate=${regenerate}`
    );
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to trigger OCD education generation';
  }
};
