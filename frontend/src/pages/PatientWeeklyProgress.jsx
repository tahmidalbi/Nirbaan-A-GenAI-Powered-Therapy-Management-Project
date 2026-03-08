import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMyProgress, createWeeklyProgress } from '../api/progress.api';
import { getMyFearLadder } from '../api/fear-ladder.api';
import './PatientWeeklyProgress.css';

const PatientWeeklyProgress = () => {
  const navigate = useNavigate();
  const [view, setView] = useState('history'); // 'history' | 'form'
  const [progressHistory, setProgressHistory] = useState([]);
  const [ladderItems, setLadderItems] = useState([]);
  const [ladderStatus, setLadderStatus] = useState(null);
  const [expandedCard, setExpandedCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [detailedProgress, setDetailedProgress] = useState('');
  const [homeworkReflection, setHomeworkReflection] = useState('');
  const [sudsValues, setSudsValues] = useState({}); // { item_id: suds_value }

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [progressRes, ladderRes] = await Promise.allSettled([
        getMyProgress(),
        getMyFearLadder(),
      ]);

      if (progressRes.status === 'fulfilled') {
        setProgressHistory(progressRes.value);
      }

      if (ladderRes.status === 'fulfilled' && ladderRes.value?.data) {
        const ladder = ladderRes.value.data;
        setLadderStatus(ladder.status);
        if (ladder.items && ladder.items.length > 0) {
          const sorted = [...ladder.items].sort((a, b) => a.suds - b.suds);
          setLadderItems(sorted);
          // Initialize suds values with current ladder suds
          const initial = {};
          sorted.forEach((item) => {
            initial[item.id] = item.suds;
          });
          setSudsValues(initial);
        }
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load your progress data.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenForm = () => {
    setDetailedProgress('');
    setHomeworkReflection('');
    // Reset suds values to current ladder values
    const initial = {};
    ladderItems.forEach((item) => {
      initial[item.id] = item.suds;
    });
    setSudsValues(initial);
    setError('');
    setView('form');
  };

  const handleSudsChange = (itemId, value) => {
    const parsed = parseInt(value, 10);
    setSudsValues((prev) => ({
      ...prev,
      [itemId]: isNaN(parsed) ? 0 : Math.min(100, Math.max(0, parsed)),
    }));
  };

  const handleSubmit = async () => {
    if (!detailedProgress.trim()) {
      setError('Please describe your progress this week.');
      return;
    }
    if (!homeworkReflection.trim()) {
      setError('Please reflect on your homework this week.');
      return;
    }

    setSubmitting(true);
    setError('');

    const today = new Date().toISOString().split('T')[0];

    // Build SUDS snapshot
    const sudsSnapshot = ladderItems.map((item) => ({
      item_id: item.id,
      item_text: item.item,
      suds: sudsValues[item.id] ?? item.suds,
    }));

    try {
      await createWeeklyProgress({
        week_start_date: today,
        detailed_progress: detailedProgress,
        homework_reflection: homeworkReflection,
        suds_snapshot: sudsSnapshot.length > 0 ? sudsSnapshot : null,
      });

      // Refresh history and go back to history view
      await fetchData();
      setView('history');
    } catch (err) {
      console.error('Failed to submit progress:', err);
      setError(typeof err === 'string' ? err : 'Failed to submit your update. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleCard = (id) => {
    setExpandedCard((prev) => (prev === id ? null : id));
  };

  if (loading) {
    return (
      <div className="progress-page-container">
        <div className="progress-background">
          <div className="geometric-pattern"></div>
        </div>
        <div className="progress-loading">
          <div className="progress-spinner"></div>
          <p>Loading your progress...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="progress-page-container">
      <div className="progress-background">
        <div className="geometric-pattern"></div>
      </div>

      <div className="progress-content">
        <div className="progress-header">
          <button className="progress-back-btn" onClick={() => navigate('/patient/dashboard')}>
            &larr; Back to Dashboard
          </button>
          <h1 className="progress-title">Weekly Progress</h1>
          {view === 'history' && (
            <button className="progress-add-btn" onClick={handleOpenForm}>
              + Add This Week's Update
            </button>
          )}
          {view === 'form' && (
            <button className="progress-cancel-btn" onClick={() => { setView('history'); setError(''); }}>
              Cancel
            </button>
          )}
        </div>

        {error && <div className="progress-error">{error}</div>}

        {/* ── FORM VIEW ── */}
        {view === 'form' && (
          <div className="progress-form-wrapper">
            <h2 className="form-section-title">This Week's Update</h2>

            {/* Box 1 – detailed progress */}
            <div className="progress-form-box">
              <label className="form-box-label">How did your week go?</label>
              <p className="form-box-hint">
                Write freely about your experiences, feelings, challenges, and wins this week. There are no right or wrong answers.
              </p>
              <textarea
                className="progress-textarea"
                rows={8}
                placeholder="Describe your week in as much detail as you'd like..."
                value={detailedProgress}
                onChange={(e) => setDetailedProgress(e.target.value)}
              />
            </div>

            {/* Box 2 – homework reflection */}
            <div className="progress-form-box">
              <label className="form-box-label">Therapy Homework Reflection</label>
              <p className="form-box-hint">
                Did you complete all your homework tasks? What difficulties did you face? How successful or challenging was it overall?
              </p>
              <textarea
                className="progress-textarea"
                rows={6}
                placeholder="Reflect on your homework — what you completed, what was hard, how you felt about your effort..."
                value={homeworkReflection}
                onChange={(e) => setHomeworkReflection(e.target.value)}
              />
            </div>

            {/* SUDS Snapshot */}
            <div className="progress-form-box">
              <label className="form-box-label">Fear Ladder – This Week's SUDS Levels</label>
              <p className="form-box-hint">
                Rate your current distress (0–100) for each item on your fear ladder. This is a snapshot for your therapist
                and will <strong>not</strong> change your official fear ladder.
              </p>

              {ladderItems.length === 0 ? (
                <div className="no-ladder-notice">
                  {ladderStatus === null
                    ? 'You do not have an approved fear ladder yet. Complete and submit your fear ladder first.'
                    : ladderStatus !== 'approved'
                    ? 'Your fear ladder is pending therapist approval. SUDS snapshot will be available once it is approved.'
                    : 'Your fear ladder has no items.'}
                </div>
              ) : (
                <div className="suds-snapshot-table">
                  <div className="suds-table-header">
                    <span>Obsession / Situation</span>
                    <span>Original SUDS</span>
                    <span>This Week's SUDS</span>
                  </div>
                  {ladderItems.map((item) => (
                    <div key={item.id} className="suds-table-row">
                      <span className="suds-item-text">{item.item}</span>
                      <span className="suds-original">{item.suds}</span>
                      <div className="suds-input-wrapper">
                        <input
                          type="number"
                          min={0}
                          max={100}
                          className="suds-input"
                          value={sudsValues[item.id] ?? item.suds}
                          onChange={(e) => handleSudsChange(item.id, e.target.value)}
                        />
                        <div
                          className="suds-bar"
                          style={{ width: `${sudsValues[item.id] ?? item.suds}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              className="progress-submit-btn"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : 'Submit This Week\'s Update'}
            </button>
          </div>
        )}

        {/* ── HISTORY VIEW ── */}
        {view === 'history' && (
          <div className="progress-history-wrapper">
            {progressHistory.length === 0 ? (
              <div className="progress-empty">
                <p>You haven't submitted any weekly updates yet.</p>
                <p>Click <strong>+ Add This Week's Update</strong> to get started.</p>
              </div>
            ) : (
              progressHistory.map((entry) => (
                <div key={entry.id} className="progress-card">
                  <button
                    className="progress-card-header"
                    onClick={() => toggleCard(entry.id)}
                  >
                    <div className="progress-card-meta">
                      <span className="week-badge">Week {entry.week_number}</span>
                      <span className="week-date">
                        {new Date(entry.week_start_date).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    <span className="card-chevron">{expandedCard === entry.id ? '▲' : '▼'}</span>
                  </button>

                  {expandedCard === entry.id && (
                    <div className="progress-card-body">
                      <div className="card-section">
                        <h4>Weekly Progress</h4>
                        <p className="card-text">{entry.detailed_progress}</p>
                      </div>

                      <div className="card-section">
                        <h4>Homework Reflection</h4>
                        <p className="card-text">{entry.homework_reflection}</p>
                      </div>

                      {entry.suds_snapshot && entry.suds_snapshot.length > 0 && (
                        <div className="card-section">
                          <h4>Fear Ladder SUDS Snapshot</h4>
                          <div className="history-suds-table">
                            <div className="history-suds-header">
                              <span>Situation</span>
                              <span>SUDS</span>
                            </div>
                            {entry.suds_snapshot.map((snap, idx) => (
                              <div key={idx} className="history-suds-row">
                                <span>{snap.item_text}</span>
                                <span className="history-suds-value">{snap.suds}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <p className="card-submitted-at">
                        Submitted:{' '}
                        {new Date(entry.created_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientWeeklyProgress;
