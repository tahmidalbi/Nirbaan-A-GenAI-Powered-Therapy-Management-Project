import axiosInstance from './axios';

const BASE = '/chat';

function getToken() {
  const authStorage = localStorage.getItem('auth-storage');
  if (!authStorage) return null;
  const { state } = JSON.parse(authStorage);
  return state?.token || null;
}

// ─── Groups ────────────────────────────────────────────────

export async function createChatGroup(name) {
  const token = getToken();
  const res = await axiosInstance.post(`${BASE}/groups?token=${token}`, { name });
  return res.data;
}

export async function listChatGroupsTherapist() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/groups?token=${token}`);
  return res.data;
}

export async function deleteChatGroup(groupId) {
  const token = getToken();
  await axiosInstance.delete(`${BASE}/groups/${groupId}?token=${token}`);
}

// ─── Members ───────────────────────────────────────────────

export async function addGroupMember(groupId, patientId) {
  const token = getToken();
  const res = await axiosInstance.post(
    `${BASE}/groups/${groupId}/members?token=${token}`,
    { patient_id: patientId }
  );
  return res.data;
}

export async function removeGroupMember(groupId, patientId) {
  const token = getToken();
  await axiosInstance.delete(
    `${BASE}/groups/${groupId}/members/${patientId}?token=${token}`
  );
}

export async function listGroupMembers(groupId) {
  const token = getToken();
  const res = await axiosInstance.get(
    `${BASE}/groups/${groupId}/members?token=${token}`
  );
  return res.data;
}

// ─── Patient groups ────────────────────────────────────────

export async function listChatGroupsPatient() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/groups/patient/mine?token=${token}`);
  return res.data;
}

// ─── Messages ──────────────────────────────────────────────

export async function getChatMessages(groupId) {
  const token = getToken();
  const res = await axiosInstance.get(
    `${BASE}/groups/${groupId}/messages?token=${token}&limit=200`
  );
  return res.data;
}

// ─── WebSocket helper ──────────────────────────────────────

export function openChatSocket(groupId) {
  const token = getToken();
  return new WebSocket(`ws://127.0.0.1:8000/chat/ws/${groupId}?token=${token}`);
}

// ─── EP (Emergency Personnel) Direct Chat ─────────────────

export async function listEPContacts() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep/contacts?token=${token}`);
  return res.data;
}

export async function getMyTherapistForEP() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep/my-therapist?token=${token}`);
  return res.data;
}

export async function getEPMessages(epId) {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep/messages/${epId}?token=${token}`);
  return res.data;
}

export function openEPChatSocket(epId) {
  const token = getToken();
  return new WebSocket(`ws://127.0.0.1:8000/chat/ep/ws/${epId}?token=${token}`);
}

// ─── EP Group Chat (shared group for all human helpers of a therapist) ────────

export async function getTherapistEPGroup() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep-group/my-group?token=${token}`);
  return res.data;
}

export async function getEPGroupAsEP() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep-group/mine?token=${token}`);
  return res.data;
}

export async function getEPGroupMessages(groupId) {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep-group/${groupId}/messages?token=${token}&limit=200`);
  return res.data;
}

export async function claimEPGroupMessage(groupId, messageId) {
  const token = getToken();
  const res = await axiosInstance.post(
    `${BASE}/ep-group/${groupId}/messages/${messageId}/claim?token=${token}`
  );
  return res.data;
}

export function openEPGroupSocket(groupId) {
  const token = getToken();
  return new WebSocket(`ws://127.0.0.1:8000/chat/ep-group/ws/${groupId}?token=${token}`);
}

// ─── EP-Patient Direct Chat ────────────────────────────────

/** EP: list all patients belonging to their therapist */
export async function getEPPatientsList() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep-patient/patients?token=${token}`);
  return res.data;
}

/** EP: open (or resume) a direct session with a patient */
export async function getOrCreateEPPatientSession(patientId) {
  const token = getToken();
  const res = await axiosInstance.post(`${BASE}/ep-patient/session/${patientId}?token=${token}`);
  return res.data;
}

/** EP or patient: fetch messages for a session */
export async function getEPPatientSessionMessages(sessionId) {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep-patient/session/${sessionId}/messages?token=${token}`);
  return res.data;
}

/** EP: close the session (deletes messages, patient loses access) */
export async function closeEPPatientSession(sessionId) {
  const token = getToken();
  const res = await axiosInstance.post(`${BASE}/ep-patient/session/${sessionId}/close?token=${token}`);
  return res.data;
}

/** Patient: see all EPs with active sessions */
export async function getPatientEPSessions() {
  const token = getToken();
  const res = await axiosInstance.get(`${BASE}/ep-patient/my-sessions?token=${token}`);
  return res.data;
}

/** WS for a session (used by both EP and patient) */
export function openEPPatientSocket(sessionId) {
  const token = getToken();
  return new WebSocket(`ws://127.0.0.1:8000/chat/ep-patient/ws/${sessionId}?token=${token}`);
}
