import axiosInstance from './axios';

// ── Send a message to NirbaanAI (therapist side) ──────────────────────────
// POST /therapist/ai-chat/send
// Returns: TherapistChatSendResponse
//   { thread_id, user_message, assistant_message, needs_clarification, clarification, analysis_run }
export const sendTherapistAIMessage = async ({ message, patient_id, thread_id }) => {
  const response = await axiosInstance.post('/therapist/ai-chat/send', {
    message,
    patient_id,
    thread_id: thread_id ?? null,
  });
  return response.data;
};

// ── Submit clarification answer and resume graph ──────────────────────────
// POST /therapist/ai-chat/analysis-runs/{analysis_run_id}/clarification
// Returns: ResumePatientAnalysisResponse
//   { run, needs_clarification, clarification, analysis_summary }
export const submitTherapistClarificationAnswer = async ({ analysisRunId, answer }) => {
  const response = await axiosInstance.post(
    `/therapist/ai-chat/analysis-runs/${analysisRunId}/clarification`,
    { answer },
  );
  return response.data;
};

// ── Fetch a single thread (with all messages) ─────────────────────────────
// GET /therapist/ai-chat/threads/{thread_id}
// Returns: { thread, messages }
export const getTherapistAIThread = async (threadId) => {
  const response = await axiosInstance.get(`/therapist/ai-chat/threads/${threadId}`);
  return response.data;
};

// ── List all threads for this therapist ───────────────────────────────────
// GET /therapist/ai-chat/threads
// Returns: TherapistAIChatThreadOut[]
export const listTherapistAIThreads = async () => {
  const response = await axiosInstance.get('/therapist/ai-chat/threads');
  return response.data;
};
