import axiosInstance from './axios';

/**
 * CRITICAL: 2-step upload flow for direct-to-R2 uploads
 * Step 1: init-upload → get presigned PUT URL
 * Step 2: PUT directly to R2 with file (R2 doesn't support POST!)  
 * Step 3: confirm-upload → trigger processing
 */

export const uploadResource = async (file, title) => {
  try {
    // Step 1: Initialize upload - get presigned R2 PUT URL
    const initResponse = await axiosInstance.post('/resources/init-upload', {
      title,
      filename: file.name,
      file_type: file.name.endsWith('.pdf') ? 'pdf' : 'txt',
      mime_type: file.type,
      size_bytes: file.size,
    });

    const { resource_id, upload_url } = initResponse.data;

    // Step 2: Upload file DIRECTLY to R2 using presigned PUT
    // R2 only supports PUT, not POST!
    const r2Response = await fetch(upload_url, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
      },
    });

    if (!r2Response.ok) {
      throw new Error(`R2 upload failed: ${r2Response.statusText}`);
    }

    // Step 3: Confirm upload - trigger backend processing
    const confirmResponse = await axiosInstance.post(
      `/resources/${resource_id}/confirm-upload`
    );

    return {
      resource_id,
      ...confirmResponse.data,
    };
  } catch (error) {
    throw error.response?.data?.detail || error.message || 'Upload failed';
  }
};

export const getResourceStatus = async (resourceId) => {
  try {
    const response = await axiosInstance.get(`/resources/${resourceId}/status`);
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch status';
  }
};

export const listResources = async () => {
  try {
    const response = await axiosInstance.get('/resources');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch resources';
  }
};

export const deleteResource = async (resourceId) => {
  try {
    await axiosInstance.delete(`/resources/${resourceId}`);
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to delete resource';
  }
};

export const searchKnowledgeBase = async (query, topK = 6) => {
  try {
    const response = await axiosInstance.post('/resources/rag/search', {
      query,
      top_k: topK,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Search failed';
  }
};

export const generateAnswer = async (query, topK = 6) => {
  try {
    const response = await axiosInstance.post('/resources/rag/answer', {
      query,
      top_k: topK,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to generate answer';
  }
};

export const uploadFromUrl = async (url, title, resourceType = 'webpage') => {
  try {
    const response = await axiosInstance.post('/resources/from-url', {
      url,
      title,
      resource_type: resourceType,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to add URL resource';
  }
};

// ============ PATIENT ENDPOINTS ============

export const listPatientResources = async () => {
  try {
    const response = await axiosInstance.get('/resources/patient');
    return response.data;
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch resources';
  }
};

export const getPatientResourceDownloadUrl = async (resourceId) => {
  try {
    const response = await axiosInstance.get(`/resources/patient/${resourceId}/download-url`);
    return response.data; // { resource_id, download_url, expires_in_seconds }
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to get download URL';
  }
};