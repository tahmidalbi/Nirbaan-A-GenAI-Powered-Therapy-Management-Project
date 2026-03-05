import { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { therapistGetERPItemDetail, therapistListItemSessions, therapistGetSessionDetail, therapistGenerateCrossSessionOverview } from '../api/erp.api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import './TherapistERPPatientList.css'; // shared bg / header styles
import './TherapistERPObsessionView.css';

const TherapistERPObsessionView = () => {
  const navigate = useNavigate();
  const { patientId, itemId } = useParams();
  const location = useLocation();
  const { logout } = useAuthStore();

  const patientName  = location.state?.patientName  || 'Patient';
  const patientEmail = location.state?.patientEmail || '';

  const [item, setItem]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  // Session history
  const [sessions, setSessions]           = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [sessionDetail, setSessionDetail] = useState(null);
  const [sessionDetailLoading, setSessionDetailLoading] = useState(false);
  const [activeTab, setActiveTab]         = useState('sessions'); // 'sessions' | 'report'
  const [crossSessionLoading, setCrossSessionLoading] = useState(false);
  const [crossSessionError, setCrossSessionError]     = useState('');

  useEffect(() => {
    therapistGetERPItemDetail(patientId, itemId)
      .then(({ data }) => {
        setItem(data);
        // Load sessions after item loads
        setSessionsLoading(true);
        return therapistListItemSessions(patientId, itemId);
      })
      .then(({ data }) => {
        setSessions(data);
        // Pre-select latest ended session
        const latest = data.find((s) => s.status === 'ended');
        if (latest) setSelectedSessionId(latest.id);
      })
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load detail.'))
      .finally(() => { setLoading(false); setSessionsLoading(false); });
  }, [patientId, itemId]);

  useEffect(() => {
    if (!selectedSessionId) return;
    setSessionDetail(null);
    setSessionDetailLoading(true);
    setCrossSessionLoading(false);
    setCrossSessionError('');
    therapistGetSessionDetail(selectedSessionId)
      .then(({ data }) => setSessionDetail(data))
      .catch(() => {})
      .finally(() => setSessionDetailLoading(false));
  }, [selectedSessionId]);

  const handleBack = () =>
    navigate(`/therapist/dashboard/erp/patient/${patientId}`, {
      state: { patientName, patientEmail },
    });

  const handleGenerateCrossSession = async () => {
    if (!selectedSessionId) return;
    setCrossSessionLoading(true);
    setCrossSessionError('');
    try {
      const { data } = await therapistGenerateCrossSessionOverview(selectedSessionId);
      // If the result has no content (no prior session data was available), keep null
      const hasContent = data && (data.summary || data.common_patterns?.length > 0 || data.blockers_to_progress?.length > 0 || data.progress_signs?.length > 0);
      setSessionDetail((prev) => ({
        ...prev,
        therapist_report: {
          ...prev.therapist_report,
          cross_session_overview: hasContent ? data : null,
        },
      }));
      if (!hasContent) {
        setCrossSessionError('No prior session reports found to generate cross-session analysis from.');
      }
    } catch (err) {
      setCrossSessionError(typeof err === 'string' ? err : 'Failed to generate cross-session overview.');
    } finally {
      setCrossSessionLoading(false);
    }
  };

  return (
    <div className="terp-ov-container">
      {/* Background */}
      <div className="terp-bg">
        <div className="terp-bg-pattern" />
        <div className="terp-deco terp-deco-top" />
        <div className="terp-deco terp-deco-bottom" />
      </div>

      {/* Header */}
      <header className="terp-header">
        <div className="terp-header-inner">
          <button className="terp-ghost-btn" onClick={handleBack}>← Back</button>
          <div className="terp-header-title">
            <h1 className="terp-logo">ERP Detail</h1>
            <p className="terp-header-sub">{patientName}{patientEmail ? ` · ${patientEmail}` : ''}</p>
          </div>
          <button className="terp-ghost-btn" onClick={() => { logout(); navigate('/login'); }}>
            Logout
          </button>
        </div>
      </header>

      <main className="terp-ov-main">
        {error && <div className="terp-ov-error">{error}</div>}

        {loading ? (
          <div className="terp-ov-loading">Loading…</div>
        ) : !item ? null : (
          <div className="terp-ov-split">
            {/* ── LEFT PANEL ── */}
            <section className="terp-ov-left">
              {/* Obsession */}
              <div className="terp-ov-section">
                <h2 className="terp-ov-section-title">Obsession</h2>
                <p className="terp-ov-obsession-text">{item.obsession}</p>
                {item.suds !== null && item.suds !== undefined && (
                  <div className="terp-ov-suds-pill">
                    Baseline SUDS&nbsp;<strong>{item.suds}</strong>
                  </div>
                )}
              </div>

              {/* Compulsions */}
              <div className="terp-ov-section">
                <h2 className="terp-ov-section-title">
                  Compulsions&nbsp;
                  <span className="terp-ov-count">({item.compulsions?.length ?? 0})</span>
                </h2>
                {!item.compulsions?.length ? (
                  <p className="terp-ov-empty-note">No compulsions recorded.</p>
                ) : (
                  <ul className="terp-ov-comp-list">
                    {item.compulsions.map((c, i) => (
                      <li key={i} className="terp-ov-comp-item">
                        <span className="terp-ov-comp-dot" />
                        {c}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* SUDS history – chart */}
              <div className="terp-ov-section">
                <h2 className="terp-ov-section-title">
                  SUDS Over Time&nbsp;
                  <span className="terp-ov-count">({item.suds_readings?.length ?? 0} readings)</span>
                </h2>
                {!item.suds_readings?.length ? (
                  <p className="terp-ov-empty-note">No SUDS readings recorded yet.</p>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={220}>
                      <LineChart
                        data={item.suds_readings.map((r, i) => ({
                          idx: i + 1,
                          suds: r.suds_value,
                          time: `${r.elapsed_seconds.toFixed(0)}s`,
                        }))}
                        margin={{ top: 8, right: 10, left: -10, bottom: 16 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(44,95,77,0.12)" />
                        <XAxis
                          dataKey="idx"
                          stroke="#7aab96"
                          tick={{ fontSize: 11, fill: '#4a7c63' }}
                          label={{ value: 'Reading #', position: 'insideBottom', offset: -8, fontSize: 11, fill: '#7aab96' }}
                        />
                        <YAxis
                          domain={[0, 100]}
                          stroke="#7aab96"
                          tick={{ fontSize: 11, fill: '#4a7c63' }}
                        />
                        <ReferenceLine y={item.suds} stroke="#fbbf24" strokeDasharray="4 3" label={{ value: `Baseline ${item.suds}`, position: 'right', fontSize: 10, fill: '#b45309' }} />
                        <Tooltip
                          contentStyle={{ background: '#fff', border: '1px solid rgba(44,95,77,0.2)', borderRadius: 8, fontSize: 12 }}
                          formatter={(val, _n, props) => [`SUDS: ${val}`, `@ ${props.payload.time}`]}
                          labelFormatter={(label) => `Reading #${label}`}
                        />
                        <Line
                          type="monotone"
                          dataKey="suds"
                          stroke="#2C5F4D"
                          strokeWidth={2}
                          dot={{ fill: '#2C5F4D', r: 4 }}
                          activeDot={{ r: 6, fill: '#4a9b7e' }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                    {/* min / max / last badges */}
                    <div className="terp-ov-suds-stats">
                      <span className="terp-ov-stat-badge stat-low">
                        ↓ Min {Math.min(...item.suds_readings.map(r => r.suds_value))}
                      </span>
                      <span className="terp-ov-stat-badge stat-high">
                        ↑ Max {Math.max(...item.suds_readings.map(r => r.suds_value))}
                      </span>
                      <span className="terp-ov-stat-badge stat-last">
                        Last {item.suds_readings[item.suds_readings.length - 1].suds_value}
                      </span>
                    </div>
                  </>
                )}
              </div>

              {/* Session note */}
              {item.session_exercise_note && (
                <div className="terp-ov-section">
                  <h2 className="terp-ov-section-title">Session Note</h2>
                  <p className="terp-ov-note-text">{item.session_exercise_note}</p>
                </div>
              )}
            </section>

            {/* ── RIGHT PANEL ── */}
            <section className="terp-ov-right">
              {/* Tabs */}
              <div className="terp-ov-tabs">
                <button
                  className={`terp-ov-tab ${activeTab === 'sessions' ? 'terp-ov-tab--active' : ''}`}
                  onClick={() => setActiveTab('sessions')}
                >
                  Sessions ({sessions.length})
                </button>
                <button
                  className={`terp-ov-tab ${activeTab === 'report' ? 'terp-ov-tab--active' : ''}`}
                  onClick={() => setActiveTab('report')}
                >
                  Clinical Report
                </button>
              </div>

              {/* ── Sessions tab ── */}
              {activeTab === 'sessions' && (
                <div className="terp-ov-sessions-panel">
                  {sessionsLoading ? (
                    <div className="terp-ov-loading">Loading sessions…</div>
                  ) : sessions.length === 0 ? (
                    <div className="terp-ov-empty-note">No sessions recorded yet.</div>
                  ) : (
                    <div className="terp-ov-sessions-split">
                      {/* Session list */}
                      <div className="terp-ov-session-list">
                        {sessions.map((s) => (
                          <button
                            key={s.id}
                            className={`terp-ov-session-btn ${selectedSessionId === s.id ? 'terp-ov-session-btn--active' : ''}`}
                            onClick={() => setSelectedSessionId(s.id)}
                          >
                            <div className="terp-ov-sbi-date">
                              {new Date(s.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}
                            </div>
                            <div className="terp-ov-sbi-meta">
                              <span className={`terp-ov-status terp-ov-status--${s.status}`}>{s.status}</span>
                              <span className="terp-ov-sbi-dur">
                                {(() => { const t = Math.round(s.accumulated_seconds || 0); return `${Math.floor(t/60)}m ${t%60}s`; })()}
                              </span>
                            </div>
                            {s.patient_feedback_json && <span className="terp-ov-report-dot">✓ Report</span>}
                          </button>
                        ))}
                      </div>

                      {/* Session detail */}
                      <div className="terp-ov-session-detail">
                        {!selectedSessionId && <div className="terp-ov-empty-note">Select a session.</div>}
                        {selectedSessionId && sessionDetailLoading && <div className="terp-ov-loading">Loading…</div>}
                        {selectedSessionId && !sessionDetailLoading && sessionDetail && (
                          <>
                            {/* Transcript */}
                            {sessionDetail.transcript?.messages?.length > 0 && (
                              <div className="terp-ov-section">
                                <h4 className="terp-ov-section-title">
                                  Transcript
                                  <span className="terp-ov-count"> ({sessionDetail.transcript.messages.length} messages)</span>
                                </h4>
                                <div className="terp-ov-transcript">
                                  {sessionDetail.transcript.messages.map((msg) => (
                                    <div key={msg.id} className={`terp-ov-msg terp-ov-msg--${msg.role}`}>
                                      <span className="terp-ov-msg-role">{msg.role}</span>
                                      <p className="terp-ov-msg-text">{msg.content}</p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* SUDS */}
                            {sessionDetail.suds_readings?.length > 0 && (
                              <div className="terp-ov-section">
                                <h4 className="terp-ov-section-title">
                                  SUDS This Session
                                  <span className="terp-ov-count"> ({sessionDetail.suds_readings.length})</span>
                                </h4>
                                <div className="terp-ov-suds-pills">
                                  <span className="terp-ov-stat-badge stat-low">
                                    Start {sessionDetail.suds_readings[0].suds_value}
                                  </span>
                                  <span className="terp-ov-stat-badge stat-high">
                                    ↑ Peak {Math.max(...sessionDetail.suds_readings.map(r => r.suds_value))}
                                  </span>
                                  <span className="terp-ov-stat-badge stat-last">
                                    End {sessionDetail.suds_readings[sessionDetail.suds_readings.length - 1].suds_value}
                                  </span>
                                </div>
                              </div>
                            )}

                            {/* Patient feedback */}
                            {sessionDetail.patient_feedback && (
                              <div className="terp-ov-section">
                                <h4 className="terp-ov-section-title">Patient Feedback</h4>
                                {sessionDetail.patient_feedback.wins?.length > 0 && (
                                  <div className="terp-ov-fb-block">
                                    <span className="terp-ov-fb-label">Wins</span>
                                    <ul className="terp-ov-fb-list">
                                      {sessionDetail.patient_feedback.wins.map((w, i) => <li key={i}>{w}</li>)}
                                    </ul>
                                  </div>
                                )}
                                {sessionDetail.patient_feedback.reflection?.length > 0 && (
                                  <div className="terp-ov-fb-block">
                                    <span className="terp-ov-fb-label">Reflections</span>
                                    <ul className="terp-ov-fb-list">
                                      {sessionDetail.patient_feedback.reflection.map((r, i) => <li key={i}>{r}</li>)}
                                    </ul>
                                  </div>
                                )}
                                {sessionDetail.patient_feedback.skill_to_practice && (
                                  <div className="terp-ov-fb-block">
                                    <span className="terp-ov-fb-label">Skill to Practice</span>
                                    <p className="terp-ov-note-text">{sessionDetail.patient_feedback.skill_to_practice}</p>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* No report yet */}
                            {!sessionDetail.patient_feedback && sessionDetail.session.status === 'ended' && (
                              <div className="terp-ov-empty-note" style={{ marginTop: '0.5rem' }}>
                                No debrief report for this session.
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Clinical Report tab ── */}
              {activeTab === 'report' && (
                <div className="terp-ov-clinical-panel">
                  {!selectedSessionId || !sessionDetail?.therapist_report ? (
                    <div className="terp-ov-ai-panel">
                      <div className="terp-ov-ai-inner">
                        <div className="terp-ov-ai-icon">📋</div>
                        <h3 className="terp-ov-ai-title">Clinical Report</h3>
                        <p className="terp-ov-ai-desc">
                          Select an ended session from the Sessions tab that has a report, then switch here to view the AI-generated clinical summary.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="terp-ov-report-content">
                      <h4 className="terp-ov-section-title">
                        AI Clinical Report —{' '}
                        {new Date(sessionDetail.session.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}
                      </h4>

                      <div className="terp-ov-section terp-ov-cross-session">
                        <span className="terp-ov-fb-label">Cross-Session Overview</span>
                        {sessionDetail.therapist_report.cross_session_overview &&
                         (sessionDetail.therapist_report.cross_session_overview.summary ||
                          sessionDetail.therapist_report.cross_session_overview.common_patterns?.length > 0 ||
                          sessionDetail.therapist_report.cross_session_overview.blockers_to_progress?.length > 0 ||
                          sessionDetail.therapist_report.cross_session_overview.progress_signs?.length > 0) ? (
                          <>
                            {sessionDetail.therapist_report.cross_session_overview.summary && (
                              <p className="terp-ov-cross-session-summary">{sessionDetail.therapist_report.cross_session_overview.summary}</p>
                            )}
                            {sessionDetail.therapist_report.cross_session_overview.common_patterns?.length > 0 && (
                              <div className="terp-ov-cross-session-group">
                                <span className="terp-ov-fb-label">Common Patterns</span>
                                <ul className="terp-ov-fb-list">
                                  {sessionDetail.therapist_report.cross_session_overview.common_patterns.map((x, i) => <li key={i}>{x}</li>)}
                                </ul>
                              </div>
                            )}
                            {sessionDetail.therapist_report.cross_session_overview.blockers_to_progress?.length > 0 && (
                              <div className="terp-ov-cross-session-group terp-ov-cross-session-blockers">
                                <span className="terp-ov-fb-label">Blockers to Progress</span>
                                <ul className="terp-ov-fb-list">
                                  {sessionDetail.therapist_report.cross_session_overview.blockers_to_progress.map((x, i) => <li key={i}>{x}</li>)}
                                </ul>
                              </div>
                            )}
                            {sessionDetail.therapist_report.cross_session_overview.progress_signs?.length > 0 && (
                              <div className="terp-ov-cross-session-group">
                                <span className="terp-ov-fb-label">Signs of Progress</span>
                                <ul className="terp-ov-fb-list">
                                  {sessionDetail.therapist_report.cross_session_overview.progress_signs.map((x, i) => <li key={i}>{x}</li>)}
                                </ul>
                              </div>
                            )}
                          </>
                        ) : (
                          <div>
                            <p className="terp-ov-cross-session-empty">
                              {sessions.filter(s => s.status === 'ended').length <= 1
                                ? 'This is the first session — cross-session analysis will appear from the second session onwards.'
                                : 'Cross-session analysis has not been generated for this session yet.'}
                            </p>
                            {sessions.filter(s => s.status === 'ended').length > 1 && (
                              <div className="terp-ov-cross-session-generate">
                                {crossSessionError && (
                                  <p className="terp-ov-cross-session-error">{crossSessionError}</p>
                                )}
                                <button
                                  className="terp-ov-generate-btn"
                                  onClick={handleGenerateCrossSession}
                                  disabled={crossSessionLoading}
                                >
                                  {crossSessionLoading ? 'Generating…' : 'Generate cross-session analysis'}
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {sessionDetail.therapist_report.suds_curve_summary && (
                        <div className="terp-ov-section">
                          <span className="terp-ov-fb-label">SUDS Curve Summary</span>
                          <p className="terp-ov-note-text">{sessionDetail.therapist_report.suds_curve_summary}</p>
                        </div>
                      )}

                      {sessionDetail.therapist_report.what_happened?.length > 0 && (
                        <div className="terp-ov-section">
                          <span className="terp-ov-fb-label">What Happened</span>
                          <ul className="terp-ov-fb-list">
                            {sessionDetail.therapist_report.what_happened.map((x, i) => <li key={i}>{x}</li>)}
                          </ul>
                        </div>
                      )}

                      {sessionDetail.therapist_report.response_prevention_successes?.length > 0 && (
                        <div className="terp-ov-section">
                          <span className="terp-ov-fb-label">Response Prevention Successes</span>
                          <ul className="terp-ov-fb-list">
                            {sessionDetail.therapist_report.response_prevention_successes.map((x, i) => <li key={i}>{x}</li>)}
                          </ul>
                        </div>
                      )}

                      {sessionDetail.therapist_report.avoidance_or_safety_behaviors?.length > 0 && (
                        <div className="terp-ov-section">
                          <span className="terp-ov-fb-label">Avoidance / Safety Behaviors</span>
                          <ul className="terp-ov-fb-list">
                            {sessionDetail.therapist_report.avoidance_or_safety_behaviors.map((x, i) => <li key={i}>{x}</li>)}
                          </ul>
                        </div>
                      )}

                      {sessionDetail.therapist_report.key_learning?.length > 0 && (
                        <div className="terp-ov-section">
                          <span className="terp-ov-fb-label">Key Learning</span>
                          <ul className="terp-ov-fb-list">
                            {sessionDetail.therapist_report.key_learning.map((x, i) => <li key={i}>{x}</li>)}
                          </ul>
                        </div>
                      )}

                      {sessionDetail.therapist_report.risk_flags?.length > 0 && (
                        <div className="terp-ov-section terp-ov-risk-flags">
                          <span className="terp-ov-fb-label">⚠ Risk Flags</span>
                          <ul className="terp-ov-fb-list">
                            {sessionDetail.therapist_report.risk_flags.map((x, i) => <li key={i}>{x}</li>)}
                          </ul>
                        </div>
                      )}

                      {sessionDetail.therapist_report.recommend_next_step && Object.keys(sessionDetail.therapist_report.recommend_next_step).length > 0 && (
                        <div className="terp-ov-section">
                          <span className="terp-ov-fb-label">Recommended Next Step</span>
                          <pre className="terp-ov-json-pre">
                            {JSON.stringify(sessionDetail.therapist_report.recommend_next_step, null, 2)}
                          </pre>
                        </div>
                      )}
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

export default TherapistERPObsessionView;
