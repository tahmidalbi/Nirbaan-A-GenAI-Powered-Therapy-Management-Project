import { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { therapistGetERPItemDetail } from '../api/erp.api';
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

  useEffect(() => {
    therapistGetERPItemDetail(patientId, itemId)
      .then(({ data }) => setItem(data))
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load detail.'))
      .finally(() => setLoading(false));
  }, [patientId, itemId]);

  const handleBack = () =>
    navigate(`/therapist/dashboard/erp/patient/${patientId}`, {
      state: { patientName, patientEmail },
    });

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
              <div className="terp-ov-ai-panel">
                <div className="terp-ov-ai-inner">
                  <div className="terp-ov-ai-icon">🤖</div>
                  <h3 className="terp-ov-ai-title">AI Clinical Summary</h3>
                  <p className="terp-ov-ai-desc">
                    The AI-generated clinical summary for this obsession — including
                    progress analysis, pattern detection, and treatment recommendations
                    — will appear here.
                  </p>
                  <div className="terp-ov-ai-coming">Coming soon</div>
                </div>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
};

export default TherapistERPObsessionView;
