import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  listChatGroupsPatient,
  getChatMessages,
  openChatSocket,
} from '../api/chat.api';
import './PatientChatPage.css';

export default function PatientChatPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  const [groups, setGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState(null);

  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [wsStatus, setWsStatus] = useState('idle');

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

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
    const isMe = msg.sender_role === 'patient' && msg.sender_id === user?.id;
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
          <span className="pcp-header-icon">💬</span>
          <span className="pcp-header-text">Group Chat</span>
          {selectedGroup && (
            <span className="pcp-header-group">/ {selectedGroup.name}</span>
          )}
        </div>
        <div className="pcp-header-right">
          {selectedGroup && (
            <span className="pcp-ws-indicator" style={{ background: dotColor }} title={wsStatus} />
          )}
        </div>
      </header>

      {/* ── Body ── */}
      <div className="pcp-body">
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
                  <span style={{ fontSize: '2.5rem', opacity: 0.4 }}>💬</span>
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

                const isMe = msg.sender_role === 'patient' && msg.sender_id === user?.id;
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
            <span className="pcp-no-group-icon">💬</span>
            <h2>Select a group to chat</h2>
            <p>Your therapist has added you to group chats where you can connect with others.</p>
          </div>
        )}
      </div>
    </div>
  );
}
