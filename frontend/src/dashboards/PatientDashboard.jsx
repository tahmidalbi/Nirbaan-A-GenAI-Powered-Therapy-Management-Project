import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import PatientHomework from '../components/PatientHomework';
import PatientResourceLibrary from '../components/PatientResourceLibrary';
import IncomingCallModal from '../components/IncomingCallModal';
import MindfulnessPlayer from '../components/MindfulnessPlayer';
import './PatientDashboard.css';

const BACK_MAP = {
  sessions:    null,
  homework:    'sessions',
  resources:   null,
  mindfulness: null,
};

const VIEW_LABELS = {
  sessions:    'Sessions',
  homework:    'Homework',
  resources:   'Resources',
  mindfulness: 'Mindfulness',
};

const PatientDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const [view, setView] = useState(null);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const [incomingCall, setIncomingCall] = useState(null);

  const handleAcceptCall = useCallback(() => {
    if (!incomingCall) return;
    setIncomingCall(null);
    navigate(`/video-call/${incomingCall.sessionId}`);
  }, [incomingCall, navigate]);

  const handleDeclineCall = useCallback(() => setIncomingCall(null), []);

  useEffect(() => {
    if (!user?.id) return;
    const connect = () => {
      const ws = new WebSocket(
        `ws://127.0.0.1:8000/api/therapy-sessions/ws/call/${user.id}?user_type=patient`
      );
      ws.onopen = () => clearTimeout(reconnectRef.current);
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'incoming_call') {
          setIncomingCall({
            callerId: msg.caller_id,
            callerName: msg.caller_name || 'Your Therapist',
            sessionId: msg.session_id,
          });
        }
      };
      ws.onclose = () => { reconnectRef.current = setTimeout(connect, 5000); };
      ws.onerror = () => ws.close();
      wsRef.current = ws;
    };
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [user?.id]);

  const goTo = (v) => setView(v);
  const handleBack = () => setView(BACK_MAP[view] ?? null);
  const handleLogout = () => { logout(); navigate('/'); };
  const showBack = view !== null && BACK_MAP[view] !== undefined;

  return (
    <div className="pd-root">
      {incomingCall && (
        <IncomingCallModal
          callerName={incomingCall.callerName}
          onAccept={handleAcceptCall}
          onDecline={handleDeclineCall}
        />
      )}

      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            {view && (
              <div className="pd-brand-breadcrumb">
                <span className="pd-brand-sep">&rsaquo;</span>
                <span>{VIEW_LABELS[view] || view}</span>
              </div>
            )}
          </div>
          <div className="pd-header-actions">
            {showBack && (
              <button className="pd-back-btn" onClick={handleBack}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Back
              </button>
            )}
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      <main className="pd-main">

        {view === null && (
          <div className="pd-home">
            <div className="pd-welcome">
              <p className="pd-welcome-greeting">Welcome</p>
              <h2 className="pd-welcome-name">{user?.name || 'Patient'}</h2>
              
            </div>

            <div className="pd-tiles-grid pd-tiles-grid--home">

              <button className="pd-tile" onClick={() => goTo('sessions')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="16" y1="2" x2="16" y2="6" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="8" y1="2" x2="8" y2="6" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="3" y1="10" x2="21" y2="10" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="pd-tile-label">Sessions</span>
                <span className="pd-tile-sub">Progress &amp; homework</span>
              </button>

              <button className="pd-tile" onClick={() => goTo('resources')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="pd-tile-label">Resources</span>
                <span className="pd-tile-sub">Therapist-curated materials</span>
              </button>

              <button className="pd-tile" onClick={() => navigate('/patient/dashboard/tools/ocd')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="pd-tile-label">Tools</span>
                <span className="pd-tile-sub">OCD &amp; therapeutic exercises</span>
              </button>

              <button className="pd-tile" onClick={() => goTo('mindfulness')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M8 14s1.5 2 4 2 4-2 4-2" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="9" y1="9" x2="9.01" y2="9" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" />
                    <line x1="15" y1="9" x2="15.01" y2="9" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" />
                  </svg>
                </span>
                <span className="pd-tile-label">Mindfulness</span>
                <span className="pd-tile-sub">Relaxation &amp; meditation</span>
              </button>

              <button className="pd-tile" onClick={() => navigate('/patient/chat')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="pd-tile-label">Chat</span>
                <span className="pd-tile-sub">Message your therapist</span>
              </button>

              <button className="pd-tile pd-tile--ai" onClick={() => navigate('/patient/nirbaanai')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 2a6 6 0 0 1 6 6c0 4-6 12-6 12S6 12 6 8a6 6 0 0 1 6-6z" strokeLinecap="round" strokeLinejoin="round" />
                    <circle cx="12" cy="8" r="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M8 21h8M9 18l1.5-3h3L15 18" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="pd-tile-label">Nirbaan AI</span>
                <span className="pd-tile-sub">AI-powered wellness support</span>
              </button>

            </div>
          </div>
        )}

        {view === 'sessions' && (
          <div className="pd-submenu">
            <h2 className="pd-submenu-title">My Sessions</h2>
            <p className="pd-submenu-sub">Track your progress and complete assignments</p>
            <div className="pd-tiles-grid pd-tiles-grid--sub">

              <button className="pd-tile pd-tile--large" onClick={() => navigate('/patient/dashboard/progress')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <line x1="18" y1="20" x2="18" y2="10" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="12" y1="20" x2="12" y2="4" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="6" y1="20" x2="6" y2="14" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="pd-tile-label">Progress</span>
                <span className="pd-tile-sub">View your treatment progress</span>
              </button>

              <button className="pd-tile pd-tile--large" onClick={() => goTo('homework')}>
                <span className="pd-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round" />
                    <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="16" y1="13" x2="8" y2="13" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="16" y1="17" x2="8" y2="17" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="pd-tile-label">Homework</span>
                <span className="pd-tile-sub">Assignments from your therapist</span>
              </button>

            </div>
          </div>
        )}

        {view === 'homework' && (
          <div className="pd-content-panel">
            <PatientHomework />
          </div>
        )}

        {view === 'resources' && (
          <div className="pd-content-panel">
            <PatientResourceLibrary />
          </div>
        )}

        {view === 'mindfulness' && (
          <div className="pd-content-panel">
            <MindfulnessPlayer />
          </div>
        )}

      </main>
    </div>
  );
};

export default PatientDashboard;
