import axiosInstance from './axios';

export const sendNirbaanAIMessage = async ({ message, thread_id }) => {
  const response = await axiosInstance.post('/patient/psychoeducation-chat/send', {
    message,
    thread_id: thread_id ?? null,
  });
  return response.data;
};

export const getNirbaanAIThread = async (threadId) => {
  const response = await axiosInstance.get(`/patient/psychoeducation-chat/threads/${threadId}`);
  return response.data;
};

export const listNirbaanAIThreads = async () => {
  const response = await axiosInstance.get('/patient/psychoeducation-chat/threads');
  return response.data;
};
