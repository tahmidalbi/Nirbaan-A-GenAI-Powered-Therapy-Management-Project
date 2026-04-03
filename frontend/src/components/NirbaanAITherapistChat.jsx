import { useState, useEffect, useRef, useCallback } from 'react';
import {
  sendTherapistAIMessage,
  submitTherapistClarificationAnswer,
  listTherapistAIThreads,
  getTherapistAIThread,
} from '../api/nirbaanai-therapist.api';
import { getPatients } from '../api/patient.api';
import './NirbaanAITherapistChat.css';

// ─── Clarification inline card ─────────────────────────────────────────────
function ClarificationCard({ question, loading, onSubmit, onCancel }) {
  const [answer, setAnswer] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = answer.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
    if (e.key === 'Escape') onCancel();
  };

  return (
    <div className="nait-clarification-card">
      <div className="nait-clarification-header">
        <span className="nait-clarification-icon">🔍</span>
        <span className="nait-clarification-label">Clarification needed</span>
      </div>
      <p className="nait-clarification-question">{question}</p>
      <form className="nait-clarification-form" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          className="nait-clarification-input"
          rows={3}
          placeholder="Type your answer… (Enter to submit)"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <div className="nait-clarification-actions">
          <button
            type="button"
            className="nait-clarification-cancel"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="nait-clarification-submit"
            disabled={loading || !answer.trim()}
          >
            {loading ? (
              <span className="nait-btn-spinner" />
            ) : (
              'Submit answer'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── Patient picker panel ──────────────────────────────────────────────────
function PatientPicker({ patients, selectedPatient, onSelect, loading }) {
  const [search, setSearch] = useState('');
  const filtered = patients.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="nait-patient-picker">
      <div className="nait-patient-picker-header">
        <span className="nait-patient-picker-title">Select a patient</span>
        <p className="nait-patient-picker-hint">
          NirbaanAI will analyse the selected patient's full context.
        </p>
      </div>
      <input
        className="nait-patient-search"
        type="text"
        placeholder="Search patients…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {loading && <p className="nait-patient-loading">Loading patients…</p>}
      <ul className="nait-patient-list">
        {filtered.length === 0 && !loading && (
          <li className="nait-patient-empty">No patients found</li>
        )}
        {filtered.map((p) => (
          <li
            key={p.id}
            className={`nait-patient-item ${selectedPatient?.id === p.id ? 'selected' : ''}`}
            onClick={() => onSelect(p)}
          >
            <div className="nait-patient-avatar">
              {p.name.charAt(0).toUpperCase()}
            </div>
            <div className="nait-patient-info">
              <span className="nait-patient-name">{p.name}</span>
              {p.conditions && (
                <span className="nait-patient-cond">{p.conditions}</span>
              )}
            </div>
            {selectedPatient?.id === p.id && (
              <span className="nait-patient-check">✓</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────
export default function NirbaanAITherapistChat({ onBack }) {
  // Patients
  const [patients, setPatients] = useState([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState(null);

  // Threads & messages
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);

  // Chat input
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  // Human-in-the-loop state
  const [pendingClarification, setPendingClarification] = useState(null);
  // { question, analysisRunId }
  const [clarificationLoading, setClarificationLoading] = useState(false);

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [patientPanelOpen, setPatientPanelOpen] = useState(false);
  const [sidebarSearch, setSidebarSearch] = useState('');

  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // ── Bootstrap ────────────────────────────────────────────────────────────
  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(() => {})
      .finally(() => setPatientsLoading(false));

    listTherapistAIThreads()
      .then(setThreads)
      .catch(() => {});
  }, []);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pendingClarification]);

  // ── Thread helpers ────────────────────────────────────────────────────────
  const loadThread = useCallback(async (threadId) => {
    try {
      setLoading(true);
      const data = await getTherapistAIThread(threadId);
      setActiveThreadId(threadId);
      setMessages(data.messages || []);
      setPendingClarification(null);

      // Auto-set selected patient from thread metadata
      if (data.thread?.patient_id) {
        const p = patients.find((pt) => pt.id === data.thread.patient_id);
        if (p) setSelectedPatient(p);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [patients]);

  const startNewChat = () => {
    setActiveThreadId(null);
    setMessages([]);
    setPendingClarification(null);
    setInput('');
    inputRef.current?.focus();
  };

  const refreshThreads = () =>
    listTherapistAIThreads().then(setThreads).catch(() => {});

  // Threads that belong to the selected patient (or all if none selected)
  const visibleThreads = selectedPatient
    ? threads.filter((t) => t.patient_id === selectedPatient.id)
    : threads;

  const filteredThreads = sidebarSearch.trim()
    ? visibleThreads.filter((t) =>
        (t.title || '').toLowerCase().includes(sidebarSearch.toLowerCase())
      )
    : visibleThreads;

  const formatThreadDate = (iso) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now - d;
    if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604800000) return d.toLocaleDateString([], { weekday: 'short' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  // ── Send message ──────────────────────────────────────────────────────────
  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading || pendingClarification) return;

    if (!selectedPatient) {
      setPatientPanelOpen(true);
      return;
    }

    const optimisticUser = {
      id: `opt-${Date.now()}`,
      role: 'therapist',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendTherapistAIMessage({
        message: text,
        patient_id: selectedPatient.id,
        thread_id: activeThreadId,
      });

      // Replace optimistic with real user message
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticUser.id),
        res.user_message,
      ]);

      if (!activeThreadId) {
        setActiveThreadId(res.thread_id);
        refreshThreads();
      }

      if (res.needs_clarification && res.clarification) {
        // Human-in-the-loop: surface the inline clarification card
        setPendingClarification({
          question: res.clarification.question,
          analysisRunId: res.analysis_run?.id,
        });
      } else if (res.assistant_message) {
        setMessages((prev) => [...prev, res.assistant_message]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: 'Something went wrong. Please try again.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // ── Submit clarification answer ────────────────────────────────────────────
  const handleClarificationSubmit = async (answer) => {
    if (!pendingClarification) return;
    setClarificationLoading(true);

    try {
      const res = await submitTherapistClarificationAnswer({
        analysisRunId: pendingClarification.analysisRunId,
        answer,
      });

      setPendingClarification(null);

      const finalText =
        res.analysis_summary ||
        "Analysis complete. No summary returned.";

      setMessages((prev) => [
        ...prev,
        {
          id: `cl-${Date.now()}`,
          role: 'assistant',
          content: finalText,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `cl-err-${Date.now()}`,
          role: 'assistant',
          content: 'Failed to process your answer. Please try again.',
          created_at: new Date().toISOString(),
        },
      ]);
      setPendingClarification(null);
    } finally {
      setClarificationLoading(false);
    }
  };

  const handleClarificationCancel = () => {
    setPendingClarification(null);
    setMessages((prev) => [
      ...prev,
      {
        id: `cl-cancel-${Date.now()}`,
        role: 'assistant',
        content: 'Clarification skipped. You can ask a more specific question to get a complete analysis.',
        created_at: new Date().toISOString(),
      },
    ]);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="nait-root">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="nait-header">
        <div className="nait-header-left">
          <div className="nait-logo-mark">N</div>
          <div className="nait-header-title">
            <span className="nait-logo-text">NirbaanAI</span>
            <span className="nait-logo-badge">Therapist</span>
          </div>
        </div>

        <div className="nait-header-center">
          {selectedPatient ? (
            <button
              className="nait-patient-chip"
              onClick={() => setPatientPanelOpen((v) => !v)}
              title="Change patient"
            >
              <span className="nait-patient-chip-avatar">
                {selectedPatient.name.charAt(0).toUpperCase()}
              </span>
              <span className="nait-patient-chip-name">{selectedPatient.name}</span>
              <span className="nait-patient-chip-arrow">▾</span>
            </button>
          ) : (
            <button
              className="nait-select-patient-btn"
              onClick={() => setPatientPanelOpen((v) => !v)}
            >
              Select a patient to analyse
            </button>
          )}
        </div>

        <div className="nait-header-right">
          <button
            className="nait-icon-btn"
            title="New chat"
            onClick={startNewChat}
          >
            ✏
          </button>
          <button
            className="nait-icon-btn"
            title="Chat history"
            onClick={() => setSidebarOpen((v) => !v)}
          >
            ☰
          </button>
          {onBack && (
            <button
              className="nait-icon-btn nait-back-btn"
              title="Back to dashboard"
              onClick={onBack}
            >
              ✕
            </button>
          )}
        </div>
      </header>

      {/* ── Patient picker dropdown ──────────────────────────────────── */}
      {patientPanelOpen && (
        <>
          <div
            className="nait-overlay"
            onClick={() => setPatientPanelOpen(false)}
          />
          <div className="nait-patient-picker-dropdown">
            <PatientPicker
              patients={patients}
              selectedPatient={selectedPatient}
              loading={patientsLoading}
              onSelect={(p) => {
                setSelectedPatient(p);
                setPatientPanelOpen(false);
                // Start fresh thread for the new patient
                startNewChat();
              }}
            />
          </div>
        </>
      )}

      {/* ── Body: history panel + chat side by side ─────────────────── */}
      <div className="nait-body">

        {/* History column — always in the flow, no portal needed */}
        <aside className={`nait-history${sidebarOpen ? '' : ' nait-history--collapsed'}`}>

          {/* History header */}
          <div className="nait-history-head">
            <div className="nait-history-head-left">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="14" height="14">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>History</span>
            </div>
            <button
              className="nait-history-new-btn"
              onClick={startNewChat}
              title="New chat"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" width="11" height="11">
                <path d="M12 5v14M5 12h14" strokeLinecap="round"/>
              </svg>
              New
            </button>
          </div>

          {/* Patient context row */}
          {selectedPatient && (
            <div className="nait-history-patient">
              <div className="nait-history-patient-avatar">
                {selectedPatient.name.charAt(0).toUpperCase()}
              </div>
              <div className="nait-history-patient-info">
                <span className="nait-history-patient-name">{selectedPatient.name}</span>
                <span className="nait-history-patient-meta">
                  {visibleThreads.length} session{visibleThreads.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          )}

          {/* Search */}
          <div className="nait-history-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="13" height="13">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35" strokeLinecap="round"/>
            </svg>
            <input
              placeholder="Search…"
              value={sidebarSearch}
              onChange={(e) => setSidebarSearch(e.target.value)}
            />
            {sidebarSearch && (
              <button onClick={() => setSidebarSearch('')}>✕</button>
            )}
          </div>

          {/* Thread list */}
          <div className="nait-history-list">
            {filteredThreads.length === 0 ? (
              <div className="nait-history-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" width="40" height="40">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <p>
                  {sidebarSearch
                    ? 'No matches'
                    : selectedPatient
                    ? `No sessions yet`
                    : 'Select a patient'}
                </p>
              </div>
            ) : (
              filteredThreads.map((t) => {
                const patient = patients.find((p) => p.id === t.patient_id);
                const isActive = t.id === activeThreadId;
                return (
                  <button
                    key={t.id}
                    className={`nait-thread-btn${isActive ? ' nait-thread-btn--active' : ''}`}
                    onClick={() => loadThread(t.id)}
                  >
                    <div className={`nait-thread-btn-icon${isActive ? ' nait-thread-btn-icon--active' : ''}`}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="12" height="12">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <div className="nait-thread-btn-body">
                      <span className="nait-thread-btn-title">
                        {t.title || `Session #${t.id}`}
                      </span>
                      {patient && !selectedPatient && (
                        <span className="nait-thread-btn-patient">{patient.name}</span>
                      )}
                    </div>
                    {t.created_at && (
                      <span className="nait-thread-btn-date">
                        {formatThreadDate(t.created_at)}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>

        </aside>

        {/* ── Main chat area ─────────────────────────────────────────── */}
        <main className="nait-main">
        <div className="nait-chat-window">

          {/* Welcome state */}
          {messages.length === 0 && !loading && !pendingClarification && (
            <div className="nait-welcome">
              <h2>Hello, I'm NirbaanAI</h2>
              {selectedPatient ? (
                <p>
                  Currently analysing <strong>{selectedPatient.name}</strong>.<br />
                  Ask me anything about their progress, fear ladder, ERP sessions, or next steps.
                </p>
              ) : (
                <p>
                  Select a patient using the button above, then ask me anything about
                  their therapy progress, ERP sessions, or clinical next steps.
                </p>
              )}
              {!selectedPatient && (
                <button
                  className="nait-welcome-cta"
                  onClick={() => setPatientPanelOpen(true)}
                >
                  Select a patient →
                </button>
              )}
            </div>
          )}

          {/* Messages */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`nait-bubble-row ${
                msg.role === 'therapist' || msg.role === 'user' ? 'user' : 'assistant'
              }`}
            >
              {(msg.role === 'assistant') && (
                <div className="nait-avatar">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="18" height="18">
                    <circle cx="12" cy="8" r="3.5" strokeLinecap="round"/>
                    <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              )}
              <div
                className={`nait-bubble ${
                  msg.role === 'therapist' || msg.role === 'user'
                    ? 'user'
                    : 'assistant'
                }`}
              >
                <p>{msg.content}</p>
                <span className="nait-ts">
                  {new Date(msg.created_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
              {(msg.role === 'therapist' || msg.role === 'user') && (
                <div className="nait-avatar user-avatar">You</div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="nait-bubble-row assistant">
              <div className="nait-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="18" height="18">
                  <circle cx="12" cy="8" r="3.5" strokeLinecap="round"/>
                  <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="nait-bubble assistant nait-typing">
                <span /><span /><span />
              </div>
            </div>
          )}

          {/* ── Human-in-the-loop clarification card ── */}
          {pendingClarification && !loading && (
            <div className="nait-bubble-row assistant nait-clarification-row">
              <div className="nait-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="18" height="18">
                  <circle cx="12" cy="8" r="3.5" strokeLinecap="round"/>
                  <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <ClarificationCard
                question={pendingClarification.question}
                loading={clarificationLoading}
                onSubmit={handleClarificationSubmit}
                onCancel={handleClarificationCancel}
              />
            </div>
          )}

          {clarificationLoading && (
            <div className="nait-bubble-row assistant">
              <div className="nait-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="18" height="18">
                  <circle cx="12" cy="8" r="3.5" strokeLinecap="round"/>
                  <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="nait-bubble assistant nait-typing">
                <span /><span /><span />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className={`nait-input-bar ${pendingClarification ? 'nait-input-bar--disabled' : ''}`}>
          {pendingClarification && (
            <div className="nait-input-blocked-hint">
              ↑ Please answer the clarification question above first
            </div>
          )}
          <div className="nait-input-row">
            <textarea
              ref={inputRef}
              className="nait-input"
              rows={2}
              placeholder={
                !selectedPatient
                  ? 'Select a patient first…'
                  : pendingClarification
                  ? 'Answer the question above to continue…'
                  : `Ask about ${selectedPatient.name}… (Enter to send)`
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading || !!pendingClarification || !selectedPatient}
            />
            <button
              className="nait-send-btn"
              onClick={handleSend}
              disabled={loading || !!pendingClarification || !input.trim() || !selectedPatient}
            >
              {loading ? '…' : '➤'}
            </button>
          </div>
        </div>
      </main>

      </div>{/* end nait-body */}
    </div>
  );
}
