import { useState, useEffect, useRef } from 'react';
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
} from '../api/chat.api';
import { getPatients } from '../api/patient.api';
import './TherapistChat.css';

const TherapistChat = () => {
  const user = useAuthStore((s) => s.user);

  // groups
  const [groups, setGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [newGroupName, setNewGroupName] = useState('');
  const [creatingGroup, setCreatingGroup] = useState(false);

  // selected group
  const [selectedGroup, setSelectedGroup] = useState(null);

  // members panel
  const [members, setMembers] = useState([]);
  const [allPatients, setAllPatients] = useState([]);
  const [showMembersPanel, setShowMembersPanel] = useState(false);
  const [membersLoading, setMembersLoading] = useState(false);

  // messages
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [inputText, setInputText] = useState('');

  // websocket
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ─── load groups ─────────────────────────────────────────────────────────

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    setGroupsLoading(true);
    try {
      const data = await listChatGroupsTherapist();
      setGroups(data);
    } catch {
      // silent
    } finally {
      setGroupsLoading(false);
    }
  };

  // ─── select group ─────────────────────────────────────────────────────────

  useEffect(() => {
    if (!selectedGroup) return;

    // load history
    setMessagesLoading(true);
    getChatMessages(selectedGroup.id)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setMessagesLoading(false));

    // open websocket
    if (wsRef.current) {
      wsRef.current.close();
    }
    const ws = openChatSocket(selectedGroup.id);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      setMessages((prev) => [...prev, data]);
    };

    ws.onerror = () => {};
    ws.onclose = () => {};

    return () => {
      ws.close();
    };
  }, [selectedGroup?.id]);

  // scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ─── create group ─────────────────────────────────────────────────────────

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;
    setCreatingGroup(true);
    try {
      const group = await createChatGroup(newGroupName.trim());
      setGroups((prev) => [...prev, { ...group, member_count: 0 }]);
      setNewGroupName('');
    } catch {
      // silent
    } finally {
      setCreatingGroup(false);
    }
  };

  // ─── delete group ─────────────────────────────────────────────────────────

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
    } catch {
      // silent
    }
  };

  // ─── members panel ────────────────────────────────────────────────────────

  const openMembersPanel = async () => {
    if (!selectedGroup) return;
    setShowMembersPanel(true);
    setMembersLoading(true);
    try {
      const [membersData, patientsData] = await Promise.all([
        listGroupMembers(selectedGroup.id),
        getPatients(),
      ]);
      setMembers(membersData);
      setAllPatients(patientsData);
    } catch {
      // silent
    } finally {
      setMembersLoading(false);
    }
  };

  const handleAddMember = async (patientId) => {
    try {
      await addGroupMember(selectedGroup.id, patientId);
      const membersData = await listGroupMembers(selectedGroup.id);
      setMembers(membersData);
      setGroups((prev) =>
        prev.map((g) =>
          g.id === selectedGroup.id
            ? { ...g, member_count: (g.member_count || 0) + 1 }
            : g
        )
      );
    } catch (err) {
      if (err?.response?.status === 409) {
        alert('Patient is already in this group.');
      }
    }
  };

  const handleRemoveMember = async (patientId) => {
    try {
      await removeGroupMember(selectedGroup.id, patientId);
      setMembers((prev) => prev.filter((m) => m.patient_id !== patientId));
      setGroups((prev) =>
        prev.map((g) =>
          g.id === selectedGroup.id
            ? { ...g, member_count: Math.max(0, (g.member_count || 1) - 1) }
            : g
        )
      );
    } catch {
      // silent
    }
  };

  // ─── send message ─────────────────────────────────────────────────────────

  const handleSend = () => {
    const text = inputText.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ content: text }));
    setInputText('');
  };

  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ─── render ───────────────────────────────────────────────────────────────

  const memberIds = new Set(members.map((m) => m.patient_id));
  const nonMembers = allPatients.filter((p) => !memberIds.has(p.id));

  return (
    <div className="tc-container">
      {/* ── Left sidebar: group list ── */}
      <aside className="tc-sidebar">
        <div className="tc-sidebar-header">
          <h3>Chat Groups</h3>
        </div>

        <form className="tc-create-form" onSubmit={handleCreateGroup}>
          <input
            className="tc-create-input"
            placeholder="New group name…"
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
          />
          <button className="tc-create-btn" type="submit" disabled={creatingGroup}>
            {creatingGroup ? '…' : '+'}
          </button>
        </form>

        {groupsLoading ? (
          <div className="tc-sidebar-loading">Loading groups…</div>
        ) : groups.length === 0 ? (
          <div className="tc-sidebar-empty">No groups yet. Create one above.</div>
        ) : (
          <ul className="tc-group-list">
            {groups.map((g) => (
              <li
                key={g.id}
                className={`tc-group-item ${selectedGroup?.id === g.id ? 'active' : ''}`}
                onClick={() => setSelectedGroup(g)}
              >
                <span className="tc-group-icon">💬</span>
                <div className="tc-group-info">
                  <span className="tc-group-name">{g.name}</span>
                  <span className="tc-group-meta">{g.member_count} member{g.member_count !== 1 ? 's' : ''}</span>
                </div>
                <button
                  className="tc-group-delete-btn"
                  onClick={(e) => handleDeleteGroup(g.id, e)}
                  title="Delete group"
                >
                  🗑
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* ── Main chat area ── */}
      {selectedGroup ? (
        <div className="tc-main">
          <div className="tc-chat-header">
            <div className="tc-chat-title">
              <span className="tc-chat-name">{selectedGroup.name}</span>
            </div>
            <button className="tc-manage-btn" onClick={openMembersPanel}>
              Manage Members
            </button>
          </div>

          <div className="tc-messages">
            {messagesLoading && <div className="tc-messages-loading">Loading messages…</div>}
            {messages.map((msg, idx) => {
              if (msg.type === 'system') {
                return (
                  <div key={idx} className="tc-system-msg">
                    {msg.content}
                  </div>
                );
              }
              const isMe = msg.sender_role === 'therapist' && msg.sender_id === user?.id;
              return (
                <div key={msg.id || idx} className={`tc-bubble-row ${isMe ? 'me' : 'other'}`}>
                  {!isMe && (
                    <div className="tc-bubble-avatar">
                      {(msg.sender_name || '?').charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="tc-bubble-wrap">
                    {!isMe && <div className="tc-bubble-sender">{msg.sender_name}</div>}
                    <div className={`tc-bubble ${isMe ? 'tc-bubble-me' : 'tc-bubble-other'}`}>
                      {msg.content}
                    </div>
                    <div className="tc-bubble-time">
                      {msg.created_at
                        ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : ''}
                    </div>
                  </div>
                  {isMe && (
                    <div className="tc-bubble-avatar tc-avatar-me">
                      {(user?.name || 'T').charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          <div className="tc-input-bar">
            <textarea
              className="tc-input"
              placeholder="Type a message… (Enter to send)"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleInputKeyDown}
              rows={1}
            />
            <button className="tc-send-btn" onClick={handleSend}>
              Send
            </button>
          </div>
        </div>
      ) : (
        <div className="tc-no-selection">
          <div className="tc-no-selection-icon">💬</div>
          <h3>Select a group to start chatting</h3>
          <p>Create a group and add your patients to chat in real time.</p>
        </div>
      )}

      {/* ── Members panel overlay ── */}
      {showMembersPanel && (
        <div className="tc-overlay" onClick={() => setShowMembersPanel(false)}>
          <div className="tc-members-panel" onClick={(e) => e.stopPropagation()}>
            <div className="tc-members-header">
              <h3>Manage Members — {selectedGroup?.name}</h3>
              <button className="tc-close-btn" onClick={() => setShowMembersPanel(false)}>✕</button>
            </div>

            {membersLoading ? (
              <div className="tc-members-loading">Loading…</div>
            ) : (
              <>
                <div className="tc-members-section">
                  <h4>Current Members ({members.length})</h4>
                  {members.length === 0 ? (
                    <p className="tc-members-empty">No members yet.</p>
                  ) : (
                    <ul className="tc-member-list">
                      {members.map((m) => (
                        <li key={m.id} className="tc-member-item">
                          <span className="tc-member-avatar">
                            {(m.patient_name || '?').charAt(0).toUpperCase()}
                          </span>
                          <span className="tc-member-name">{m.patient_name}</span>
                          <button
                            className="tc-member-remove-btn"
                            onClick={() => handleRemoveMember(m.patient_id)}
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="tc-members-section">
                  <h4>Add Patients</h4>
                  {nonMembers.length === 0 ? (
                    <p className="tc-members-empty">All your patients are already members.</p>
                  ) : (
                    <ul className="tc-member-list">
                      {nonMembers.map((p) => (
                        <li key={p.id} className="tc-member-item">
                          <span className="tc-member-avatar">
                            {(p.name || '?').charAt(0).toUpperCase()}
                          </span>
                          <span className="tc-member-name">{p.name}</span>
                          <button
                            className="tc-member-add-btn"
                            onClick={() => handleAddMember(p.id)}
                          >
                            Add
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TherapistChat;
