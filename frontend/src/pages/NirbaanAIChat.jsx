import { useState, useEffect, useRef, useCallback } from 'react'; // useRef kept for bottomRef + inputRef
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { sendNirbaanAIMessage, listNirbaanAIThreads, getNirbaanAIThread } from '../api/nirbaanai.api';
import './NirbaanAIChat.css';

export default function NirbaanAIChat() {
  const navigate = useNavigate();

  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Load thread list on mount
  useEffect(() => {
    listNirbaanAIThreads()
      .then(setThreads)
      .catch(() => {});
  }, []);

  // Scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadThread = useCallback(async (threadId) => {
    try {
      setLoading(true);
      const data = await getNirbaanAIThread(threadId);
      setActiveThreadId(threadId);
      setMessages(data.messages || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
      setSidebarOpen(false);
    }
  }, []);

  const startNewChat = () => {
    setActiveThreadId(null);
    setMessages([]);
    setSidebarOpen(false);
    inputRef.current?.focus();
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendNirbaanAIMessage({ message: text, thread_id: activeThreadId });

      // If this is a new thread, capture the ID and refresh sidebar list
      if (!activeThreadId) {
        setActiveThreadId(res.thread_id);
        listNirbaanAIThreads().then(setThreads).catch(() => {});
      }

      const assistantMsg = {
        ...res.assistant_message,
        is_escalation: res.is_escalation || false,
      };

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== userMsg.id), // remove optimistic
        res.user_message,
        assistantMsg,
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="nai-root">
      {/* Top bar */}
      <header className="nai-header">
        <button className="nai-back-btn" onClick={() => navigate('/patient/dashboard')}>
          ← Back
        </button>
        <div className="nai-header-title">
          <span className="nai-logo-text">NirbaanAI</span>
        </div>
        <button className="nai-sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)}>
          ☰ History
        </button>
      </header>

      {/* Thread sidebar */}
      <aside className={`nai-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="nai-sidebar-header">
          <span>Conversations</span>
          <button className="nai-new-btn" onClick={startNewChat}>+ New</button>
        </div>
        <ul className="nai-thread-list">
          {threads.length === 0 && (
            <li className="nai-thread-empty">No conversations yet</li>
          )}
          {threads.map((t) => (
            <li
              key={t.id}
              className={`nai-thread-item ${t.id === activeThreadId ? 'active' : ''}`}
              onClick={() => loadThread(t.id)}
            >
              <span className="nai-thread-icon">💬</span>
              <span className="nai-thread-label">
                {t.title || `Chat #${t.id}`}
              </span>
            </li>
          ))}
        </ul>
      </aside>

      {/* Overlay to close sidebar on mobile */}
      {sidebarOpen && <div className="nai-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* Main chat area */}
      <main className="nai-main">
        <div className="nai-chat-window">
          {messages.length === 0 && !loading && (
            <div className="nai-welcome">
              <div className="nai-welcome-icon">🌿</div>
              <h2>Hello, I'm NirbaanAI</h2>
              <p>Your personal psychoeducation companion.<br />Ask me anything about OCD, anxiety, or your therapy journey.</p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`nai-bubble-row ${msg.role === 'user' ? 'user' : 'assistant'}`}
            >
              {msg.role === 'assistant' && (
                <div className="nai-avatar">{msg.is_escalation ? '🚨' : '🌸'}</div>
              )}
              <div className={`nai-bubble ${msg.role}${msg.is_escalation ? ' escalation' : ''}`}>
                {msg.is_escalation && (
                  <div className="nai-escalation-banner">
                    🚨 Human helpers have been alerted
                  </div>
                )}
                {msg.role === 'assistant' ? (
                  <div className="nai-md">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p>{msg.content}</p>
                )}
                <span className="nai-ts">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              {msg.role === 'user' && (
                <div className="nai-avatar user-avatar">You</div>
              )}
            </div>
          ))}

          {loading && (
            <div className="nai-bubble-row assistant">
              <div className="nai-avatar">🌸</div>
              <div className="nai-bubble assistant nai-typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="nai-input-bar">
          
          <div className="nai-input-row">
            <textarea
              ref={inputRef}
              className="nai-input"
              rows={2}
              placeholder="Type your message… (Enter to send)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              className="nai-send-btn"
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              {loading ? '…' : '➤'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
