import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPatientSessions, getSessionDetail, createSession, updateSession } from '../api/session.api';
import './TherapistSessionDetail.css';

const TherapistSessionDetail = () => {
  const { patientId } = useParams();
  const navigate = useNavigate();
  
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedTranscript, setEditedTranscript] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newWeekNumber, setNewWeekNumber] = useState(1);
  const [newTranscript, setNewTranscript] = useState('');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchSessions();
  }, [patientId]);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const data = await getPatientSessions(patientId);
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
      setEditedTranscript(sessionDetail.transcript);
      setIsEditing(false);
      setError('');
      setSuccess('');
    } catch (err) {
      setError('Failed to load session details');
      console.error(err);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedTranscript(selectedSession.transcript);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedTranscript(selectedSession.transcript);
  };

  const handleSave = async () => {
    if (!editedTranscript.trim()) {
      setError('Transcript cannot be empty');
      return;
    }

    try {
      setSaving(true);
      await updateSession(selectedSessionId, editedTranscript);
      setSuccess('Session updated successfully!');
      setIsEditing(false);
      
      // Refresh session data
      const updatedSession = await getSessionDetail(selectedSessionId);
      setSelectedSession(updatedSession);
    } catch (err) {
      setError('Failed to update session');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleAddSession = async () => {
    if (!newTranscript.trim()) {
      setError('Please enter a transcript');
      return;
    }

    try {
      setSaving(true);
      await createSession(parseInt(patientId), newWeekNumber, newTranscript);
      setSuccess('Session created successfully!');
      setNewTranscript('');
      setShowAddModal(false);
      
      // Refresh sessions list
      await fetchSessions();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create session');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const openAddModal = () => {
    // Calculate next week number
    const nextWeek = sessions.length > 0 
      ? Math.max(...sessions.map(s => s.week_number)) + 1 
      : 1;
    setNewWeekNumber(nextWeek);
    setNewTranscript('');
    setShowAddModal(true);
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
      <div className="therapist-session-detail-wrapper">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading sessions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="therapist-session-detail-wrapper">
      {/* Header */}
      <div className="session-detail-header">
        <button className="back-button" onClick={() => navigate('/therapist/dashboard')}>
          ← Back to Dashboard
        </button>
        <div className="header-ornament header-ornament-left"></div>
        <h1 className="session-detail-title">Session Transcripts</h1>
        <div className="header-ornament header-ornament-right"></div>
      </div>

      {/* Main Layout */}
      <div className="session-layout">
        {/* Left Sidebar - Session List */}
        <div className="session-sidebar">
          <div className="sidebar-title">Sessions</div>
          <div className="session-entry-list">
            {sessions.length === 0 ? (
              <div className="no-entries">No sessions yet</div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.id}
                  className={`session-entry-item ${selectedSessionId === session.id ? 'active' : ''}`}
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
        <div className="session-detail-main">
          {!selectedSession ? (
            <div className="no-selection">
              <div className="no-selection-icon">📝</div>
              <h3>Select a Session</h3>
              <p>Choose a session from the left to view transcript</p>
            </div>
          ) : (
            <div className="session-detail-content">
              {error && <div className="alert alert-error">{error}</div>}
              {success && <div className="alert alert-success">{success}</div>}

              {/* Session Title */}
              <div className="content-section">
                <h2 className="section-heading">Week {selectedSession.week_number} Transcript</h2>
                <p className="session-date">{formatDate(selectedSession.session_date)}</p>
                <div className="decorative-separator"></div>
              </div>

              {/* Transcript */}
              <div className="content-section">
                {isEditing ? (
                  <>
                    <textarea
                      className="session-textarea"
                      value={editedTranscript}
                      onChange={(e) => setEditedTranscript(e.target.value)}
                      rows="20"
                    />
                    <div className="action-buttons">
                      <button 
                        className="save-button"
                        onClick={handleSave}
                        disabled={saving}
                      >
                        {saving ? 'Saving...' : 'Save Changes'}
                      </button>
                      <button 
                        className="cancel-button"
                        onClick={handleCancelEdit}
                      >
                        Cancel
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="content-display-box">
                      <p className="content-display-text">{selectedSession.transcript}</p>
                    </div>
                    <button 
                      className="edit-button"
                      onClick={handleEdit}
                    >
                      Edit Transcript
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Session FAB */}
      <button 
        className="add-session-fab"
        onClick={openAddModal}
        title="Add New Session"
      >
        <span className="fab-plus">+</span>
      </button>

      {/* Add Session Modal */}
      {showAddModal && (
        <div className="add-session-modal">
          <div className="modal-overlay" onClick={() => setShowAddModal(false)}></div>
          <div className="modal-content">
            <div className="modal-header">
              <h3>Add Session Transcript - Week {newWeekNumber}</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>✕</button>
            </div>
            
            <div className="modal-body">
              <label className="modal-label">Session Transcript</label>
              <textarea
                className="modal-textarea"
                value={newTranscript}
                onChange={(e) => setNewTranscript(e.target.value)}
                placeholder="Enter the session transcript here...&#10;&#10;(This is dummy data for now. Will be integrated with video pipeline and LangGraph later.)"
                rows="15"
              />
            </div>
            
            <div className="modal-footer">
              <button className="modal-button modal-button-cancel" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
              <button 
                className="modal-button modal-button-save"
                onClick={handleAddSession}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Session'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TherapistSessionDetail;
