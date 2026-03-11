import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getMyTherapistForEP, getEPMessages, openEPChatSocket } from '../api/chat.api';
import './EPChatPage.css';

export default function EPChatPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  const [therapistInfo, setTherapistInfo] = useState(null); // { id, name, ep_id }
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [wsStatus, setWsStatus] = useState('idle');

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ── Load therapist info on mount ─────────────────────────────────────────
  useEffect(() => {
    getMyTherapistForEP()
      .then((info) => {
        setTherapistInfo(info);
      })
      .catch(() => setLoadError('Could not load therapist info.'))
      .finally(() => setLoading(false));
  }, []);

  // ── Once we have therapist info, load history + open WS ──────────────────
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Send ─────────────────────────────────────────────────────────────────
  const handleSend = () => {
    const text = inputText.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ content: text }));
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── Styling helpers ───────────────────────────────────────────────────────
  const fmtTime = (ts) =>
    ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  const dotColor = wsStatus === 'open' ? '#4ade80' : wsStatus === 'connecting' ? '#fbbf24' : '#6b7280';

  const getMeBubbleStyle = () => ({
    background: 'linear-gradient(135deg, rgba(34,120,60,0.92), rgba(20,90,48,0.96))',
    border: '1px solid rgba(52,168,83,0.4)',
    color: '#e8f5e9',
    borderBottomRightRadius: '3px',
    boxShadow: '0 2px 12px rgba(52,168,83,0.12)',
  });

  const getThemBubbleStyle = () => ({
    background: 'linear-gradient(135deg, rgba(59,100,180,0.75), rgba(40,70,150,0.80))',
    border: '1px solid rgba(99,130,246,0.35)',
    color: '#e0e7ff',
    borderBottomLeftRadius: '3px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.15)',
  });

  // Use therapistInfo.ep_id — this is the exact same ID the WebSocket broadcasts use,
  // so it is the most reliable way to identify the EP's own messages.
  const isMe = (msg) =>
    msg.sender_role === 'emergency_personnel' &&
    Number(msg.sender_id) === Number(therapistInfo?.ep_id);

  return (
    <div className="ecp-root">
      <div className="ecp-bg-dots" />

      {/* ── Header ── */}
      <header className="ecp-header">
        <button className="ecp-back-btn" onClick={() => navigate('/emergency/dashboard')}>
          ← Back
        </button>
        <div className="ecp-header-title">
          <span className="ecp-header-icon">🤝</span>
          <span className="ecp-header-text">Chat with Your Therapist</span>
          {therapistInfo && (
            <span className="ecp-header-sub">/ {therapistInfo.name}</span>
          )}
        </div>
        <div className="ecp-header-right">
          {therapistInfo && (
            <span className="ecp-ws-dot" style={{ background: dotColor }} title={wsStatus} />
          )}
        </div>
      </header>

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

        {!loading && !loadError && therapistInfo && (
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
                  <span style={{ fontSize: '2.5rem', opacity: 0.4 }}>💬</span>
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
      </div>
    </div>
  );
}
