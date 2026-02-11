import { useState, useEffect } from 'react';
import { getMySessions, getSessionDetail } from '../api/session.api';
import './SessionTracker.css';

const SessionTracker = () => {
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchMySessions();
  }, []);

  const fetchMySessions = async () => {
    try {
      setLoading(true);
      const data = await getMySessions();
      setSessions(data);
      
      if (data.length > 0) {
        handleSelectSession(data[0].id);
      }
    } catch (err) {
      setError('Failed to load sessions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSession = async (sessionId) => {
    try {
      setSelectedSessionId(sessionId);
      const sessionDetail = await getSessionDetail(sessionId);
      setSelectedSession(sessionDetail);
      setError('');
    } catch (err) {
      setError('Failed to load session details');
      console.error(err);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  if (loading) {
    return (
      <div className="session-tracker-wrapper">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading sessions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="session-tracker-wrapper">
      {/* Header */}
      <div className="session-tracker-header">
        <div className="header-ornament header-ornament-left"></div>
        <h1 className="session-tracker-title">My Sessions</h1>
        <div className="header-ornament header-ornament-right"></div>
      </div>

      {/* Main Layout */}
      <div className="session-tracker-layout">
        {/* Left Sidebar - Session List */}
        <div className="session-tracker-sidebar">
          <div className="sidebar-title">Session Records</div>
          <div className="session-tracker-entry-list">
            {sessions.length === 0 ? (
              <div className="no-entries">No sessions yet</div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.id}
                  className={`session-tracker-entry-item ${selectedSessionId === session.id ? 'active' : ''}`}
                  onClick={() => handleSelectSession(session.id)}
                >
                  <span className="entry-bullet">◆</span>
                  <div className="entry-content">
                    <span className="entry-label">Week {session.week_number}</span>
                    <span className="entry-date">{formatDate(session.session_date)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Main Content */}
        <div className="session-tracker-detail-main">
          {!selectedSession ? (
            <div className="no-selection">
              <div className="no-selection-icon">📝</div>
              <h3>Select a Session</h3>
              <p>Choose a session from the left to view transcript</p>
            </div>
          ) : (
            <div className="session-tracker-detail-content">
              {error && <div className="alert alert-error">{error}</div>}

              {/* Session Title */}
              <div className="content-section">
                <h2 className="section-heading">Week {selectedSession.week_number} Session</h2>
                <p className="session-date">{formatDate(selectedSession.session_date)}</p>
                <div className="decorative-separator"></div>
              </div>

              {/* Transcript */}
              <div className="content-section">
                <h3 className="subsection-title">Session Transcript</h3>
                <div className="content-display-box">
                  <p className="content-display-text">{selectedSession.transcript}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SessionTracker;
