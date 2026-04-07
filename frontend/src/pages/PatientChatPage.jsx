import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  listChatGroupsPatient,
  getChatMessages,
  openChatSocket,
  getPatientEPSessions,
  getEPPatientSessionMessages,
  openEPPatientSocket,
  uploadMyPublicKey,
  getPeerPublicKey,
} from '../api/chat.api';
import { getOrCreateKeyPair, deriveSharedKey, encryptMsg, decryptMessageContent } from '../utils/epCrypto';
import './PatientChatPage.css';

export default function PatientChatPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);

  // Decode user ID directly from JWT — exact same value the backend writes as sender_id
  const myUserId = useMemo(() => {
    if (!token) return null;
    try { return JSON.parse(atob(token.split('.')[1])).id; } catch { return null; }
  }, [token]);

  const [groups, setGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState(null);

  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [wsStatus, setWsStatus] = useState('idle');

  // ── EP Direct Sessions state ──────────────────────────────────────────────
  const [epSessions, setEpSessions] = useState([]); // [{session_id, ep_id, ep_name}]
  const [selectedEpSession, setSelectedEpSession] = useState(null);
  const [epMessages, setEpMessages] = useState([]);
  const [epMessagesLoading, setEpMessagesLoading] = useState(false);
  const [epInputText, setEpInputText] = useState('');
  const [epWsStatus, setEpWsStatus] = useState('idle');
  // Tab: 'groups' | 'helpers'
  const [activeTab, setActiveTab] = useState('groups');

  const wsRef = useRef(null);
  const epWsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const epMessagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ── E2EE key material (EP-Patient chat only) ──────────────────────────────
  const patientKeyPairRef = useRef(null);   // { privateKey: CryptoKey, publicKeyJwk }
  const epSharedKeyRef = useRef(null);       // AES-GCM CryptoKey, one per session
  // ── Generate / load ECDH key pair on mount and upload public key ─────────
  useEffect(() => {
    getOrCreateKeyPair().then(async (kp) => {
      patientKeyPairRef.current = kp;
      try { await uploadMyPublicKey(kp.publicKeyJwk); } catch { /* silent */ }
    });
  }, []);
  // ── load groups ────────────────────────────────────────────────────────────
  useEffect(() => {
    listChatGroupsPatient()
      .then(setGroups)
      .catch(() => {})
      .finally(() => setGroupsLoading(false));
  }, []);

  // ── select group ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!selectedGroup) return;
    setMessages([]);
    setMessagesLoading(true);
    getChatMessages(selectedGroup.id)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setMessagesLoading(false));

    if (wsRef.current) wsRef.current.close();
    setWsStatus('connecting');
    const ws = openChatSocket(selectedGroup.id);
    wsRef.current = ws;

    ws.onopen = () => setWsStatus('open');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setMessages((prev) => [...prev, data]);
    };
    ws.onerror = () => setWsStatus('closed');
    ws.onclose = () => setWsStatus('closed');

    return () => ws.close();
  }, [selectedGroup?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    epMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [epMessages]);

  // ── Load EP sessions when tab switches to 'helpers' ───────────────────────
  useEffect(() => {
    if (activeTab !== 'helpers') return;
    getPatientEPSessions()
      .then(setEpSessions)
      .catch(() => {});
  }, [activeTab]);

  // ── Open WS for selected EP session ──────────────────────────────────────
  useEffect(() => {
    if (!selectedEpSession) return;
    if (epWsRef.current) { epWsRef.current.close(); epWsRef.current = null; }
    epSharedKeyRef.current = null;

    const run = async () => {
      // Derive shared AES key with EP (ECDH)
      if (patientKeyPairRef.current) {
        try {
          const peerJwk = await getPeerPublicKey(selectedEpSession.session_id);
          epSharedKeyRef.current = await deriveSharedKey(patientKeyPairRef.current.privateKey, peerJwk);
        } catch {
          epSharedKeyRef.current = null; // peer hasn't uploaded key yet — fallback to plain
        }
      }

      // Load + decrypt history
      setEpMessagesLoading(true);
      try {
        const msgs = await getEPPatientSessionMessages(selectedEpSession.session_id);
        const decrypted = await Promise.all(msgs.map((m) => decryptMessageContent(m, epSharedKeyRef.current)));
        setEpMessages(decrypted);
      } catch {
        setEpMessages([]);
      } finally {
        setEpMessagesLoading(false);
      }

      // Open WebSocket
      setEpWsStatus('connecting');
      const ws = openEPPatientSocket(selectedEpSession.session_id);
      epWsRef.current = ws;
      ws.onopen = () => setEpWsStatus('open');
      ws.onmessage = async (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'session_closed') {
          setEpSessions((prev) => prev.filter((s) => s.session_id !== selectedEpSession.session_id));
          setSelectedEpSession(null);
          setEpMessages([]);
          ws.close();
        } else {
          const decData = await decryptMessageContent(data, epSharedKeyRef.current);
          setEpMessages((prev) => [...prev, decData]);
        }
      };
      ws.onerror = () => setEpWsStatus('closed');
      ws.onclose = () => setEpWsStatus('closed');
    };

    run();

    return () => { if (epWsRef.current) { epWsRef.current.close(); epWsRef.current = null; } };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEpSession?.session_id]);

  // ── send message ──────────────────────────────────────────────────────────
  const handleSend = () => {
    const text = inputText.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ content: text }));
    setInputText('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── Send to EP — encrypts before sending ──────────────────────────────────
  const handleEpSend = async () => {
    const text = epInputText.trim();
    if (!text || !epWsRef.current || epWsRef.current.readyState !== WebSocket.OPEN) return;
    let content = text;
    if (epSharedKeyRef.current) {
      const encrypted = await encryptMsg(epSharedKeyRef.current, text);
      content = JSON.stringify(encrypted);
    }
    epWsRef.current.send(JSON.stringify({ content }));
    setEpInputText('');
  };

  const handleEpKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEpSend(); }
  };

  // ── per-sender unique color ───────────────────────────────────────────────
  const PEER_COLORS = [
    { bg: 'rgba(55, 48, 100, 0.82)',  border: 'rgba(99, 102, 241, 0.35)' },
    { bg: 'rgba(120, 60, 0, 0.82)',   border: 'rgba(251, 191, 36, 0.35)' },
    { bg: 'rgba(10, 70, 130, 0.82)',  border: 'rgba(59, 130, 246, 0.35)' },
    { bg: 'rgba(110, 20, 60, 0.82)',  border: 'rgba(236, 72, 153, 0.35)' },
    { bg: 'rgba(0, 90, 80, 0.82)',    border: 'rgba(20, 184, 166, 0.35)' },
    { bg: 'rgba(80, 40, 120, 0.82)',  border: 'rgba(168, 85, 247, 0.35)' },
    { bg: 'rgba(120, 90, 10, 0.80)',  border: 'rgba(234, 179, 8, 0.35)'  },
    { bg: 'rgba(20, 80, 100, 0.82)',  border: 'rgba(34, 211, 238, 0.35)' },
  ];

  const hashId = (id) =>
    String(id).split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);

  const getSenderStyle = (msg) => {
    const isMe = msg.sender_role === 'patient' && Number(msg.sender_id) === Number(myUserId);
    if (isMe) return {
      background: 'linear-gradient(135deg, rgba(34,120,60,0.92), rgba(20,90,48,0.96))',
      border: '1px solid rgba(52,168,83,0.4)',
      color: '#e8f5e9',
      borderBottomRightRadius: '3px',
      boxShadow: '0 2px 12px rgba(52,168,83,0.12)',
    };
    const c = PEER_COLORS[hashId(msg.sender_id) % PEER_COLORS.length];
    return {
      background: c.bg,
      border: `1px solid ${c.border}`,
      color: '#e8eaf6',
      borderBottomLeftRadius: '3px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.15)',
    };
  };

  const fmtTime = (ts) =>
    ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  const dotColor = wsStatus === 'open' ? '#4ade80' : wsStatus === 'connecting' ? '#fbbf24' : '#6b7280';

  return (
    <div className="pcp-root">
      <div className="pcp-bg-dots" />

      {/* ── Header ── */}
      <header className="pcp-header">
        <button className="pcp-back-btn" onClick={() => navigate('/patient/dashboard')}>
          ← Back
        </button>
        <div className="pcp-header-title">
          <span className="pcp-header-text">
            {activeTab === 'groups' ? 'Group Chat' : 'My Helpers'}
          </span>
          {activeTab === 'groups' && selectedGroup && (
            <span className="pcp-header-group">/ {selectedGroup.name}</span>
          )}
          {activeTab === 'helpers' && selectedEpSession && (
            <span className="pcp-header-group">/ {selectedEpSession.ep_name}</span>
          )}
        </div>
        <div className="pcp-header-right">
          {activeTab === 'groups' && selectedGroup && (
            <span className="pcp-ws-indicator" style={{ background: dotColor }} title={wsStatus} />
          )}
          {activeTab === 'helpers' && selectedEpSession && (
            <span className="pcp-ws-indicator"
              style={{ background: epWsStatus === 'open' ? '#4ade80' : epWsStatus === 'connecting' ? '#fbbf24' : '#6b7280' }}
              title={epWsStatus}
            />
          )}
        </div>
      </header>

      {/* ── Tab bar ── */}
      <div className="pcp-tab-bar">
        <button
          className={`pcp-tab-btn ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          Group Chat
        </button>
        <button
          className={`pcp-tab-btn ${activeTab === 'helpers' ? 'active' : ''}`}
          onClick={() => setActiveTab('helpers')}
        >
          My Helpers
          {epSessions.length > 0 && (
            <span className="pcp-tab-badge">{epSessions.length}</span>
          )}
        </button>
      </div>

      {/* ── Body ── */}
      <div className="pcp-body">
        {activeTab === 'groups' && (
          <>
        {/* ── Sidebar ── */}
        <aside className="pcp-sidebar">
          <div className="pcp-sidebar-top">
            <h3 className="pcp-sidebar-title">My Groups</h3>
          </div>

          {groupsLoading ? (
            <div className="pcp-sidebar-empty">Loading…</div>
          ) : groups.length === 0 ? (
            <div className="pcp-sidebar-empty">
              You haven&apos;t been added to any group yet.
              <br /><br />
              Ask your therapist to add you.
            </div>
          ) : (
            <ul className="pcp-group-list">
              {groups.map((g) => (
                <li
                  key={g.id}
                  className={`pcp-group-item ${selectedGroup?.id === g.id ? 'active' : ''}`}
                  onClick={() => setSelectedGroup(g)}
                >
                  <div className="pcp-group-dot" />
                  <div className="pcp-group-info">
                    <span className="pcp-group-name">{g.name}</span>
                    <span className="pcp-group-meta">
                      {g.member_count} member{g.member_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </aside>

        {/* ── Main ── */}
        {selectedGroup ? (
          <div className="pcp-main">
            <div className="pcp-messages">
              {messagesLoading && (
                <div className="pcp-loading-msg">
                  <span className="pcp-dots"><span/><span/><span/></span>
                  Loading messages…
                </div>
              )}

              {!messagesLoading && messages.length === 0 && (
                <div className="pcp-empty-msg">
                  <p>No messages yet. Be the first to say something!</p>
                </div>
              )}

              {messages.map((msg, idx) => {
                if (msg.type === 'system') {
                  return (
                    <div key={idx} className="pcp-system-msg">
                      <span className="pcp-system-line" />
                      <span className="pcp-system-text">{msg.content}</span>
                      <span className="pcp-system-line" />
                    </div>
                  );
                }

                const isMe = msg.sender_role === 'patient' && Number(msg.sender_id) === Number(myUserId);
                const bubbleStyle = getSenderStyle(msg);

                return (
                  <div key={msg.id || idx} className={`pcp-row ${isMe ? 'pcp-row-me' : ''}`}>
                    {!isMe && (
                      <div className="pcp-avatar pcp-avatar-other">
                        {(msg.sender_name || '?').charAt(0).toUpperCase()}
                      </div>
                    )}

                    <div className="pcp-bubble-wrap">
                      {!isMe && (
                        <div className="pcp-sender-meta">
                          <span className="pcp-sender-name">{msg.sender_name}</span>
                          {msg.sender_role === 'therapist' && (
                            <span className="pcp-therapist-tag">Therapist</span>
                          )}
                        </div>
                      )}
                      <div className="pcp-bubble" style={bubbleStyle}>
                        {msg.content}
                        <span className="pcp-time">{fmtTime(msg.created_at)}</span>
                      </div>
                    </div>

                    {isMe && (
                      <div className="pcp-avatar pcp-avatar-me">
                        {(user?.name || 'P').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <div className="pcp-input-bar">
              <textarea
                ref={inputRef}
                className="pcp-input"
                placeholder="Type a message… (Enter to send)"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <button
                className="pcp-send-btn"
                onClick={handleSend}
                disabled={!inputText.trim() || wsStatus !== 'open'}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>
        ) : (
          <div className="pcp-no-group">
            <h2>Select a group to chat</h2>
            <p>Your therapist has added you to group chats where you can connect with others.</p>
          </div>
        )}
          </>
        )}

        {/* ── My Helpers tab ── */}
        {activeTab === 'helpers' && (
          <div className="pcp-helpers-layout">
            {/* EP contact sidebar */}
            <aside className="pcp-sidebar">
              <div className="pcp-sidebar-top">
                <h3 className="pcp-sidebar-title">Active Helpers</h3>
              </div>
              {epSessions.length === 0 ? (
                <div className="pcp-sidebar-empty">
                  No human helper has started a chat with you yet.
                </div>
              ) : (
                <ul className="pcp-group-list">
                  {epSessions.map((s) => (
                    <li
                      key={s.session_id}
                      className={`pcp-group-item ${selectedEpSession?.session_id === s.session_id ? 'active' : ''}`}
                      onClick={() => setSelectedEpSession(s)}
                    >
                      <div className="pcp-group-dot" style={{ background: '#fbbf24' }} />
                      <div className="pcp-group-info">
                        <span className="pcp-group-name">{s.ep_name}</span>
                        <span className="pcp-group-meta">Human Helper</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </aside>

            {/* Chat panel */}
            {selectedEpSession ? (
              <div className="pcp-main">
                <div className="pcp-messages">
                  {epMessagesLoading && (
                    <div className="pcp-loading-msg">
                      <span className="pcp-dots"><span/><span/><span/></span>
                      Loading messages…
                    </div>
                  )}
                  {!epMessagesLoading && epMessages.length === 0 && (
                    <div className="pcp-empty-msg">
                      <p>{selectedEpSession.ep_name} has started a chat with you. Say hello!</p>
                    </div>
                  )}
                  {epMessages.map((msg, idx) => {
                    const isMe = msg.sender_role === 'patient';
                    const bubbleStyle = isMe
                      ? {
                          background: 'linear-gradient(135deg, rgba(34,120,60,0.92), rgba(20,90,48,0.96))',
                          border: '1px solid rgba(52,168,83,0.4)',
                          color: '#e8f5e9',
                          borderBottomRightRadius: '3px',
                        }
                      : {
                          background: 'linear-gradient(135deg, rgba(234,179,8,0.2), rgba(180,130,0,0.25))',
                          border: '1px solid rgba(234,179,8,0.35)',
                          color: '#fef3c7',
                          borderBottomLeftRadius: '3px',
                        };
                    return (
                      <div key={msg.id || idx} className={`pcp-row ${isMe ? 'pcp-row-me' : ''}`}>
                        {!isMe && (
                          <div className="pcp-avatar pcp-avatar-other"
                            style={{ background: 'linear-gradient(135deg,rgba(234,179,8,0.6),rgba(180,130,0,0.6))' }}>
                            {(msg.sender_name || 'H').charAt(0).toUpperCase()}
                          </div>
                        )}
                        <div className="pcp-bubble-wrap">
                          {!isMe && (
                            <div className="pcp-sender-meta">
                              <span className="pcp-sender-name">{msg.sender_name}</span>
                              <span className="pcp-therapist-tag" style={{ background: 'rgba(234,179,8,0.15)', color: '#fcd34d' }}>Helper</span>
                            </div>
                          )}
                          <div className="pcp-bubble" style={bubbleStyle}>
                            {msg.content}
                            <span className="pcp-time">{fmtTime(msg.created_at)}</span>
                          </div>
                        </div>
                        {isMe && (
                          <div className="pcp-avatar pcp-avatar-me">
                            {(user?.name || 'P').charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                    );
                  })}
                  <div ref={epMessagesEndRef} />
                </div>

                <div className="pcp-input-bar">
                  <textarea
                    className="pcp-input"
                    placeholder="Reply to your helper… (Enter to send)"
                    value={epInputText}
                    onChange={(e) => setEpInputText(e.target.value)}
                    onKeyDown={handleEpKeyDown}
                    rows={1}
                  />
                  <button
                    className="pcp-send-btn"
                    onClick={handleEpSend}
                    disabled={!epInputText.trim() || epWsStatus !== 'open'}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                    </svg>
                  </button>
                </div>
              </div>
            ) : (
              <div className="pcp-no-group">
                <h2>Select a helper to chat</h2>
                <p>Your human helpers will appear here when they start a conversation with you.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
