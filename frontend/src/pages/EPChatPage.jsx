import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  getMyTherapistForEP,
  getEPMessages,
  openEPChatSocket,
  getEPGroupAsEP,
  getEPGroupMessages,
  claimEPGroupMessage,
  openEPGroupSocket,
  getEPPatientsList,
  getOrCreateEPPatientSession,
  getEPPatientSessionMessages,
  closeEPPatientSession,
  openEPPatientSocket,
  uploadMyPublicKey,
  getPeerPublicKey,
} from '../api/chat.api';
import { getOrCreateKeyPair, deriveSharedKey, encryptMsg, decryptMessageContent } from '../utils/epCrypto';
import './EPChatPage.css';
import '../dashboards/PatientDashboard.css';

export default function EPChatPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);

  // Decode EP id from JWT — same value backend writes as sender_id
  const myUserId = useMemo(() => {
    if (!token) return null;
    try { return JSON.parse(atob(token.split('.')[1])).id; } catch { return null; }
  }, [token]);

  const initialTab = new URLSearchParams(location.search).get('tab') || 'direct';
  const [activeTab, setActiveTab] = useState(initialTab); // 'direct' | 'group' | 'patients'

  const [therapistInfo, setTherapistInfo] = useState(null); // { id, name, ep_id }
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  // ── Direct chat state ─────────────────────────────────────────────────────
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [wsStatus, setWsStatus] = useState('idle');

  // ── Group chat state ──────────────────────────────────────────────────────
  const [epGroupInfo, setEpGroupInfo] = useState(null);
  const [groupMessages, setGroupMessages] = useState([]);
  const [groupMessagesLoading, setGroupMessagesLoading] = useState(false);
  const [groupInputText, setGroupInputText] = useState('');
  const [groupWsStatus, setGroupWsStatus] = useState('idle');

  // ── Patients tab state ────────────────────────────────────────────────────
  const [patients, setPatients] = useState([]);
  const [patientsLoading, setPatientsLoading] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientSession, setPatientSession] = useState(null); // { id, ep_name, patient_name, … }
  const [patientMessages, setPatientMessages] = useState([]);
  const [patientMessagesLoading, setPatientMessagesLoading] = useState(false);
  const [patientInputText, setPatientInputText] = useState('');
  const [patientWsStatus, setPatientWsStatus] = useState('idle');
  const [closingSession, setClosingSession] = useState(false);

  const wsRef = useRef(null);
  const groupWsRef = useRef(null);
  const patientWsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const groupMessagesEndRef = useRef(null);
  const patientMessagesEndRef = useRef(null);

  // ── E2EE key material (EP-Patient chat only) ──────────────────────────────
  const epKeyPairRef = useRef(null);       // { privateKey: CryptoKey, publicKeyJwk }
  const patientSharedKeyRef = useRef(null); // AES-GCM CryptoKey, one per session

  // ── Generate / load ECDH key pair on mount and upload public key ─────────
  useEffect(() => {
    getOrCreateKeyPair().then(async (kp) => {
      epKeyPairRef.current = kp;
      try { await uploadMyPublicKey(kp.publicKeyJwk); } catch { /* silent */ }
    });
  }, []);

  // ── Load therapist info on mount ─────────────────────────────────────────
  useEffect(() => {
    getMyTherapistForEP()
      .then((info) => {
        setTherapistInfo(info);
      })
      .catch(() => setLoadError('Could not load therapist info.'))
      .finally(() => setLoading(false));
  }, []);

  // ── Once we have therapist info, load DM history + open WS ───────────────
  useEffect(() => {
    if (!therapistInfo) return;
    const epId = therapistInfo.ep_id;

    setMessagesLoading(true);
    getEPMessages(epId)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setMessagesLoading(false));

    setWsStatus('connecting');
    const ws = openEPChatSocket(epId);
    wsRef.current = ws;

    ws.onopen = () => setWsStatus('open');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setMessages((prev) => [...prev, data]);
    };
    ws.onerror = () => setWsStatus('closed');
    ws.onclose = () => setWsStatus('closed');

    return () => ws.close();
  }, [therapistInfo?.ep_id]);

  // ── Group chat: load when tab switches to 'group' ─────────────────────────
  useEffect(() => {
    if (activeTab !== 'group' || !therapistInfo) return;
    if (epGroupInfo) return; // already loaded
    getEPGroupAsEP()
      .then((info) => {
        setEpGroupInfo(info);
        setGroupMessagesLoading(true);
        return getEPGroupMessages(info.id);
      })
      .then(setGroupMessages)
      .catch(() => {})
      .finally(() => setGroupMessagesLoading(false));
  }, [activeTab, therapistInfo]);

  // ── Group WS: connect once group info is ready and tab is active ──────────
  useEffect(() => {
    if (!epGroupInfo || activeTab !== 'group') return;
    if (groupWsRef.current) groupWsRef.current.close();
    setGroupWsStatus('connecting');
    const ws = openEPGroupSocket(epGroupInfo.id);
    groupWsRef.current = ws;
    ws.onopen = () => setGroupWsStatus('open');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'claim_update') {
        setGroupMessages((prev) => prev.map((m) => (m.id === data.id ? data : m)));
      } else {
        setGroupMessages((prev) => [...prev, data]);
      }
    };
    ws.onerror = () => setGroupWsStatus('closed');
    ws.onclose = () => setGroupWsStatus('closed');
    return () => ws.close();
  }, [epGroupInfo?.id, activeTab]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    groupMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [groupMessages]);

  useEffect(() => {
    patientMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [patientMessages]);

  // ── Patients tab: load list when tab becomes active ───────────────────────
  useEffect(() => {
    if (activeTab !== 'patients') return;
    setPatientsLoading(true);
    getEPPatientsList()
      .then(setPatients)
      .catch(() => {})
      .finally(() => setPatientsLoading(false));
  }, [activeTab]);

  // ── Open session when a patient is selected ───────────────────────────────
  useEffect(() => {
    if (!selectedPatient) return;

    if (patientWsRef.current) { patientWsRef.current.close(); patientWsRef.current = null; }
    patientSharedKeyRef.current = null;

    const run = async () => {
      // Get or create session
      let sess;
      try {
        sess = selectedPatient.active_session_id
          ? { id: selectedPatient.active_session_id, patient_name: selectedPatient.name, ep_name: user?.name || 'Helper' }
          : await getOrCreateEPPatientSession(selectedPatient.id);
      } catch {
        setPatientMessagesLoading(false);
        return;
      }
      setPatientSession(sess);

      // Derive shared AES key with patient (ECDH)
      if (epKeyPairRef.current) {
        try {
          const peerJwk = await getPeerPublicKey(sess.id);
          patientSharedKeyRef.current = await deriveSharedKey(epKeyPairRef.current.privateKey, peerJwk);
        } catch {
          patientSharedKeyRef.current = null; // peer hasn't uploaded key yet — fallback to plain
        }
      }

      // Load + decrypt history
      setPatientMessagesLoading(true);
      try {
        const msgs = await getEPPatientSessionMessages(sess.id);
        const decrypted = await Promise.all(msgs.map((m) => decryptMessageContent(m, patientSharedKeyRef.current)));
        setPatientMessages(decrypted);
      } catch {
        setPatientMessages([]);
      } finally {
        setPatientMessagesLoading(false);
      }

      // Open WebSocket
      setPatientWsStatus('connecting');
      const ws = openEPPatientSocket(sess.id);
      patientWsRef.current = ws;
      ws.onopen = () => setPatientWsStatus('open');
      ws.onmessage = async (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'session_closed') {
          setPatientSession(null);
          setPatientMessages([]);
          setSelectedPatient(null);
          ws.close();
        } else {
          const decData = await decryptMessageContent(data, patientSharedKeyRef.current);
          setPatientMessages((prev) => [...prev, decData]);
        }
      };
      ws.onerror = () => setPatientWsStatus('closed');
      ws.onclose = () => setPatientWsStatus('closed');
    };

    run();

    return () => {
      if (patientWsRef.current) { patientWsRef.current.close(); patientWsRef.current = null; }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPatient?.id]);

  // ── Send (direct) ─────────────────────────────────────────────────────────
  const handleSend = () => {
    const text = inputText.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ content: text }));
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── Send (group) ──────────────────────────────────────────────────────────
  const handleGroupSend = () => {
    const text = groupInputText.trim();
    if (!text || !groupWsRef.current || groupWsRef.current.readyState !== WebSocket.OPEN) return;
    groupWsRef.current.send(JSON.stringify({ content: text }));
    setGroupInputText('');
  };

  const handleGroupKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleGroupSend(); }
  };

  // ── Claim a message ───────────────────────────────────────────────────────
  const handleClaim = async (msg) => {
    if (!epGroupInfo || msg.is_claimed) return;
    try {
      await claimEPGroupMessage(epGroupInfo.id, msg.id);
      // WS broadcast will update local state
    } catch { /* silent */ }
  };

  // ── Send (patient session) — encrypts before sending ─────────────────────
  const handlePatientSend = async () => {
    const text = patientInputText.trim();
    if (!text || !patientWsRef.current || patientWsRef.current.readyState !== WebSocket.OPEN) return;
    let content = text;
    if (patientSharedKeyRef.current) {
      const encrypted = await encryptMsg(patientSharedKeyRef.current, text);
      content = JSON.stringify(encrypted);
    }
    patientWsRef.current.send(JSON.stringify({ content }));
    setPatientInputText('');
  };

  const handlePatientKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handlePatientSend(); }
  };

  // ── Close patient session ─────────────────────────────────────────────────
  const handleCloseSession = async () => {
    if (!patientSession || closingSession) return;
    if (!window.confirm(`Close chat with ${patientSession.patient_name || selectedPatient?.name}? All messages will be deleted.`)) return;
    setClosingSession(true);
    try {
      await closeEPPatientSession(patientSession.id);
      if (patientWsRef.current) { patientWsRef.current.close(); patientWsRef.current = null; }
      setPatientSession(null);
      setPatientMessages([]);
      setSelectedPatient(null);
      // Refresh patient list so active_session_id is cleared
      getEPPatientsList().then(setPatients).catch(() => {});
    } catch { /* silent */ }
    finally { setClosingSession(false); }
  };

  // ── Styling helpers ───────────────────────────────────────────────────────
  const fmtTime = (ts) =>
    ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  const dotColor = wsStatus === 'open' ? '#4ade80' : wsStatus === 'connecting' ? '#fbbf24' : '#6b7280';

  const getMeBubbleStyle = () => ({
    background: 'linear-gradient(135deg, rgba(34,120,100,0.92), rgba(20,90,75,0.96))',
    border: '1px solid rgba(90,184,154,0.4)',
    color: '#e8f5e9',
    borderBottomRightRadius: '3px',
    boxShadow: '0 2px 12px rgba(90,184,154,0.12)',
  });

  const getThemBubbleStyle = () => ({
    background: 'linear-gradient(135deg, rgba(59,100,180,0.75), rgba(40,70,150,0.80))',
    border: '1px solid rgba(99,130,246,0.35)',
    color: '#e0e7ff',
    borderBottomLeftRadius: '3px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.15)',
  });

  // Use therapistInfo.ep_id — exact same ID the backend writes as sender_id
  const isMe = (msg) =>
    msg.sender_role === 'emergency_personnel' &&
    Number(msg.sender_id) === Number(therapistInfo?.ep_id);

  // For group messages, use JWT-decoded myUserId
  const isGroupMe = (msg) =>
    msg.sender_role === 'emergency_personnel' &&
    Number(msg.sender_id) === Number(myUserId);

  return (
    <div className="ecp-root">
      <div className="ecp-bg-dots" />

      {/* ── Header ── */}
      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>
                {activeTab === 'direct' ? 'Chat with Your Therapist'
                  : activeTab === 'group' ? 'Human Helper Group'
                  : 'Patient Chats'}
              </span>
            </div>
            {therapistInfo && activeTab === 'direct' && (
              <div className="pd-brand-breadcrumb">
                <span className="pd-brand-sep">&rsaquo;</span>
                <span>{therapistInfo.name}</span>
              </div>
            )}
            {activeTab === 'patients' && selectedPatient && (
              <div className="pd-brand-breadcrumb">
                <span className="pd-brand-sep">&rsaquo;</span>
                <span>{selectedPatient.name}</span>
              </div>
            )}
          </div>
          <div className="pd-header-actions">
            <span className="ecp-ws-dot"
              style={{ background: activeTab === 'direct'
                ? (wsStatus === 'open' ? '#4ade80' : wsStatus === 'connecting' ? '#fbbf24' : '#6b7280')
                : activeTab === 'group'
                ? (groupWsStatus === 'open' ? '#4ade80' : groupWsStatus === 'connecting' ? '#fbbf24' : '#6b7280')
                : (patientWsStatus === 'open' ? '#4ade80' : patientWsStatus === 'connecting' ? '#fbbf24' : '#6b7280')
              }}
            />
            <button className="pd-back-btn" onClick={() => navigate('/emergency-personnel/dashboard')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
          </div>
        </div>
      </header>

      {/* ── Tab bar ── */}
      <div className="ecp-tab-bar">
        <button
          className={`ecp-tab-btn ${activeTab === 'direct' ? 'active' : ''}`}
          onClick={() => setActiveTab('direct')}
        >
          Direct Message
        </button>
        <button
          className={`ecp-tab-btn ${activeTab === 'group' ? 'active' : ''}`}
          onClick={() => setActiveTab('group')}
        >
          Group Chat
        </button>
        <button
          className={`ecp-tab-btn ${activeTab === 'patients' ? 'active' : ''}`}
          onClick={() => setActiveTab('patients')}
        >
          Patients
        </button>
      </div>

      {/* ── Body ── */}
      <div className="ecp-body">
        {loading && (
          <div className="ecp-center">
            <div className="ecp-spinner" />
            <p>Connecting to your therapist…</p>
          </div>
        )}

        {!loading && loadError && (
          <div className="ecp-center">
            <p className="ecp-error">{loadError}</p>
          </div>
        )}

        {!loading && !loadError && therapistInfo && activeTab === 'direct' && (
          <div className="ecp-main">
            {/* Therapist info banner */}
            <div className="ecp-therapist-banner">
              <div className="ecp-therapist-avatar">
                {therapistInfo.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="ecp-therapist-name">{therapistInfo.name}</div>
                <div className="ecp-therapist-role">Your Therapist</div>
              </div>
              <div className="ecp-status-pill" style={{ background: wsStatus === 'open' ? 'rgba(74,222,128,0.15)' : 'rgba(107,114,128,0.15)', borderColor: wsStatus === 'open' ? 'rgba(74,222,128,0.4)' : 'rgba(107,114,128,0.3)', color: wsStatus === 'open' ? '#4ade80' : '#9ca3af' }}>
                {wsStatus === 'open' ? '● Online' : wsStatus === 'connecting' ? '◌ Connecting…' : '○ Offline'}
              </div>
            </div>

            {/* Messages */}
            <div className="ecp-messages">
              {messagesLoading && (
                <div className="ecp-loading-msg">
                  <span className="ecp-dots"><span/><span/><span/></span>
                  Loading messages…
                </div>
              )}

              {!messagesLoading && messages.length === 0 && (
                <div className="ecp-empty-msg">
                  <p>No messages yet. Say hello to your therapist!</p>
                </div>
              )}

              {messages.map((msg, idx) => {
                const mine = isMe(msg);
                const bubbleStyle = mine ? getMeBubbleStyle() : getThemBubbleStyle();
                return (
                  <div key={msg.id || idx} className={`ecp-row ${mine ? 'ecp-row-me' : ''}`}>
                    {!mine && (
                      <div className="ecp-avatar ecp-avatar-therapist">
                        {(msg.sender_name || 'T').charAt(0).toUpperCase()}
                      </div>
                    )}

                    <div className="ecp-bubble-wrap">
                      {!mine && (
                        <div className="ecp-sender-name">{msg.sender_name}</div>
                      )}
                      <div className="ecp-bubble" style={bubbleStyle}>
                        {msg.content}
                        <span className="ecp-time">{fmtTime(msg.created_at)}</span>
                      </div>
                    </div>

                    {mine && (
                      <div className="ecp-avatar ecp-avatar-me">
                        {(user?.name || 'H').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Input bar */}
            <div className="ecp-input-bar">
              <textarea
                className="ecp-input"
                placeholder="Type a message… (Enter to send)"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <button
                className="ecp-send-btn"
                onClick={handleSend}
                disabled={!inputText.trim() || wsStatus !== 'open'}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* ── Group Chat tab ── */}
        {!loading && !loadError && therapistInfo && activeTab === 'group' && (
          <div className="ecp-main">
            <div className="ecp-messages">
              {groupMessagesLoading && (
                <div className="ecp-loading-msg">
                  <span className="ecp-dots"><span/><span/><span/></span>
                  Loading messages…
                </div>
              )}
              {!groupMessagesLoading && groupMessages.length === 0 && (
                <div className="ecp-empty-msg">
                  <p>No messages yet. The AI agent will post patient alerts here for the group to act on.</p>
                </div>
              )}
              {groupMessages.map((msg, idx) => {
                const mine = isGroupMe(msg);
                const isAI = msg.sender_role === 'ai_agent' || msg.sender_role === 'system';
                const bubbleStyle = mine
                  ? getMeBubbleStyle()
                  : isAI
                    ? { background: 'rgba(80,40,120,0.85)', border: '1px solid rgba(168,85,247,0.4)', color: '#e0e7ff', borderBottomLeftRadius: '3px' }
                    : getThemBubbleStyle();
                return (
                  <div key={msg.id || idx} className={`ecp-row ${mine ? 'ecp-row-me' : ''}`}>
                    {!mine && (
                      <div className="ecp-avatar ecp-avatar-therapist"
                        style={isAI ? { background: 'linear-gradient(135deg,#6d28d9,#4c1d95)' } : {}}>
                        {isAI ? 'AI' : (msg.sender_name || '?').charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="ecp-bubble-wrap">
                      {!mine && (
                        <div className="ecp-sender-name">
                          {msg.sender_name}
                          {isAI && <span className="ecp-ai-tag">AI</span>}
                        </div>
                      )}
                      <div className="ecp-bubble" style={bubbleStyle}>
                        {msg.patient_name && (
                          <div className="ecp-patient-ref">
                            Patient: <strong>{msg.patient_name}</strong>
                          </div>
                        )}
                        {msg.content}
                        {msg.is_claimed && (
                          <div className="ecp-claim-badge">
                            Being visited by <strong>{msg.claimed_by_name}</strong>
                          </div>
                        )}
                        {!msg.is_claimed && (msg.sender_role === 'ai_agent' || msg.patient_name) && !mine && (
                          <button
                            className="ecp-claim-btn"
                            onClick={() => handleClaim(msg)}
                          >
                            I'm Visiting This Patient
                          </button>
                        )}
                        <span className="ecp-time">{fmtTime(msg.created_at)}</span>
                      </div>
                    </div>
                    {mine && (
                      <div className="ecp-avatar ecp-avatar-me">
                        {(user?.name || 'H').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={groupMessagesEndRef} />
            </div>

            <div className="ecp-input-bar">
              <textarea
                className="ecp-input"
                placeholder="Send a message to the group… (Enter to send)"
                value={groupInputText}
                onChange={(e) => setGroupInputText(e.target.value)}
                onKeyDown={handleGroupKeyDown}
                rows={1}
              />
              <button
                className="ecp-send-btn"
                onClick={handleGroupSend}
                disabled={!groupInputText.trim() || groupWsStatus !== 'open'}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* ── Patients tab ── */}
        {!loading && !loadError && activeTab === 'patients' && (
          <div className="ecp-patients-layout">
            {/* Patient list sidebar */}
            <aside className="ecp-patients-sidebar">
              <div className="ecp-patients-sidebar-title">Therapist's Patients</div>
              {patientsLoading ? (
                <div className="ecp-patients-empty">Loading…</div>
              ) : patients.length === 0 ? (
                <div className="ecp-patients-empty">No patients found.</div>
              ) : (
                <ul className="ecp-patients-list">
                  {patients.map((p) => (
                    <li
                      key={p.id}
                      className={`ecp-patients-item ${selectedPatient?.id === p.id ? 'active' : ''}`}
                      onClick={() => setSelectedPatient(p)}
                    >
                      <div className="ecp-patients-avatar">
                        {p.name.charAt(0).toUpperCase()}
                      </div>
                      <div className="ecp-patients-info">
                        <span className="ecp-patients-name">{p.name}</span>
                        <span className="ecp-patients-cond">{p.conditions}</span>
                      </div>
                      {p.active_session_id && (
                        <span className="ecp-patients-active-dot" title="Active chat" />
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </aside>

            {/* Chat panel */}
            {selectedPatient && patientSession ? (
              <div className="ecp-main ecp-patients-main">
                {/* Session header */}
                <div className="ecp-patient-session-header">
                  <div className="ecp-therapist-avatar">
                    {selectedPatient.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="ecp-therapist-name">{selectedPatient.name}</div>
                    <div className="ecp-therapist-role">Patient — {selectedPatient.conditions}</div>
                  </div>
                  <button
                    className="ecp-close-session-btn"
                    onClick={handleCloseSession}
                    disabled={closingSession}
                  >
                    {closingSession ? 'Closing…' : '✕ Close Session'}
                  </button>
                </div>

                {/* Messages */}
                <div className="ecp-messages">
                  {patientMessagesLoading && (
                    <div className="ecp-loading-msg">
                      <span className="ecp-dots"><span/><span/><span/></span>
                      Loading messages…
                    </div>
                  )}
                  {!patientMessagesLoading && patientMessages.length === 0 && (
                    <div className="ecp-empty-msg">
                      <p>Session started. Say hello to {selectedPatient.name}!</p>
                    </div>
                  )}
                  {patientMessages.map((msg, idx) => {
                    const mine = msg.sender_role === 'ep';
                    const bubbleStyle = mine ? getMeBubbleStyle() : getThemBubbleStyle();
                    return (
                      <div key={msg.id || idx} className={`ecp-row ${mine ? 'ecp-row-me' : ''}`}>
                        {!mine && (
                          <div className="ecp-avatar ecp-avatar-therapist">
                            {(msg.sender_name || 'P').charAt(0).toUpperCase()}
                          </div>
                        )}
                        <div className="ecp-bubble-wrap">
                          {!mine && <div className="ecp-sender-name">{msg.sender_name}</div>}
                          <div className="ecp-bubble" style={bubbleStyle}>
                            {msg.content}
                            <span className="ecp-time">{fmtTime(msg.created_at)}</span>
                          </div>
                        </div>
                        {mine && (
                          <div className="ecp-avatar ecp-avatar-me">
                            {(user?.name || 'H').charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                    );
                  })}
                  <div ref={patientMessagesEndRef} />
                </div>

                {/* Input */}
                <div className="ecp-input-bar">
                  <textarea
                    className="ecp-input"
                    placeholder="Message patient… (Enter to send)"
                    value={patientInputText}
                    onChange={(e) => setPatientInputText(e.target.value)}
                    onKeyDown={handlePatientKeyDown}
                    rows={1}
                  />
                  <button
                    className="ecp-send-btn"
                    onClick={handlePatientSend}
                    disabled={!patientInputText.trim() || patientWsStatus !== 'open'}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                    </svg>
                  </button>
                </div>
              </div>
            ) : selectedPatient ? (
              <div className="ecp-no-group">
                <div className="ecp-spinner" />
                <p>Opening session with {selectedPatient.name}…</p>
              </div>
            ) : (
              <div className="ecp-no-group">
                <p>Select a patient to start a direct chat.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
