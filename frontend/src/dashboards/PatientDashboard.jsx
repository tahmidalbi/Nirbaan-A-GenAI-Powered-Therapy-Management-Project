import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { getMyTherapySessions } from '../api/sessions.api';
import PatientHomework from '../components/PatientHomework';
import PatientResourceLibrary from '../components/PatientResourceLibrary';
import IncomingCallModal from '../components/IncomingCallModal';
import './PatientDashboard.css';

const PatientDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const [activeSection, setActiveSection] = useState(null);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  // Therapy sessions state (session transcripts from therapist)
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState('');
  const [expandedSession, setExpandedSession] = useState(null);

  // Incoming call state
  const [incomingCall, setIncomingCall] = useState(null); // { callerId, callerName, sessionId }

  const handleAcceptCall = useCallback(() => {
    if (!incomingCall) return;
    setIncomingCall(null);
    navigate(`/video-call/${incomingCall.sessionId}`);
  }, [incomingCall, navigate]);

  const handleDeclineCall = useCallback(() => {
    setIncomingCall(null);
  }, []);

  // Persistent WebSocket for incoming call notifications — auto-reconnects
  useEffect(() => {
    if (!user?.id) return;

    const connect = () => {
      const ws = new WebSocket(
        `ws://127.0.0.1:8000/api/therapy-sessions/ws/call/${user.id}?user_type=patient`
      );

      ws.onopen = () => {
        console.log('[CallNotify] Connected');
        clearTimeout(reconnectRef.current);
      };

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

      ws.onclose = () => {
        console.log('[CallNotify] Disconnected — reconnecting in 5s');
        reconnectRef.current = setTimeout(connect, 5000);
      };

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

  // Fetch therapy session transcripts when section is opened
  useEffect(() => {
    if (activeSection === 'sessions' && sessions.length === 0) {
      setSessionsLoading(true);
      setSessionsError('');
      getMyTherapySessions()
        .then((data) => setSessions(data))
        .catch((err) => setSessionsError(typeof err === 'string' ? err : 'Failed to load sessions'))
        .finally(() => setSessionsLoading(false));
    }
  }, [activeSection]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleOCDToolsClick = () => {
    navigate('/patient/dashboard/tools/ocd');
  };

  const handleProgressClick = () => {
    navigate('/patient/dashboard/progress');
  };

  const handleNirbaanAIClick = () => {
    navigate('/patient/nirbaanai');
  };

  return (
    <div className="patient-dashboard-container">
      {incomingCall && (
        <IncomingCallModal
          callerName={incomingCall.callerName}
          onAccept={handleAcceptCall}
          onDecline={handleDeclineCall}
        />
      )}
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header with Navigation */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Nirbaan</h1>
          <nav className="nav-menu">
            <button
              className={`nav-btn ${activeSection === 'live_sessions' ? 'active' : ''}`}
              onClick={() => setActiveSection('live_sessions')}
            >
              Live Sessions
            </button>
            <button
              className={`nav-btn ${activeSection === 'sessions' ? 'active' : ''}`}
              onClick={() => setActiveSection('sessions')}
            >
              Sessions
            </button>
            <button
              className="nav-btn"
              onClick={handleProgressClick}
            >
              Progress
            </button>
            <button
              className={`nav-btn ${activeSection === 'homework' ? 'active' : ''}`}
              onClick={() => setActiveSection('homework')}
            >
              Homework
            </button>
            <button
              className={`nav-btn ${activeSection === 'resources' ? 'active' : ''}`}
              onClick={() => setActiveSection('resources')}
            >
              Resources
            </button>
            <button
              className="nav-btn"
              onClick={handleOCDToolsClick}
            >
              Tools
            </button>
            <button
              className={`nav-btn ${activeSection === 'mindfulness' ? 'active' : ''}`}
              onClick={() => setActiveSection('mindfulness')}
            >
              Mindfulness
            </button>
            <button
              className="nav-btn"
              onClick={() => navigate('/patient/chat')}
            >
              Chat
            </button>
            <button
              className="nav-btn nav-btn-ai"
              onClick={handleNirbaanAIClick}
            >
              NirbaanAI
            </button>
          </nav>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      {/* Video Call Button - Only on landing page */}
      {!activeSection && (
        <button className="video-call-btn" title="Start Video Call">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
          </svg>
        </button>
      )}

      {/* Main Content */}
      <main className="dashboard-main">
        {activeSection === 'live_sessions' && (
          <div className="empty-section">
            {/* Live Sessions section - video call sessions */}
          </div>
        )}

        {activeSection === 'sessions' && (
          <div className="pd-sessions-panel">
            <h2 className="pd-sessions-title">My Therapy Sessions</h2>

            {sessionsLoading && (
              <div className="pd-sessions-loading">
                <div className="spinner"></div>
                <p>Loading sessions...</p>
              </div>
            )}

            {sessionsError && (
              <div className="pd-sessions-error">{sessionsError}</div>
            )}

            {!sessionsLoading && !sessionsError && sessions.length === 0 && (
              <div className="pd-sessions-empty">
                <p>No sessions have been added yet. Your therapist will log sessions here after each appointment.</p>
              </div>
            )}

            {!sessionsLoading && sessions.map((s) => (
              <div key={s.id} className="pd-session-card">
                <button
                  className="pd-session-header"
                  onClick={() => setExpandedSession(expandedSession === s.id ? null : s.id)}
                >
                  <div className="pd-session-meta">
                    <span className="pd-session-badge">Session {s.session_number}</span>
                    <span className="pd-session-title-text">{s.title}</span>
                    <span className="pd-session-date">
                      {new Date(s.session_date).toLocaleDateString('en-US', {
                        year: 'numeric', month: 'long', day: 'numeric',
                      })}
                    </span>
                  </div>
                  <span className="pd-session-chevron">{expandedSession === s.id ? '▲' : '▼'}</span>
                </button>

                {expandedSession === s.id && (
                  <div className="pd-session-body">
                    <h4 className="pd-section-label">Session Transcript</h4>
                    <pre className="pd-session-transcript">{s.transcript}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeSection === 'homework' && (
          <div className="section-content">
            <PatientHomework />
          </div>
        )}

        {activeSection === 'resources' && (
          <div className="pd-resources-panel">
            <PatientResourceLibrary />
          </div>
        )}

        {activeSection === 'mindfulness' && (
          <div className="empty-section">
            {/* Empty Mindfulness section */}
          </div>
        )}
      </main>
    </div>
  );
};

export default PatientDashboard;
