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
