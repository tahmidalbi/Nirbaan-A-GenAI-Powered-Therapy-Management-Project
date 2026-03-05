import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  getERPItem,
  listImaginalCards,
  createImaginalCard,
  updateImaginalCard,
  deleteImaginalCard,
  getActiveSession,
  startSession,
  pauseSession,
  resumeSession,
  recordSUDS,
  getSUDSHistory,
  getLatestExerciseNote,
  createExerciseNote,
  updateExerciseNote,
  coachSendMessage,
  coachEndClick,
  coachDebriefSubmit,
  getSessionTranscript,
} from '../api/erp.api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import './ERPSessionPage.css';

const TOGGLE_ERP       = 'erp';
const TOGGLE_IMAGINAL  = 'imaginal';

const ERPSessionPage = () => {
  const { itemId } = useParams();
  const navigate   = useNavigate();
  const logout     = useAuthStore((s) => s.logout);

  // ── item data ──────────────────────────────────────────────────────────────
  const [item, setItem]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  // ── left panel toggle ──────────────────────────────────────────────────────
  const [leftView, setLeftView] = useState(TOGGLE_ERP);

  // ── session note (exercise notes table) ─────────────────────────────────────────
  const [noteText, setNoteText]     = useState('');
  const [noteSaving, setNoteSaving] = useState(false);
  const [latestNote, setLatestNote] = useState(null);  // {id, content} | null
  const noteTimerRef                = useRef(null);
  const currentNoteIdRef            = useRef(null);  // id of the note created this visit

  // ── imaginal cards ─────────────────────────────────────────────────────────
  const [cards, setCards]           = useState([]);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [addingCard, setAddingCard] = useState(false);
  // map of cardId -> local textarea content (for controlled inputs)
  const [cardDrafts, setCardDrafts] = useState({});
  const cardTimers                  = useRef({});

  // ── live session ───────────────────────────────────────────────────────────
  const [session, setSession]               = useState(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [actionLoading, setActionLoading]   = useState(false);
  const [displaySeconds, setDisplaySeconds] = useState(0);
  const timerRef                            = useRef(null);

  // ── SUDS ───────────────────────────────────────────────────────────────────
  const [sudsValue, setSudsValue]           = useState(50);
  const [sudsSubmitting, setSudsSubmitting] = useState(false);
  const [sudsHistory, setSudsHistory]       = useState([]);

  // ── Coach chat ─────────────────────────────────────────────────────────────
  const [chatMessages, setChatMessages]         = useState([]);
  const [chatInput, setChatInput]               = useState('');
  const [chatSending, setChatSending]           = useState(false);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  // debrief flow
  const [debriefMode, setDebriefMode]           = useState(false); // true when status==='ending'
  const [debriefText, setDebriefText]           = useState('');
  const [debriefSubmitting, setDebriefSubmitting] = useState(false);
  const [sessionFeedback, setSessionFeedback]   = useState(null); // PatientFeedbackJSON after submit
  const chatEndRef                              = useRef(null);
  const pollRef                                 = useRef(null);  // coach message poll interval

  // ── helpers ────────────────────────────────────────────────────────────────
  const formatTime = (totalSeconds) => {
    const s = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    const pad = (n) => String(n).padStart(2, '0');
    return h > 0 ? `${pad(h)}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
  };

  // ─────────────────────────────────────────────────────────────────────────
  const loadItem = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await getERPItem(Number(itemId));
      setItem(data);
      // note text starts empty — user writes a fresh exercise each visit
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Could not load this item.');
    } finally {
      setLoading(false);
    }
  }, [itemId]);

  const loadLatestNote = useCallback(async () => {
    try {
      const { data } = await getLatestExerciseNote(Number(itemId));
      setLatestNote(data || null);
    } catch {
      // silent
    }
  }, [itemId]);

  const loadCards = useCallback(async () => {
    try {
      setCardsLoading(true);
      const { data } = await listImaginalCards(Number(itemId));
      setCards(data);
      // initialise drafts
      const drafts = {};
      data.forEach((c) => { drafts[c.id] = c.content; });
      setCardDrafts(drafts);
    } catch {
      // silent — not critical
    } finally {
      setCardsLoading(false);
    }
  }, [itemId]);

  const loadSession = useCallback(async () => {
    try {
      setSessionLoading(true);
      const { data } = await getActiveSession(Number(itemId));
      setSession(data);
      if (data) {
        const base = data.accumulated_seconds || 0;
        if (data.status === 'running' && data.resumed_at) {
          const elapsed = (Date.now() - new Date(data.resumed_at + 'Z').getTime()) / 1000;
          setDisplaySeconds(base + elapsed);
        } else {
          setDisplaySeconds(base);
        }
      }
    } catch {
      // silent
    } finally {
      setSessionLoading(false);
    }
  }, [itemId]);

  const loadSUDSHistory = useCallback(async () => {
    try {
      const { data } = await getSUDSHistory(Number(itemId));
      setSudsHistory(data);
    } catch {
      // silent
    }
  }, [itemId]);

  const loadTranscript = useCallback(async (sessionId, { silent = false } = {}) => {
    if (!sessionId) return;
    try {
      if (!silent) setTranscriptLoading(true);
      const { data } = await getSessionTranscript(sessionId);
      setChatMessages(data.messages || []);
    } catch {
      // silent
    } finally {
      if (!silent) setTranscriptLoading(false);
    }
  }, []);

  useEffect(() => {
    loadItem();
    loadLatestNote();
    loadCards();
    loadSession();
    loadSUDSHistory();
  }, [loadItem, loadLatestNote, loadCards, loadSession, loadSUDSHistory]);

  // Load transcript when session becomes known
  useEffect(() => {
    if (session?.id) {
      loadTranscript(session.id);
      if (session.status === 'ending') setDebriefMode(true);
      if (session.status === 'ended' && session.patient_feedback_json) {
        setSessionFeedback(session.patient_feedback_json);
      }
    }
  }, [session?.id, session?.status, loadTranscript]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, debriefMode, sessionFeedback]);

  // ── poll for new coach messages while session is running ─────────────────
  useEffect(() => {
    const sid = session?.id;
    const isRunning = session?.status === 'running';
    if (sid && isRunning) {
      // clear any stale interval first
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(() => {
        loadTranscript(sid, { silent: true });
      }, 15000); // every 15 seconds
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [session?.id, session?.status, loadTranscript]);

  // ── timer tick ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (session?.status === 'running') {
      timerRef.current = setInterval(() => {
        setDisplaySeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [session?.status]);

  // ── session actions ───────────────────────────────────────────────────────
  const handleStart = async () => {
    setActionLoading(true);
    try {
      const { data } = await startSession(Number(itemId));
      setSession(data);
      setDisplaySeconds(0);
    } catch { /* silent */ } finally { setActionLoading(false); }
  };

  const handlePause = async () => {
    if (!session) return;
    setActionLoading(true);
    try {
      const { data } = await pauseSession(session.id);
      setSession(data);
      setDisplaySeconds(data.accumulated_seconds);
    } catch { /* silent */ } finally { setActionLoading(false); }
  };

  const handleResume = async () => {
    if (!session) return;
    setActionLoading(true);
    try {
      const { data } = await resumeSession(session.id);
      setSession(data);
    } catch { /* silent */ } finally { setActionLoading(false); }
  };

  const handleEnd = async () => {
    if (!session) return;
    if (!window.confirm('End this session and begin the debrief?')) return;
    setActionLoading(true);
    try {
      const { data: coachResp } = await coachEndClick(session.id);
      // Reload session so status reflects 'ending'
      const { data: updatedSession } = await getActiveSession(Number(itemId));
      if (updatedSession) {
        setSession(updatedSession);
        setDisplaySeconds(updatedSession.accumulated_seconds);
      }
      // Append coach debrief prompt to chat
      if (coachResp?.coach_message) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            role: 'coach',
            content: coachResp.coach_message,
            intent: 'DEBRIEF_PROMPT',
            tags: coachResp.tags || [],
            created_at: new Date().toISOString(),
          },
        ]);
      }
      setDebriefMode(true);
    } catch { /* silent */ } finally { setActionLoading(false); }
  };

  const handleCoachSend = async () => {
    if (!chatInput.trim() || !session || session.status !== 'running') return;
    const text = chatInput.trim();
    setChatInput('');
    // Optimistic patient message
    const tempPatientMsg = { id: Date.now(), role: 'patient', content: text, created_at: new Date().toISOString() };
    setChatMessages((prev) => [...prev, tempPatientMsg]);
    setChatSending(true);
    try {
      const { data: coachResp } = await coachSendMessage(session.id, text);
      if (coachResp?.coach_message && coachResp.type !== 'NO_MESSAGE') {
        setChatMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: 'coach',
            content: coachResp.coach_message,
            intent: coachResp.source,
            tags: coachResp.tags || [],
            created_at: new Date().toISOString(),
          },
        ]);
      }
    } catch { /* silent */ } finally { setChatSending(false); }
  };

  const handleDebriefSubmit = async () => {
    if (!debriefText.trim() || !session) return;
    setDebriefSubmitting(true);
    try {
      const { data } = await coachDebriefSubmit(session.id, debriefText);
      setSessionFeedback(data.patient_feedback);
      setDebriefMode(false);
      // Mark session as ended locally
      setSession((prev) => prev ? { ...prev, status: 'ended' } : prev);
    } catch { /* silent */ } finally { setDebriefSubmitting(false); }
  };

  const handleRecordSUDS = async () => {
    if (!session || session.status === 'ended') return;
    setSudsSubmitting(true);
    try {
      await recordSUDS(session.id, sudsValue, displaySeconds);
      await loadSUDSHistory();
    } catch { /* silent */ } finally { setSudsSubmitting(false); }
  };

  // ── exercise note: auto-save 1s after last keypress ───────────────────────
  const handleNoteChange = (value) => {
    setNoteText(value);
    if (noteTimerRef.current) clearTimeout(noteTimerRef.current);
    if (!value.trim()) return;  // don’t save empty
    noteTimerRef.current = setTimeout(async () => {
      try {
        setNoteSaving(true);
        if (currentNoteIdRef.current === null) {
          // first save this visit → create a new note
          const { data } = await createExerciseNote(Number(itemId), value);
          currentNoteIdRef.current = data.id;
          setLatestNote(data);
        } else {
          // subsequent saves → update the same note
          const { data } = await updateExerciseNote(currentNoteIdRef.current, value);
          setLatestNote(data);
        }
      } catch {
        // silently fail
      } finally {
        setNoteSaving(false);
      }
    }, 1000);
  };

  // ── imaginal cards ─────────────────────────────────────────────────────────
  const handleAddCard = async () => {
    setAddingCard(true);
    try {
      const { data: newCard } = await createImaginalCard(Number(itemId), { content: '' });
      setCards((prev) => [...prev, newCard]);
      setCardDrafts((prev) => ({ ...prev, [newCard.id]: '' }));
    } catch {
      // silent
    } finally {
      setAddingCard(false);
    }
  };

  const handleCardDraftChange = (cardId, value) => {
    setCardDrafts((prev) => ({ ...prev, [cardId]: value }));
    if (cardTimers.current[cardId]) clearTimeout(cardTimers.current[cardId]);
    cardTimers.current[cardId] = setTimeout(async () => {
      try {
        await updateImaginalCard(cardId, { content: value });
        // update local cards array too
        setCards((prev) => prev.map((c) => c.id === cardId ? { ...c, content: value } : c));
      } catch {
        // silent
      }
    }, 800);
  };

  const handleDeleteCard = async (cardId) => {
    if (!window.confirm('Delete this card?')) return;
    try {
      await deleteImaginalCard(cardId);
      setCards((prev) => prev.filter((c) => c.id !== cardId));
      setCardDrafts((prev) => {
        const next = { ...prev };
        delete next[cardId];
        return next;
      });
    } catch {
      // silent
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="session-loader">
        <span>Loading session…</span>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="session-loader">
        <span className="session-loader-error">{error || 'Item not found.'}</span>
        <button onClick={() => navigate('/patient/dashboard/erp/dive-in')}>← Back</button>
      </div>
    );
  }

  return (
    <div className="session-container">
      {/* background */}
      <div className="session-bg">
        <div className="session-bg-pattern" />
      </div>

      {/* header */}
      <header className="session-header">
        <div className="session-header-inner">
          <button className="session-ghost-btn" onClick={() => navigate('/patient/dashboard/erp/dive-in')}>
            ← Back
          </button>
          <h1 className="session-logo">ERP Session</h1>
          <button className="session-ghost-btn" onClick={() => { logout(); navigate('/'); }}>
            Logout
          </button>
        </div>
      </header>

      {/* three-panel layout */}
      <main className="session-main">

        {/* ── LEFT PANEL ──────────────────────────────────────────────── */}
        <section className="session-panel session-panel-left">

          {/* toggle */}
          <div className="session-toggle-bar">
            <button
              className={`session-toggle-btn ${leftView === TOGGLE_ERP ? 'active' : ''}`}
              onClick={() => setLeftView(TOGGLE_ERP)}
            >
              ERP Exercise
            </button>
            <button
              className={`session-toggle-btn ${leftView === TOGGLE_IMAGINAL ? 'active' : ''}`}
              onClick={() => setLeftView(TOGGLE_IMAGINAL)}
            >
              Imaginal Exposures
            </button>
          </div>

          {/* ── ERP Exercise view ── */}
          {leftView === TOGGLE_ERP && (
            <div className="session-erp-view">
              {/* obsession */}
              <div className="session-section">
                <span className="session-label">Obsession</span>
                <p className="session-obsession-text">{item.obsession}</p>
              </div>

              {/* compulsions */}
              {item.compulsions && item.compulsions.length > 0 && (
                <div className="session-section">
                  <span className="session-label">Compulsions</span>
                  <ul className="session-compulsions-list">
                    {item.compulsions.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* exercise note */}
              <div className="session-section session-section-grow">
                <span className="session-label">
                  My Exercise for This Session
                  {noteSaving && <span className="session-saving-indicator"> · saving…</span>}
                  {!noteSaving && currentNoteIdRef.current && <span className="session-saved-indicator"> · saved</span>}
                </span>
                <textarea
                  className="session-note-textarea"
                  placeholder="Write the exercise you will practise in this session…"
                  value={noteText}
                  onChange={(e) => handleNoteChange(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* ── Imaginal Exposures view ── */}
          {leftView === TOGGLE_IMAGINAL && (
            <div className="session-imaginal-view">
              <div className="session-imaginal-header">
                <span className="session-label">Imaginal Exposure Cards</span>
                <button
                  className="session-add-card-btn"
                  onClick={handleAddCard}
                  disabled={addingCard}
                  title="Add a new card"
                >
                  {addingCard ? '…' : '+'}
                </button>
              </div>

              {cardsLoading && <p className="session-cards-loading">Loading cards…</p>}

              {!cardsLoading && cards.length === 0 && (
                <p className="session-cards-empty">
                  No cards yet. Click <strong>+</strong> to add your first exposure card.
                </p>
              )}

              <div className="session-cards-grid">
                {cards.map((card, idx) => (
                  <div key={card.id} className="session-imaginal-card">
                    <div className="session-card-top">
                      <span className="session-card-num">Card {idx + 1}</span>
                      <button
                        className="session-card-delete-btn"
                        title="Delete card"
                        onClick={() => handleDeleteCard(card.id)}
                      >
                        ✕
                      </button>
                    </div>
                    <textarea
                      className="session-card-textarea"
                      placeholder="Write your fear item or exposure script…"
                      value={cardDrafts[card.id] ?? card.content}
                      onChange={(e) => handleCardDraftChange(card.id, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ── CENTER PANEL ─────────────────────────────────────────────── */}
        <section className="session-panel session-panel-center">

          {/* ── Timer ── */}
          <div className="sc-timer-block">
            <div className="sc-timer-display">{formatTime(displaySeconds)}</div>
            <div className={`sc-status-badge sc-status-${session?.status ?? 'idle'}`}>
              {session?.status === 'running' && '● Running'}
              {session?.status === 'paused'  && '⏸ Paused'}
              {session?.status === 'ending'  && '📝 Debrief'}
              {session?.status === 'ended'   && '✓ Ended'}
              {!session && (sessionLoading ? 'Loading…' : 'Not started')}
            </div>
          </div>

          {/* ── Controls ── */}
          <div className="sc-controls-row">
            {/* Start — only when no active/paused session */}
            {!session && !sessionLoading && (
              <button
                className="sc-btn sc-btn-start"
                onClick={handleStart}
                disabled={actionLoading}
              >
                ▶ Start Session
              </button>
            )}
            {/* Pause — when running */}
            {session?.status === 'running' && (
              <button
                className="sc-btn sc-btn-pause"
                onClick={handlePause}
                disabled={actionLoading}
              >
                ⏸ Pause
              </button>
            )}
            {/* Resume — when paused */}
            {session?.status === 'paused' && (
              <button
                className="sc-btn sc-btn-resume"
                onClick={handleResume}
                disabled={actionLoading}
              >
                ▶ Resume
              </button>
            )}
            {/* End — when running or paused */}
            {(session?.status === 'running' || session?.status === 'paused') && (
              <button
                className="sc-btn sc-btn-end"
                onClick={handleEnd}
                disabled={actionLoading}
              >
                ■ End
              </button>
            )}
            {/* Start New — when ended */}
            {session?.status === 'ended' && (
              <button
                className="sc-btn sc-btn-start"
                onClick={handleStart}
                disabled={actionLoading}
              >
                ▶ New Session
              </button>
            )}
          </div>

          {/* ── SUDS Input ── */}
          <div className="sc-suds-block">
            <span className="sc-suds-label">
              Record SUDS  <span className="sc-suds-value-badge">{sudsValue}</span>
            </span>
            <div className="sc-suds-row">
              <span className="sc-suds-scale-hint">0</span>
              <input
                type="range"
                min={0}
                max={100}
                value={sudsValue}
                onChange={(e) => setSudsValue(Number(e.target.value))}
                className="sc-suds-slider"
              />
              <span className="sc-suds-scale-hint">100</span>
              <input
                type="number"
                min={0}
                max={100}
                value={sudsValue}
                onChange={(e) => setSudsValue(Math.min(100, Math.max(0, Number(e.target.value))))}
                className="sc-suds-number"
              />
            </div>
            <button
              className="sc-btn sc-btn-suds"
              onClick={handleRecordSUDS}
              disabled={sudsSubmitting || !session || session.status === 'ended'}
            >
              {sudsSubmitting ? 'Saving…' : 'Submit SUDS'}
            </button>
          </div>

          {/* ── SUDS Graph ── */}
          <div className="sc-graph-block">
            <span className="sc-graph-label">SUDS Over Time (All Sessions)</span>
            {sudsHistory.length === 0 ? (
              <p className="sc-graph-empty">No SUDS readings yet. Submit your first one above.</p>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart
                  data={sudsHistory.map((r, i) => ({
                    reading: i + 1,
                    suds: r.suds_value,
                    time: formatTime(r.elapsed_seconds),
                  }))}
                  margin={{ top: 8, right: 10, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.15)" />
                  <XAxis
                    dataKey="reading"
                    stroke="rgba(255,255,255,0.55)"
                    tick={{ fontSize: 11 }}
                    label={{ value: 'Reading #', position: 'insideBottom', offset: -2, fontSize: 11, fill: 'rgba(255,255,255,0.55)' }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    stroke="rgba(255,255,255,0.55)"
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={{ background: 'rgba(30,50,45,0.92)', border: 'none', borderRadius: 8, color: '#fff', fontSize: 12 }}
                    formatter={(value, name, props) => [`SUDS: ${value}`, `@ ${props.payload.time}`]}
                    labelFormatter={(label) => `Reading #${label}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="suds"
                    stroke="#7de8c8"
                    strokeWidth={2}
                    dot={{ fill: '#7de8c8', r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

        </section>

        {/* ── RIGHT PANEL ─ ERP Coach Chat ─────────────────────────────── */}
        <section className="session-panel session-panel-right">
          <div className="sc-coach-panel">
            <div className="sc-coach-header">
              <span className="sc-coach-title">🤖 ERP Coach</span>
              {transcriptLoading && <span className="sc-coach-loading-dot" />}
            </div>

            {/* ── Messages ── */}
            <div className="sc-chat-messages">
              {!transcriptLoading && chatMessages.length === 0 && !sessionFeedback && (
                <div className="sc-chat-empty">
                  {session?.status === 'running' || session?.status === 'paused'
                    ? 'Send a message to start chatting with your ERP Coach.'
                    : session
                    ? 'No messages in this session yet.'
                    : 'Start a session to chat with your coach.'}
                </div>
              )}

              {chatMessages.map((msg) => (
                <div key={msg.id} className={`sc-chat-bubble sc-bubble-${msg.role}`}>
                  {(msg.role === 'coach' || msg.role === 'system') && (
                    <span className="sc-bubble-icon">🤖</span>
                  )}
                  <div className="sc-bubble-content">
                    <p className="sc-bubble-text">{msg.content}</p>
                    {msg.tags?.length > 0 && (
                      <div className="sc-bubble-tags">
                        {msg.tags.map((t, i) => <span key={i} className="sc-tag">{t}</span>)}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* ── Debrief form ── */}
              {debriefMode && (
                <div className="sc-debrief-form">
                  <p className="sc-debrief-label">Your reflection on this session:</p>
                  <textarea
                    className="sc-debrief-textarea"
                    placeholder="What did you notice during the exposure? How did your anxiety change?"
                    value={debriefText}
                    onChange={(e) => setDebriefText(e.target.value)}
                    rows={4}
                  />
                  <button
                    className="sc-btn sc-btn-debrief"
                    onClick={handleDebriefSubmit}
                    disabled={debriefSubmitting || !debriefText.trim()}
                  >
                    {debriefSubmitting ? 'Saving…' : 'Submit Reflection'}
                  </button>
                </div>
              )}

              {/* ── Patient feedback after debrief ── */}
              {sessionFeedback && (
                <div className="sc-feedback-card">
                  <div className="sc-feedback-header">✨ Session Summary</div>
                  {sessionFeedback.wins?.length > 0 && (
                    <div className="sc-feedback-section">
                      <span className="sc-feedback-label">Your Wins</span>
                      <ul className="sc-feedback-list">
                        {sessionFeedback.wins.map((w, i) => <li key={i}>{w}</li>)}
                      </ul>
                    </div>
                  )}
                  {sessionFeedback.reflection?.length > 0 && (
                    <div className="sc-feedback-section">
                      <span className="sc-feedback-label">Reflections</span>
                      <ul className="sc-feedback-list">
                        {sessionFeedback.reflection.map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}
                  {sessionFeedback.skill_to_practice && (
                    <div className="sc-feedback-section">
                      <span className="sc-feedback-label">Skill to Practice</span>
                      <p className="sc-feedback-text">{sessionFeedback.skill_to_practice}</p>
                    </div>
                  )}
                  {sessionFeedback.one_micro_goal_next_time && (
                    <div className="sc-feedback-section">
                      <span className="sc-feedback-label">Next Session Goal</span>
                      <p className="sc-feedback-text">{sessionFeedback.one_micro_goal_next_time}</p>
                    </div>
                  )}
                  {sessionFeedback.reminder && (
                    <div className="sc-feedback-reminder">{sessionFeedback.reminder}</div>
                  )}
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* ── Input area ── */}
            {session?.status === 'running' && !debriefMode && (
              <div className="sc-chat-input-row">
                <textarea
                  className="sc-chat-input"
                  placeholder="Message your coach…"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleCoachSend();
                    }
                  }}
                  rows={2}
                  disabled={chatSending}
                />
                <button
                  className="sc-chat-send-btn"
                  onClick={handleCoachSend}
                  disabled={chatSending || !chatInput.trim()}
                >
                  {chatSending ? '…' : '↑'}
                </button>
              </div>
            )}
            {session?.status === 'paused' && !debriefMode && (
              <div className="sc-chat-paused-note">Resume the session to send messages.</div>
            )}
            {session?.status === 'ended' && !sessionFeedback && (
              <div className="sc-chat-paused-note">Session ended. View your report above.</div>
            )}
          </div>
        </section>

      </main>
    </div>
  );
};

export default ERPSessionPage;
