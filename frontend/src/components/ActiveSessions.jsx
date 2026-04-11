import { useState, useEffect } from 'react';
import {
  getActiveSessionsWithHomeworks,
  updateSessionHomeworks,
  approveSessionHomeworks
} from '../api/homework.api';
import { sendLiveSessionTranscriptToTherapySession } from '../api/sessions.api';
import './ActiveSessions.css';

const ActiveSessions = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingSession, setEditingSession] = useState(null);
  const [editHomeworks, setEditHomeworks] = useState([]);
  const [savingSession, setSavingSession] = useState(null);
  const [expandedTranscript, setExpandedTranscript] = useState(null);
  const [sendingSession, setSendingSession] = useState(null);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      setError('');
      const { data } = await getActiveSessionsWithHomeworks();
      setSessions(data);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to fetch sessions');
    } finally {
      setLoading(false);
    }
  };

  const handleEditClick = (session) => {
    setEditingSession(session.session_id);
    setEditHomeworks([...session.homeworks]);
  };

  const handleCancelEdit = () => {
    setEditingSession(null);
    setEditHomeworks([]);
  };

  const handleHomeworkChange = (index, field, value) => {
    const updated = [...editHomeworks];
    updated[index] = { ...updated[index], [field]: value };
    setEditHomeworks(updated);
  };

  const handleAddHomework = () => {
    setEditHomeworks([...editHomeworks, { task: '', rationale: '', frequency: '' }]);
  };

  const handleRemoveHomework = (index) => {
    setEditHomeworks(editHomeworks.filter((_, i) => i !== index));
  };

  const handleSaveEdit = async () => {
    try {
      setSavingSession(editingSession);
      await updateSessionHomeworks(editingSession, editHomeworks);
      setEditingSession(null);
      setEditHomeworks([]);
      await fetchSessions();
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to save homeworks');
    } finally {
      setSavingSession(null);
    }
  };

  const handleApprove = async (sessionId, homeworks) => {
    if (homeworks.length === 0) {
      setError('No homeworks to approve');
      return;
    }
    try {
      setSavingSession(sessionId);
      await approveSessionHomeworks(sessionId, homeworks);
      await fetchSessions();
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to approve homeworks');
    } finally {
      setSavingSession(null);
    }
  };

  const handleSendToActiveSession = async (session) => {
    if (session.transcripts.length === 0) {
      setError('No transcript available for this session.');
      return;
    }
    try {
      setSendingSession(session.session_id);
      await sendLiveSessionTranscriptToTherapySession(session.session_id);
      // Refresh so the button becomes permanently disabled from server state
      await fetchSessions();
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to send transcript');
    } finally {
      setSendingSession(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="as-page">
      <div className="as-shell">
        <div className="as-topbar">
          <div className="as-brand">
            <div className="as-brandDot" />
            <div>
              <h1 className="as-title">Session Reviews</h1>
              <p className="as-subtitle">Review AI-generated homeworks and approve for patients</p>
            </div>
          </div>
          <button className="as-refreshBtn" onClick={fetchSessions} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {error && (
          <div className="as-errorBanner">
            <span>{error}</span>
            <button onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        <div className="as-content">
          {loading ? (
            <div className="as-state">
              <div className="as-spinner" />
              <p>Loading sessions...</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="as-empty">
              <div className="as-emptyIcon">📋</div>
              <h3>No completed sessions</h3>
              <p>Sessions with AI-generated homeworks will appear here after they end.</p>
            </div>
          ) : (
            <div className="as-sessionsList">
              {sessions.map((session) => (
                <div key={session.session_id} className="as-sessionCard">
                  <div className="as-sessionHeader">
                    <div className="as-sessionInfo">
                      <div className="as-avatar">
                        {session.patient_name.slice(0, 1).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="as-patientName">{session.patient_name}</h3>
                        <div className="as-sessionMeta">
                          <span>{formatDate(session.started_at)}</span>
                          <span className="as-dot">•</span>
                          <span>{session.transcript_count} transcript entries</span>
                        </div>
                      </div>
                    </div>
                    <div className="as-sessionStatus">
                      {session.approved_count > 0 ? (
                        <span className="as-badge as-approved">
                          {session.approved_count} Approved
                        </span>
                      ) : (
                        <span className="as-badge as-pending">Pending Review</span>
                      )}
                    </div>
                  </div>

                  {session.transcripts && session.transcripts.length > 0 && (
                    <div className="as-transcriptSection">
                      <div className="as-transcriptHeader">
                        <strong>Session Transcript:</strong>
                        <span className="as-transcriptCount">{session.transcripts.length} entries</span>
                      </div>
                      <div className="as-transcriptList">
                        {(expandedTranscript === session.session_id
                          ? session.transcripts
                          : session.transcripts.slice(0, 3)
                        ).map((t, idx) => (
                          <div key={t.id || idx} className={`as-transcriptItem as-speaker-${t.speaker}`}>
                            <span className="as-speakerLabel">{t.speaker}:</span>
                            <span className="as-transcriptText">{t.text}</span>
                          </div>
                        ))}
                      </div>
                      {session.transcripts.length > 3 && (
                        <button
                          className="as-readMoreBtn"
                          onClick={() => setExpandedTranscript(
                            expandedTranscript === session.session_id ? null : session.session_id
                          )}
                        >
                          {expandedTranscript === session.session_id
                            ? 'Show Less'
                            : `Read More (${session.transcripts.length - 3} more entries)`}
                        </button>
                      )}
                    </div>
                  )}

                  <div className="as-homeworksSection">
                    <h4 className="as-homeworksTitle">
                      AI-Generated Homeworks ({session.homeworks.length})
                    </h4>

                    {editingSession === session.session_id ? (
                      <div className="as-editMode">
                        {editHomeworks.map((hw, idx) => (
                          <div key={idx} className="as-homeworkEditItem">
                            <div className="as-editField">
                              <label>Task</label>
                              <textarea
                                value={hw.task}
                                onChange={(e) => handleHomeworkChange(idx, 'task', e.target.value)}
                                placeholder="Describe the homework task..."
                              />
                            </div>
                            <div className="as-editField">
                              <label>Rationale</label>
                              <textarea
                                value={hw.rationale}
                                onChange={(e) => handleHomeworkChange(idx, 'rationale', e.target.value)}
                                placeholder="Why this homework is beneficial..."
                              />
                            </div>
                            <div className="as-editField">
                              <label>Frequency</label>
                              <input
                                type="text"
                                value={hw.frequency}
                                onChange={(e) => handleHomeworkChange(idx, 'frequency', e.target.value)}
                                placeholder="e.g., Daily, 3x per week"
                              />
                            </div>
                            <button
                              className="as-removeBtn"
                              onClick={() => handleRemoveHomework(idx)}
                            >
                              Remove
                            </button>
                          </div>
                        ))}

                        <button className="as-addBtn" onClick={handleAddHomework}>
                          + Add Homework
                        </button>

                        <div className="as-editActions">
                          <button
                            className="as-saveBtn"
                            onClick={handleSaveEdit}
                            disabled={savingSession === session.session_id}
                          >
                            {savingSession === session.session_id ? 'Saving...' : 'Save Changes'}
                          </button>
                          <button className="as-cancelBtn" onClick={handleCancelEdit}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="as-viewMode">
                        {session.homeworks.length === 0 ? (
                          <div className="as-noHomeworks">
                            No homeworks generated for this session.
                          </div>
                        ) : (
                          <div className="as-homeworksList">
                            {session.homeworks.map((hw, idx) => (
                              <div key={idx} className="as-homeworkItem">
                                <div className="as-homeworkTask">{hw.task}</div>
                                <div className="as-homeworkRationale">{hw.rationale}</div>
                                <div className="as-homeworkFrequency">
                                  <span className="as-freqLabel">Frequency:</span> {hw.frequency}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="as-actions">
                          <button
                            className="as-editBtn"
                            onClick={() => handleEditClick(session)}
                          >
                            Edit Homeworks
                          </button>
                          <button
                            className="as-sendSessionBtn"
                            onClick={() => handleSendToActiveSession(session)}
                            disabled={
                              sendingSession === session.session_id ||
                              session.sent_to_active_session ||
                              session.transcripts.length === 0
                            }
                          >
                            {sendingSession === session.session_id
                              ? 'Sending...'
                              : session.sent_to_active_session
                                ? 'Already Sent'
                                : 'Send in Active Session'}
                          </button>
                          <button
                            className="as-approveBtn"
                            onClick={() => handleApprove(session.session_id, session.homeworks)}
                            disabled={savingSession === session.session_id || session.approved_count > 0 || session.homeworks.length === 0}
                          >
                            {savingSession === session.session_id
                              ? 'Approving...'
                              : session.approved_count > 0
                                ? 'Already Approved'
                                : 'Approve & Assign to Patient'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ActiveSessions;
