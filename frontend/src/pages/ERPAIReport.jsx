import { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { listItemSessions, getSessionDetail } from '../api/erp.api';
import '../dashboards/PatientDashboard.css';
import './ERPAIReport.css';

const fmt = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
};
const fmtTime = (sec) => {
  if (!sec && sec !== 0) return '—';
  const s = Math.max(0, Math.round(sec));
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${m}m ${ss}s`;
};

const ERPAIReport = () => {
  const navigate   = useNavigate();
  const { itemId } = useParams();
  const location   = useLocation();
  const { logout } = useAuthStore();

  const obsession = location.state?.obsession || 'Your obsession';

  const [sessions, setSessions]         = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState('');
  const [selectedId, setSelectedId]     = useState(null);
  const [detail, setDetail]             = useState(null);   // ERPSessionDetailResponse
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    listItemSessions(Number(itemId))
      .then(({ data }) => {
        setSessions(data);
        // Pre-select latest ended session that has a report
        const latest = data.find((s) => s.status === 'ended' && s.patient_feedback_json);
        if (latest) setSelectedId(latest.id);
      })
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load sessions.'))
      .finally(() => setLoading(false));
  }, [itemId]);

  useEffect(() => {
    if (!selectedId) return;
    setDetail(null);
    setDetailLoading(true);
    getSessionDetail(selectedId)
      .then(({ data }) => setDetail(data))
      .catch(() => { /* silent */ })
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  const endedWithReport = sessions.filter((s) => s.status === 'ended');

  const handleLogout = () => { logout(); navigate('/select-role'); };

  return (
    <div className="air-root">
      {/* Background */}
      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      {/* Header */}
      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>Session Reports</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={() => navigate('/patient/dashboard/erp/dive-in')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      <main className="ai-report-main air-main-wide">
        {/* Obsession context */}
        <div className="ai-report-context">
          <span className="ai-report-context-label">Obsession</span>
          <p className="ai-report-context-text">{obsession}</p>
        </div>

        {error && <div className="air-error">{error}</div>}

        {loading ? (
          <div className="air-loading">Loading sessions…</div>
        ) : sessions.length === 0 ? (
          <div className="air-empty-state">
            <div className="air-empty-icon"></div>
            <p>No sessions found for this obsession yet.</p>
            <button
              className="ai-report-ghost-btn"
              onClick={() => navigate(`/patient/dashboard/erp/session/${itemId}`)}
            >
              Start Your First Session →
            </button>
          </div>
        ) : (
          <div className="air-split">
            {/* ── Session list ── */}
            <aside className="air-session-list">
              <h3 className="air-list-title">Sessions ({sessions.length})</h3>
              {sessions.map((s) => (
                <button
                  key={s.id}
                  className={`air-session-item ${selectedId === s.id ? 'air-session-item--active' : ''}`}
                  onClick={() => setSelectedId(s.id)}
                >
                  <div className="air-si-date">{fmt(s.created_at)}</div>
                  <div className="air-si-meta">
                    <span className={`air-si-status air-si-status--${s.status}`}>{s.status}</span>
                    <span className="air-si-duration">{fmtTime(s.accumulated_seconds)}</span>
                  </div>
                  {s.patient_feedback_json && (
                    <span className="air-si-report-badge">Report</span>
                  )}
                </button>
              ))}
            </aside>

            {/* ── Detail panel ── */}
            <section className="air-detail-panel">
              {!selectedId && (
                <div className="air-detail-placeholder">
                  <span className="air-detail-placeholder-icon"></span>
                  <p>Select a session to view its report.</p>
                </div>
              )}

              {selectedId && detailLoading && (
                <div className="air-detail-loading">Loading report…</div>
              )}

              {selectedId && !detailLoading && detail && (
                <div className="air-detail-content">
                  {/* Session meta */}
                  <div className="air-detail-meta">
                    <div className="air-detail-meta-row">
                      <span className="air-meta-label">Date</span>
                      <span className="air-meta-value">{fmt(detail.session.created_at)}</span>
                    </div>
                    <div className="air-detail-meta-row">
                      <span className="air-meta-label">Duration</span>
                      <span className="air-meta-value">{fmtTime(detail.session.accumulated_seconds)}</span>
                    </div>
                    <div className="air-detail-meta-row">
                      <span className="air-meta-label">Status</span>
                      <span className={`air-si-status air-si-status--${detail.session.status}`}>
                        {detail.session.status}
                      </span>
                    </div>
                    {detail.suds_readings?.length > 0 && (
                      <div className="air-detail-meta-row">
                        <span className="air-meta-label">SUDS Readings</span>
                        <span className="air-meta-value">{detail.suds_readings.length}</span>
                      </div>
                    )}
                  </div>

                  {/* No report yet */}
                  {!detail.patient_feedback && (
                    <div className="air-no-report">
                      <span>No AI report for this session yet.</span>
                      {detail.session.status !== 'ended' && (
                        <p className="air-no-report-hint">
                          Complete the session and submit your debrief to generate a report.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Patient feedback */}
                  {detail.patient_feedback && (
                    <div className="air-feedback">
                      <h3 className="air-feedback-title">Your Session Feedback</h3>

                      {detail.patient_feedback.wins?.length > 0 && (
                        <div className="air-feedback-block">
                          <span className="air-fb-label">Wins From This Session</span>
                          <ul className="air-fb-list">
                            {detail.patient_feedback.wins.map((w, i) => <li key={i}>{w}</li>)}
                          </ul>
                        </div>
                      )}

                      {detail.patient_feedback.reflection?.length > 0 && (
                        <div className="air-feedback-block">
                          <span className="air-fb-label">Reflections</span>
                          <ul className="air-fb-list">
                            {detail.patient_feedback.reflection.map((r, i) => <li key={i}>{r}</li>)}
                          </ul>
                        </div>
                      )}

                      {detail.patient_feedback.skill_to_practice && (
                        <div className="air-feedback-block">
                          <span className="air-fb-label">Skill to Practice</span>
                          <p className="air-fb-text">{detail.patient_feedback.skill_to_practice}</p>
                        </div>
                      )}

                      {detail.patient_feedback.one_micro_goal_next_time && (
                        <div className="air-feedback-block">
                          <span className="air-fb-label">Next Session Goal</span>
                          <p className="air-fb-text">{detail.patient_feedback.one_micro_goal_next_time}</p>
                        </div>
                      )}

                      {detail.patient_feedback.reminder && (
                        <div className="air-feedback-reminder">
                          {detail.patient_feedback.reminder}
                        </div>
                      )}
                    </div>
                  )}

                  {/* SUDS mini-stats */}
                  {detail.suds_readings?.length > 0 && (
                    <div className="air-suds-stats">
                      <span className="air-fb-label">SUDS Summary</span>
                      <div className="air-suds-pills">
                        <span className="air-suds-pill air-suds-pill--first">
                          Start: {detail.suds_readings[0].suds_value}
                        </span>
                        <span className="air-suds-pill air-suds-pill--peak">
                          Peak: {Math.max(...detail.suds_readings.map((r) => r.suds_value))}
                        </span>
                        <span className="air-suds-pill air-suds-pill--end">
                          End: {detail.suds_readings[detail.suds_readings.length - 1].suds_value}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
};

export default ERPAIReport;
