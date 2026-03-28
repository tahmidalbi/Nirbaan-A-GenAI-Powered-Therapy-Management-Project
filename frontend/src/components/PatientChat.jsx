import { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '../store/authStore';
import {
  listChatGroupsPatient,
  getChatMessages,
  openChatSocket,
} from '../api/chat.api';
import './PatientChat.css';

const PatientChat = () => {
  const user = useAuthStore((s) => s.user);

  const [groups, setGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState(null);

  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [inputText, setInputText] = useState('');

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ─── load groups ─────────────────────────────────────────────────────────

  useEffect(() => {
    listChatGroupsPatient()
      .then(setGroups)
      .catch(() => {})
      .finally(() => setGroupsLoading(false));
  }, []);

  // ─── select group ─────────────────────────────────────────────────────────

  useEffect(() => {
    if (!selectedGroup) return;

    setMessagesLoading(true);
    getChatMessages(selectedGroup.id)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setMessagesLoading(false));

    if (wsRef.current) wsRef.current.close();

    const ws = openChatSocket(selectedGroup.id);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      setMessages((prev) => [...prev, data]);
    };
    ws.onerror = () => {};
    ws.onclose = () => {};

    return () => ws.close();
  }, [selectedGroup?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ─── send message ─────────────────────────────────────────────────────────

  const handleSend = () => {
    const text = inputText.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ content: text }));
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ─── render ───────────────────────────────────────────────────────────────

  return (
    <div className="pc-container">
      {/* ── Group list sidebar ── */}
      <aside className="pc-sidebar">
        <div className="pc-sidebar-header">
          <h3>My Chat Groups</h3>
        </div>

        {groupsLoading ? (
          <div className="pc-sidebar-loading">Loading…</div>
        ) : groups.length === 0 ? (
          <div className="pc-sidebar-empty">
            You haven{"'"}t been added to any group yet.
            <br />
            Ask your therapist to add you.
          </div>
        ) : (
          <ul className="pc-group-list">
            {groups.map((g) => (
              <li
                key={g.id}
                className={`pc-group-item ${selectedGroup?.id === g.id ? 'active' : ''}`}
                onClick={() => setSelectedGroup(g)}
              >
                <span className="pc-group-icon">💬</span>
                <div className="pc-group-info">
                  <span className="pc-group-name">{g.name}</span>
                  <span className="pc-group-meta">
                    {g.member_count} member{g.member_count !== 1 ? 's' : ''}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* ── Chat area ── */}
      {selectedGroup ? (
        <div className="pc-main">
          <div className="pc-chat-header">
            <span className="pc-chat-name">{selectedGroup.name}</span>
          </div>

          <div className="pc-messages">
            {messagesLoading && (
              <div className="pc-messages-loading">Loading messages…</div>
            )}
            {messages.map((msg, idx) => {
              if (msg.type === 'system') {
                return (
                  <div key={idx} className="pc-system-msg">
                    {msg.content}
                  </div>
                );
              }
              const isMe =
                msg.sender_role === 'patient' && msg.sender_id === user?.id;
              return (
                <div key={msg.id || idx} className={`pc-bubble-row ${isMe ? 'me' : 'other'}`}>
                  {!isMe && (
                    <div className="pc-bubble-avatar">
                      {(msg.sender_name || '?').charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="pc-bubble-wrap">
                    {!isMe && (
                      <div className="pc-bubble-sender">
                        {msg.sender_name}
                        {msg.sender_role === 'therapist' && (
                          <span className="pc-therapist-badge"> · Therapist</span>
                        )}
                      </div>
                    )}
                    <div className={`pc-bubble ${isMe ? 'pc-bubble-me' : 'pc-bubble-other'}`}>
                      {msg.content}
                    </div>
                    <div className="pc-bubble-time">
                      {msg.created_at
                        ? new Date(msg.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : ''}
                    </div>
                  </div>
                  {isMe && (
                    <div className="pc-bubble-avatar pc-avatar-me">
                      {(user?.name || 'P').charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          <div className="pc-input-bar">
            <textarea
              className="pc-input"
              placeholder="Type a message… (Enter to send)"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button className="pc-send-btn" onClick={handleSend}>
              Send
            </button>
          </div>
        </div>
      ) : (
        <div className="pc-no-selection">
          <div className="pc-no-selection-icon">💬</div>
          <h3>Select a group to chat</h3>
          <p>Your therapist has added you to group chats.</p>
        </div>
      )}
    </div>
  );
};

export default PatientChat;
