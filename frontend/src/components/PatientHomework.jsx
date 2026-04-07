import { useState, useEffect } from 'react';
import { getMyHomeworks, markHomeworkComplete } from '../api/homework.api';
import './PatientHomework.css';

const PatientHomework = () => {
  const [homeworksByWeek, setHomeworksByWeek] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedWeek, setExpandedWeek] = useState(null);
  const [completingId, setCompletingId] = useState(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchHomeworks();
  }, []);

  const fetchHomeworks = async () => {
    try {
      setLoading(true);
      setError('');
      const { data } = await getMyHomeworks();
      setHomeworksByWeek(data);
      // Auto-expand first week
      if (data.length > 0) {
        setExpandedWeek(data[0].week_number);
      }
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to fetch homeworks');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (homeworkId) => {
    try {
      setSubmitting(true);
      await markHomeworkComplete(homeworkId, notes);
      setCompletingId(null);
      setNotes('');
      await fetchHomeworks();
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to mark homework complete');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelComplete = () => {
    setCompletingId(null);
    setNotes('');
  };

  const getStatusInfo = (status) => {
    const info = {
      active: { class: 'ph-statusActive', text: 'Active', icon: '📝' },
      completed: { class: 'ph-statusCompleted', text: 'Completed', icon: '✓' },
      skipped: { class: 'ph-statusSkipped', text: 'Skipped', icon: '⏭' }
    };
    return info[status] || info.active;
  };

  const getWeekProgress = (homeworks) => {
    const completed = homeworks.filter(h => h.status === 'completed').length;
    return { completed, total: homeworks.length };
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="ph-page">
      <div className="ph-shell">
        <div className="ph-topbar">
          <div className="ph-brand">
            <div>
              <h1 className="ph-titleMain">My Homework</h1>
              <p className="ph-subtitleMain">Track and complete your therapy assignments</p>
            </div>
          </div>
          <button className="ph-refreshBtn" onClick={fetchHomeworks} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {error && (
          <div className="ph-errorBanner">
            <span>{error}</span>
            <button onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        <div className="ph-content">
          {loading ? (
            <div className="ph-stateMain">
              <div className="ph-spinnerMain" />
              <p>Loading your homeworks...</p>
            </div>
          ) : homeworksByWeek.length === 0 ? (
            <div className="ph-emptyMain">
              <div className="ph-emptyIconMain">📚</div>
              <h3>No homework yet</h3>
              <p>Your therapist will assign homework after your therapy sessions.</p>
            </div>
          ) : (
            <div className="ph-weeksList">
              {homeworksByWeek.map((week) => {
                const progress = getWeekProgress(week.homeworks);
                const isExpanded = expandedWeek === week.week_number;

                return (
                  <div key={week.week_number} className="ph-weekCard">
                    <button
                      className={`ph-weekHeader ${isExpanded ? 'expanded' : ''}`}
                      onClick={() => setExpandedWeek(isExpanded ? null : week.week_number)}
                    >
                      <div className="ph-weekInfo">
                        <h3>Week {week.week_number}</h3>
                        <span className="ph-weekCount">
                          {progress.completed}/{progress.total} completed
                        </span>
                      </div>
                      <div className="ph-weekRight">
                        <div className="ph-progressBar">
                          <div
                            className="ph-progressFill"
                            style={{ width: `${(progress.completed / progress.total) * 100}%` }}
                          />
                        </div>
                        <span className={`ph-chevron ${isExpanded ? 'up' : 'down'}`}>▼</span>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="ph-weekContent">
                        {week.homeworks.map((hw) => {
                          const statusInfo = getStatusInfo(hw.status);
                          const isCompleting = completingId === hw.id;

                          return (
                            <div key={hw.id} className={`ph-homeworkCard ${hw.status}`}>
                              <div className="ph-homeworkHeader">
                                <span className={`ph-statusBadge ${statusInfo.class}`}>
                                  <span className="ph-statusIcon">{statusInfo.icon}</span>
                                  {statusInfo.text}
                                </span>
                                <span className="ph-frequency">{hw.frequency}</span>
                              </div>

                              <div className="ph-homeworkBody">
                                <h4 className="ph-taskTitle">{hw.task}</h4>
                                <p className="ph-taskRationale">{hw.rationale}</p>
                              </div>

                              {hw.status === 'active' && (
                                isCompleting ? (
                                  <div className="ph-completeForm">
                                    <textarea
                                      placeholder="Add notes about how it went (optional)"
                                      value={notes}
                                      onChange={(e) => setNotes(e.target.value)}
                                    />
                                    <div className="ph-completeActions">
                                      <button
                                        className="ph-completeBtn"
                                        onClick={() => handleComplete(hw.id)}
                                        disabled={submitting}
                                      >
                                        {submitting ? 'Saving...' : 'Mark Complete'}
                                      </button>
                                      <button
                                        className="ph-cancelCompleteBtn"
                                        onClick={handleCancelComplete}
                                      >
                                        Cancel
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <button
                                    className="ph-markCompleteBtn"
                                    onClick={() => setCompletingId(hw.id)}
                                  >
                                    Mark as Complete
                                  </button>
                                )
                              )}

                              {hw.status === 'completed' && hw.completed_at && (
                                <div className="ph-completedInfo">
                                  Completed on {formatDate(hw.completed_at)}
                                </div>
                              )}

                              {hw.patient_notes && (
                                <div className="ph-patientNotes">
                                  <strong>My notes:</strong> {hw.patient_notes}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatientHomework;
