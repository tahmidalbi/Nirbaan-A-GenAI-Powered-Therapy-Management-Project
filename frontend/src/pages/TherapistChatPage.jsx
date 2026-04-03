import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  createChatGroup,
  deleteChatGroup,
  listChatGroupsTherapist,
  addGroupMember,
  removeGroupMember,
  listGroupMembers,
  getChatMessages,
  openChatSocket,
  listEPContacts,
  getEPMessages,
  openEPChatSocket,
  getTherapistEPGroup,
  getEPGroupMessages,
  claimEPGroupMessage,
  openEPGroupSocket,
} from '../api/chat.api';
import { getPatients } from '../api/patient.api';
import './TherapistChatPage.css';

export default function TherapistChatPage() {
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
  const [newGroupName, setNewGroupName] = useState('');
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState(null);

  const [members, setMembers] = useState([]);
  const [allPatients, setAllPatients] = useState([]);
  const [showMembersPanel, setShowMembersPanel] = useState(false);
  const [membersLoading, setMembersLoading] = useState(false);

  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [wsStatus, setWsStatus] = useState('idle');

  // ── EP contacts state ─────────────────────────────────────────────────────
  const [sidebarTab, setSidebarTab] = useState('groups'); // 'groups' | 'ep' | 'epgroup'
  const [epContacts, setEpContacts] = useState([]);
  const [epContactsLoading, setEpContactsLoading] = useState(false);
  const [selectedEP, setSelectedEP] = useState(null);
  const [epMessages, setEpMessages] = useState([]);
  const [epMessagesLoading, setEpMessagesLoading] = useState(false);
  const [epInputText, setEpInputText] = useState('');
  const [epWsStatus, setEpWsStatus] = useState('idle');

  // ── EP Group state ────────────────────────────────────────────────────────
  const [epGroupInfo, setEpGroupInfo] = useState(null); // { id, therapist_id }
  const [epGroupMessages, setEpGroupMessages] = useState([]);
  const [epGroupMessagesLoading, setEpGroupMessagesLoading] = useState(false);
  const [epGroupInputText, setEpGroupInputText] = useState('');
  const [epGroupWsStatus, setEpGroupWsStatus] = useState('idle');

  const wsRef = useRef(null);
  const epWsRef = useRef(null);
  const epGroupWsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ── load groups ────────────────────────────────────────────────────────────
  useEffect(() => {
    listChatGroupsTherapist()
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
  }, [messages, epMessages]);

  // ── EP contacts: load when tab switches ───────────────────────────────────
  useEffect(() => {
    if (sidebarTab !== 'ep') return;
    setEpContactsLoading(true);
    listEPContacts()
      .then(setEpContacts)
      .catch(() => {})
      .finally(() => setEpContactsLoading(false));
  }, [sidebarTab]);

  // ── EP selected: load history + open WS ──────────────────────────────────
  useEffect(() => {
    if (!selectedEP) return;
    setEpMessages([]);
    setEpMessagesLoading(true);
    getEPMessages(selectedEP.id)
      .then(setEpMessages)
      .catch(() => {})
      .finally(() => setEpMessagesLoading(false));

    if (epWsRef.current) epWsRef.current.close();
    setEpWsStatus('connecting');
    const ws = openEPChatSocket(selectedEP.id);
    epWsRef.current = ws;
    ws.onopen = () => setEpWsStatus('open');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEpMessages((prev) => [...prev, data]);
    };
    ws.onerror = () => setEpWsStatus('closed');
    ws.onclose = () => setEpWsStatus('closed');
    return () => ws.close();
  }, [selectedEP?.id]);

  // ── EP Group: load group info + history + open WS when tab selected ───────
  useEffect(() => {
    if (sidebarTab !== 'epgroup') return;
    if (epGroupInfo) return; // already loaded
    getTherapistEPGroup()
      .then((info) => {
        setEpGroupInfo(info);
        setEpGroupMessagesLoading(true);
        return getEPGroupMessages(info.id);
      })
      .then(setEpGroupMessages)
      .catch(() => {})
      .finally(() => setEpGroupMessagesLoading(false));
  }, [sidebarTab]);

  useEffect(() => {
    if (!epGroupInfo) return;
    if (sidebarTab !== 'epgroup') return;
    if (epGroupWsRef.current) epGroupWsRef.current.close();
    setEpGroupWsStatus('connecting');
    const ws = openEPGroupSocket(epGroupInfo.id);
    epGroupWsRef.current = ws;
    ws.onopen = () => setEpGroupWsStatus('open');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      // Handle claim_update: replace existing message
      if (data.type === 'claim_update') {
        setEpGroupMessages((prev) =>
          prev.map((m) => (m.id === data.id ? data : m))
        );
      } else {
        setEpGroupMessages((prev) => [...prev, data]);
      }
    };
    ws.onerror = () => setEpGroupWsStatus('closed');
    ws.onclose = () => setEpGroupWsStatus('closed');
    return () => ws.close();
  }, [epGroupInfo?.id, sidebarTab]);

  // ── create group ──────────────────────────────────────────────────────────
  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;
    setCreatingGroup(true);
    try {
      const g = await createChatGroup(newGroupName.trim());
      setGroups((prev) => [...prev, { ...g, member_count: 0 }]);
      setNewGroupName('');
    } catch {
      // silent
    } finally {
      setCreatingGroup(false);
    }
  };

  // ── delete group ──────────────────────────────────────────────────────────
  const handleDeleteGroup = async (groupId, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this group and all its messages?')) return;
    try {
      await deleteChatGroup(groupId);
      setGroups((prev) => prev.filter((g) => g.id !== groupId));
      if (selectedGroup?.id === groupId) {
        setSelectedGroup(null);
        setMessages([]);
        wsRef.current?.close();
      }
    } catch { /* silent */ }
  };

  // ── members panel ─────────────────────────────────────────────────────────
  const openMembersPanel = async () => {
    if (!selectedGroup) return;
    setShowMembersPanel(true);
    setMembersLoading(true);
    try {
      const [m, p] = await Promise.all([
        listGroupMembers(selectedGroup.id),
        getPatients(),
      ]);
      setMembers(m);
      setAllPatients(p);
    } catch { /* silent */ }
    finally { setMembersLoading(false); }
  };

  const handleAddMember = async (patientId) => {
    try {
      await addGroupMember(selectedGroup.id, patientId);
      const m = await listGroupMembers(selectedGroup.id);
      setMembers(m);
      setGroups((prev) =>
        prev.map((g) => g.id === selectedGroup.id ? { ...g, member_count: (g.member_count || 0) + 1 } : g)
      );
    } catch (err) {
      if (err?.response?.status === 409) alert('Patient already in group.');
    }
  };

  const handleRemoveMember = async (patientId) => {
    try {
      await removeGroupMember(selectedGroup.id, patientId);
      setMembers((prev) => prev.filter((m) => m.patient_id !== patientId));
      setGroups((prev) =>
        prev.map((g) => g.id === selectedGroup.id ? { ...g, member_count: Math.max(0, (g.member_count || 1) - 1) } : g)
      );
    } catch { /* silent */ }
  };

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

  // ── EP send ───────────────────────────────────────────────────────────────
  const handleEPSend = () => {
    const text = epInputText.trim();
    if (!text || !epWsRef.current || epWsRef.current.readyState !== WebSocket.OPEN) return;
    epWsRef.current.send(JSON.stringify({ content: text }));
    setEpInputText('');
  };

  const handleEPKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEPSend(); }
  };

  // ── EP Group send ─────────────────────────────────────────────────────────
  const handleEPGroupSend = () => {
    const text = epGroupInputText.trim();
    if (!text || !epGroupWsRef.current || epGroupWsRef.current.readyState !== WebSocket.OPEN) return;
    epGroupWsRef.current.send(JSON.stringify({ content: text }));
    setEpGroupInputText('');
  };

  const handleEPGroupKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEPGroupSend(); }
  };

  // ── EP Group claim ────────────────────────────────────────────────────────
  const handleClaimMessage = async (msg) => {
    if (!epGroupInfo || msg.is_claimed) return;
    try {
      await claimEPGroupMessage(epGroupInfo.id, msg.id);
      // WS broadcast will update local state via onmessage
    } catch { /* silent */ }
  };

  // ── helpers ───────────────────────────────────────────────────────────────
  const memberIds = new Set(members.map((m) => m.patient_id));
  const nonMembers = allPatients.filter((p) => !memberIds.has(p.id));

  // Two-color chat: me (therapist) = dark green, everyone else = dark slate
  const getSenderStyle = (msg) => {
    const isMe = msg.sender_role === 'therapist' && Number(msg.sender_id) === Number(myUserId);
    if (isMe) return {
      background: 'linear-gradient(135deg, rgba(34,120,60,0.9), rgba(20,90,48,0.95))',
      border: '1px solid rgba(52,168,83,0.4)',
      color: '#e8f5e9',
      borderBottomRightRadius: '3px',
      boxShadow: '0 2px 12px rgba(52,168,83,0.12)',
    };
    return {
      background: 'rgba(28, 50, 44, 0.88)',
      border: '1px solid rgba(125, 212, 188, 0.18)',
      color: '#dceee8',
      borderBottomLeftRadius: '3px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.15)',
    };
  };

  const fmtTime = (ts) =>
    ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  const dotColor = wsStatus === 'open' ? '#4ade80' : wsStatus === 'connecting' ? '#fbbf24' : '#6b7280';
  const epDotColor = epWsStatus === 'open' ? '#4ade80' : epWsStatus === 'connecting' ? '#fbbf24' : '#6b7280';

  return (
    <div className="tcp-root">
      {/* dot-grid texture */}
      <div className="tcp-bg-dots" />

      {/* ── Header ── */}
      <header className="tcp-header">
        <button className="tcp-back-btn" onClick={() => navigate('/therapist/dashboard')}>
          ← Back
        </button>
        <div className="tcp-header-title">
          <span className="tcp-header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" width="20" height="20">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </span>
          <span className="tcp-header-text">
            {sidebarTab === 'ep' ? 'EP Direct Chat' : sidebarTab === 'epgroup' ? 'HH Group Chat' : 'Group Chat'}
          </span>
          {selectedGroup && sidebarTab === 'groups' && (
            <span className="tcp-header-group">/ {selectedGroup.name}</span>
          )}
          {selectedEP && sidebarTab === 'ep' && (
            <span className="tcp-header-group">/ {selectedEP.name}</span>
          )}
        </div>
        <div className="tcp-header-right">
          {selectedGroup && sidebarTab === 'groups' && (
            <>
              <span className="tcp-ws-indicator" style={{ background: dotColor }} title={wsStatus} />
              <button className="tcp-manage-btn" onClick={openMembersPanel}>
                Manage Members
              </button>
            </>
          )}
          {selectedEP && sidebarTab === 'ep' && (
            <span className="tcp-ws-indicator" style={{ background: epDotColor }} title={epWsStatus} />
          )}
        </div>
      </header>

      {/* ── Body ── */}
      <div className="tcp-body">
        {/* ── Left sidebar ── */}
        <aside className="tcp-sidebar">
          {/* Tab switcher */}
          <div className="tcp-sidebar-tabs">
            <button
              className={`tcp-tab-btn ${sidebarTab === 'groups' ? 'active' : ''}`}
              onClick={() => setSidebarTab('groups')}
            >
              Groups
            </button>
            <button
              className={`tcp-tab-btn ${sidebarTab === 'ep' ? 'active' : ''}`}
              onClick={() => setSidebarTab('ep')}
            >
              Contacts
            </button>
            <button
              className={`tcp-tab-btn ${sidebarTab === 'epgroup' ? 'active' : ''}`}
              onClick={() => setSidebarTab('epgroup')}
            >
              HH Group
            </button>
          </div>

          {/* ── Groups tab ── */}
          {sidebarTab === 'groups' && (
            <>
              <div className="tcp-sidebar-top">
                <form className="tcp-create-form" onSubmit={handleCreateGroup}>
                  <input
                    className="tcp-create-input"
                    placeholder="New group name…"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                  />
                  <button className="tcp-create-btn" type="submit" disabled={creatingGroup}>
                    {creatingGroup ? '…' : '+'}
                  </button>
                </form>
              </div>

              {groupsLoading ? (
                <div className="tcp-sidebar-empty">Loading groups…</div>
              ) : groups.length === 0 ? (
                <div className="tcp-sidebar-empty">No groups yet.<br />Create one above.</div>
              ) : (
                <ul className="tcp-group-list">
                  {groups.map((g) => (
                    <li
                      key={g.id}
                      className={`tcp-group-item ${selectedGroup?.id === g.id ? 'active' : ''}`}
                      onClick={() => setSelectedGroup(g)}
                    >
                      <div className="tcp-group-dot" />
                      <div className="tcp-group-info">
                        <span className="tcp-group-name">{g.name}</span>
                        <span className="tcp-group-meta">
                          {g.member_count} member{g.member_count !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <button
                        className="tcp-group-del"
                        onClick={(e) => handleDeleteGroup(g.id, e)}
                        title="Delete group"
                      >✕</button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          {/* ── EP Contacts tab ── */}
          {sidebarTab === 'ep' && (
            <>
              <div className="tcp-sidebar-top">
                <h3 className="tcp-sidebar-title">Human Helpers</h3>
              </div>

              {epContactsLoading ? (
                <div className="tcp-sidebar-empty">Loading contacts…</div>
              ) : epContacts.length === 0 ? (
                <div className="tcp-sidebar-empty">No emergency personnel assigned yet.</div>
              ) : (
                <ul className="tcp-group-list">
                  {epContacts.map((ep) => (
                    <li
                      key={ep.id}
                      className={`tcp-group-item ${selectedEP?.id === ep.id ? 'active' : ''}`}
                      onClick={() => setSelectedEP(ep)}
                    >
                      <div className="tcp-ep-avatar">{ep.name.charAt(0).toUpperCase()}</div>
                      <div className="tcp-group-info">
                        <span className="tcp-group-name">{ep.name}</span>
                        <span className="tcp-group-meta">{ep.email}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          {/* ── HH Group tab (sidebar is just a label — no sub-selection) ── */}
          {sidebarTab === 'epgroup' && (
            <div className="tcp-sidebar-top" style={{ padding: '1rem 1rem 0.75rem' }}>
              <h3 className="tcp-sidebar-title">Human Helper Group</h3>
              <p style={{ fontSize: '0.72rem', color: 'rgba(165,214,167,0.6)', marginTop: '0.4rem', lineHeight: 1.4 }}>
                All your human helpers are in this shared group. AI agent alerts appear here.
              </p>
            </div>
          )}
        </aside>

        {/* ── Main chat area ── */}
        {sidebarTab === 'groups' ? (
          selectedGroup ? (
          <div className="tcp-main">
            {/* messages */}
            <div className="tcp-messages">
              {messagesLoading && (
                <div className="tcp-loading-msg">
                  <span className="tcp-dots"><span/><span/><span/></span>
                  Loading messages…
                </div>
              )}

              {!messagesLoading && messages.length === 0 && (
                <div className="tcp-empty-msg">
                  <p>No messages yet. Say something!</p>
                </div>
              )}

              {messages.map((msg, idx) => {
                if (msg.type === 'system') {
                  return (
                    <div key={idx} className="tcp-system-msg">
                      <span className="tcp-system-line" />
                      <span className="tcp-system-text">{msg.content}</span>
                      <span className="tcp-system-line" />
                    </div>
                  );
                }

                const isMe = msg.sender_role === 'therapist' && Number(msg.sender_id) === Number(myUserId);
                const bubbleStyle = getSenderStyle(msg);

                return (
                  <div key={msg.id || idx} className={`tcp-row ${isMe ? 'tcp-row-me' : ''}`}>
                    {!isMe && (
                      <div className="tcp-avatar tcp-avatar-patient">
                        {(msg.sender_name || '?').charAt(0).toUpperCase()}
                      </div>
                    )}

                    <div className="tcp-bubble-wrap">
                      {!isMe && (
                        <div className="tcp-sender-name">{msg.sender_name}</div>
                      )}
                      <div className="tcp-bubble" style={bubbleStyle}>
                        {msg.content}
                        <span className="tcp-time">{fmtTime(msg.created_at)}</span>
                      </div>
                    </div>

                    {isMe && (
                      <div className="tcp-avatar tcp-avatar-me">
                        {(user?.name || 'T').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* input */}
            <div className="tcp-input-bar">
              <textarea
                ref={inputRef}
                className="tcp-input"
                placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <button
                className="tcp-send-btn"
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
          <div className="tcp-no-group">
            <h2>Select a group to chat</h2>
            <p>Create a group and add your patients to start chatting in real time.</p>
          </div>
          )
        ) : sidebarTab === 'ep' ? (
          /* ── EP DM view ── */
          selectedEP ? (
          <div className="tcp-main">
            <div className="tcp-messages">
              {epMessagesLoading && (
                <div className="tcp-loading-msg">
                  <span className="tcp-dots"><span/><span/><span/></span>
                  Loading messages…
                </div>
              )}

              {!epMessagesLoading && epMessages.length === 0 && (
                <div className="tcp-empty-msg">
                  <span style={{ fontSize: '2.5rem', opacity: 0.4 }}>🤝</span>
                  <p>No messages yet. Start the conversation with {selectedEP.name}.</p>
                </div>
              )}

              {epMessages.map((msg, idx) => {
                const isMe = msg.sender_role === 'therapist' && Number(msg.sender_id) === Number(myUserId);
                const bubbleStyle = getSenderStyle(msg);
                return (
                  <div key={msg.id || idx} className={`tcp-row ${isMe ? 'tcp-row-me' : ''}`}>
                    {!isMe && (
                      <div className="tcp-avatar tcp-avatar-patient">
                        {(msg.sender_name || '?').charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="tcp-bubble-wrap">
                      {!isMe && <div className="tcp-sender-name">{msg.sender_name}</div>}
                      <div className="tcp-bubble" style={bubbleStyle}>
                        {msg.content}
                        <span className="tcp-time">{fmtTime(msg.created_at)}</span>
                      </div>
                    </div>
                    {isMe && (
                      <div className="tcp-avatar tcp-avatar-me">
                        {(user?.name || 'T').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <div className="tcp-input-bar">
              <textarea
                className="tcp-input"
                placeholder={`Message ${selectedEP.name}… (Enter to send)`}
                value={epInputText}
                onChange={(e) => setEpInputText(e.target.value)}
                onKeyDown={handleEPKeyDown}
                rows={1}
              />
              <button
                className="tcp-send-btn"
                onClick={handleEPSend}
                disabled={!epInputText.trim() || epWsStatus !== 'open'}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>
          ) : (
          <div className="tcp-no-group">
            <h2>Select a contact to chat</h2>
            <p>Click an emergency personnel contact from the list to start a direct conversation.</p>
          </div>
          )
        ) : sidebarTab === 'epgroup' ? (
          /* ── EP Group view ── */
          <div className="tcp-main">
            <div className="tcp-epg-header-bar">

              <span className="tcp-epg-title">Human Helper Group</span>
              <span
                className="tcp-ws-indicator"
                style={{ background: epGroupWsStatus === 'open' ? '#4ade80' : epGroupWsStatus === 'connecting' ? '#fbbf24' : '#6b7280', marginLeft: 'auto' }}
                title={epGroupWsStatus}
              />
            </div>

            <div className="tcp-messages">
              {epGroupMessagesLoading && (
                <div className="tcp-loading-msg">
                  <span className="tcp-dots"><span/><span/><span/></span>
                  Loading messages…
                </div>
              )}
              {!epGroupMessagesLoading && epGroupMessages.length === 0 && (
                <div className="tcp-empty-msg">
                  <p>No messages yet. The AI agent will post alerts here when a patient needs a visit.</p>
                </div>
              )}
              {epGroupMessages.map((msg, idx) => {
                const isMe = msg.sender_role === 'therapist' && Number(msg.sender_id) === Number(myUserId);
                const isAI = msg.sender_role === 'ai_agent' || msg.sender_role === 'system';
                const bubbleStyle = isMe
                  ? getSenderStyle(msg)
                  : isAI
                    ? { background: 'rgba(80,40,120,0.82)', border: '1px solid rgba(168,85,247,0.4)', color: '#e0e7ff', borderBottomLeftRadius: '3px' }
                    : getSenderStyle(msg);
                return (
                  <div key={msg.id || idx} className={`tcp-row ${isMe ? 'tcp-row-me' : ''}`}>
                    {!isMe && (
                      <div className="tcp-avatar tcp-avatar-patient" style={isAI ? { background: 'linear-gradient(135deg,#6d28d9,#4c1d95)' } : {}}>
                        {isAI ? 'AI' : (msg.sender_name || '?').charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="tcp-bubble-wrap">
                      {!isMe && <div className="tcp-sender-name">{msg.sender_name}{isAI && <span className="tcp-therapist-tag" style={{ background: 'rgba(109,40,217,0.25)', color: '#c4b5fd' }}>AI</span>}</div>}
                      <div className="tcp-bubble" style={bubbleStyle}>
                        {msg.patient_name && (
                          <div className="tcp-epg-patient-ref">
                            Patient: <strong>{msg.patient_name}</strong>
                          </div>
                        )}
                        {msg.content}
                        {msg.is_claimed && (
                          <div className="tcp-epg-claim-badge">
                            ✅ Being visited by <strong>{msg.claimed_by_name}</strong>
                          </div>
                        )}
                        <span className="tcp-time">{fmtTime(msg.created_at)}</span>
                      </div>
                    </div>
                    {isMe && (
                      <div className="tcp-avatar tcp-avatar-me">
                        {(user?.name || 'T').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <div className="tcp-input-bar">
              <textarea
                className="tcp-input"
                placeholder="Type a message to all human helpers… (Enter to send)"
                value={epGroupInputText}
                onChange={(e) => setEpGroupInputText(e.target.value)}
                onKeyDown={handleEPGroupKeyDown}
                rows={1}
              />
              <button
                className="tcp-send-btn"
                onClick={handleEPGroupSend}
                disabled={!epGroupInputText.trim() || epGroupWsStatus !== 'open'}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {/* ── Members overlay ── */}
      {showMembersPanel && (
        <div className="tcp-overlay" onClick={() => setShowMembersPanel(false)}>
          <div className="tcp-members-modal" onClick={(e) => e.stopPropagation()}>
            <div className="tcp-modal-header">
              <h3>Manage Members — {selectedGroup?.name}</h3>
              <button className="tcp-modal-close" onClick={() => setShowMembersPanel(false)}>✕</button>
            </div>

            {membersLoading ? (
              <div className="tcp-modal-loading">Loading…</div>
            ) : (
              <>
                <section className="tcp-modal-section">
                  <h4 className="tcp-modal-section-title">
                    Current Members <span className="tcp-count-badge">{members.length}</span>
                  </h4>
                  {members.length === 0 ? (
                    <p className="tcp-modal-empty">No members yet.</p>
                  ) : (
                    <ul className="tcp-modal-list">
                      {members.map((m) => (
                        <li key={m.id} className="tcp-modal-member">
                          <div className="tcp-modal-avatar">
                            {(m.patient_name || '?').charAt(0).toUpperCase()}
                          </div>
                          <span className="tcp-modal-name">{m.patient_name}</span>
                          <button
                            className="tcp-modal-action tcp-action-remove"
                            onClick={() => handleRemoveMember(m.patient_id)}
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <section className="tcp-modal-section">
                  <h4 className="tcp-modal-section-title">Add Patients</h4>
                  {nonMembers.length === 0 ? (
                    <p className="tcp-modal-empty">All your patients are already members.</p>
                  ) : (
                    <ul className="tcp-modal-list">
                      {nonMembers.map((p) => (
                        <li key={p.id} className="tcp-modal-member">
                          <div className="tcp-modal-avatar tcp-modal-avatar-add">
                            {(p.name || '?').charAt(0).toUpperCase()}
                          </div>
                          <span className="tcp-modal-name">{p.name}</span>
                          <button
                            className="tcp-modal-action tcp-action-add"
                            onClick={() => handleAddMember(p.id)}
                          >
                            + Add
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
