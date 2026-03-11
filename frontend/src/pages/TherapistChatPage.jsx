import { useState, useEffect, useRef } from 'react';
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
} from '../api/chat.api';
import { getPatients } from '../api/patient.api';
import './TherapistChatPage.css';

export default function TherapistChatPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

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
  const [sidebarTab, setSidebarTab] = useState('groups'); // 'groups' | 'ep'
  const [epContacts, setEpContacts] = useState([]);
  const [epContactsLoading, setEpContactsLoading] = useState(false);
  const [selectedEP, setSelectedEP] = useState(null);
  const [epMessages, setEpMessages] = useState([]);
  const [epMessagesLoading, setEpMessagesLoading] = useState(false);
  const [epInputText, setEpInputText] = useState('');
  const [epWsStatus, setEpWsStatus] = useState('idle');

  const wsRef = useRef(null);
  const epWsRef = useRef(null);
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

  // ── helpers ───────────────────────────────────────────────────────────────
  const memberIds = new Set(members.map((m) => m.patient_id));
  const nonMembers = allPatients.filter((p) => !memberIds.has(p.id));

  // Palette of distinct colors for each non-me sender
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
    const isMe = msg.sender_role === 'therapist' && msg.sender_id === user?.id;
    if (isMe) return {
      background: 'linear-gradient(135deg, rgba(34,120,60,0.9), rgba(20,90,48,0.95))',
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
          <span className="tcp-header-icon">💬</span>
          <span className="tcp-header-text">{sidebarTab === 'ep' ? 'EP Direct Chat' : 'Group Chat'}</span>
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
                  <span style={{ fontSize: '2.5rem', opacity: 0.4 }}>💬</span>
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

                const isMe = msg.sender_role === 'therapist' && msg.sender_id === user?.id;
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
            <span className="tcp-no-group-icon">💬</span>
            <h2>Select a group to chat</h2>
            <p>Create a group and add your patients to start chatting in real time.</p>
          </div>
          )
        ) : (
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
                const isMe = msg.sender_role === 'therapist' && msg.sender_id === user?.id;
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
            <span className="tcp-no-group-icon">🤝</span>
            <h2>Select a contact to chat</h2>
            <p>Click an emergency personnel contact from the list to start a direct conversation.</p>
          </div>
          )
        )}
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
