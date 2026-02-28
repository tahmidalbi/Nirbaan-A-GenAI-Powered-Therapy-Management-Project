import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getMyOCDEducation, triggerOCDEducationGeneration } from '../api/ocd-education.api';
import ReactMarkdown from 'react-markdown';
import './PatientOCDEducation.css';

const POLL_INTERVAL_MS = 4000; // poll every 4 seconds while queued/running

const PatientOCDEducation = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const [record, setRecord] = useState(null);          // full {status, education, error_message}
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState('');
  const [expandedSections, setExpandedSections] = useState(new Set());

  const pollRef = useRef(null);

  // ---------- fetch ----------
  const fetchStatus = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const data = await getMyOCDEducation();
      setRecord(data);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to fetch education status.');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  // ---------- polling ----------
  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    const status = record?.status;
    if (status === 'queued' || status === 'running') {
      // Start polling
      if (!pollRef.current) {
        pollRef.current = setInterval(() => fetchStatus(true), POLL_INTERVAL_MS);
      }
    } else {
      // Stop polling
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [record?.status]);

  // ---------- trigger ----------
  const handleGenerate = async (regenerate = false) => {
    try {
      setTriggering(true);
      setError('');
      await triggerOCDEducationGeneration(regenerate);
      // Immediately fetch to get the queued status
      await fetchStatus();
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to start generation. Please try again.');
    } finally {
      setTriggering(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard/tools/ocd/assessment');
  };

  const toggleSection = (sectionId) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      next.has(sectionId) ? next.delete(sectionId) : next.add(sectionId);
      return next;
    });
  };

  const education = record?.status === 'completed' ? record.education : null;
  const status = record?.status;

  // ---------- render ----------
  return (
    <div className="ocd-education-container">
      {/* Background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Understanding OCD</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="ocd-edu-main">
        <div className="ocd-edu-content">

          {/* Action button */}
          <div className="edu-actions">
            {!record || record.status === 'failed' ? (
              <button
                onClick={() => handleGenerate(false)}
                disabled={triggering || loading}
                className="generate-btn primary"
              >
                {triggering ? 'Starting...' : 'Generate OCD Education'}
              </button>
            ) : status === 'completed' ? (
              <button
                onClick={() => handleGenerate(true)}
                disabled={triggering}
                className="generate-btn secondary"
              >
                {triggering ? 'Starting...' : 'Regenerate'}
              </button>
            ) : null}
          </div>

          {/* Error */}
          {error && <div className="edu-error-banner">{error}</div>}

          {/* Initial loading */}
          {loading && (
            <div className="edu-loading">
              <div className="edu-spinner"></div>
              <p>Loading...</p>
            </div>
          )}

          {/* No record yet */}
          {!loading && !record && !error && (
            <div className="edu-empty">
              <div className="edu-empty-icon">🧠</div>
              <h3>No Education Content Yet</h3>
              <p>Click "Generate OCD Education" to create personalised content about OCD concepts drawn from your therapist's knowledge base.</p>
            </div>
          )}

          {/* Queued / Running */}
          {!loading && (status === 'queued' || status === 'running') && (
            <div className="edu-loading">
              <div className="edu-spinner"></div>
              <h4>Generating your OCD education…</h4>
              <p className="edu-status-text">Status: <strong>{status}</strong></p>
              <p className="edu-status-sub">This usually takes 20–60 seconds. This page will update automatically.</p>
            </div>
          )}

          {/* Failed */}
          {!loading && status === 'failed' && (
            <div className="edu-error-state">
              <div className="edu-error-icon">⚠️</div>
              <h4>Generation Failed</h4>
              <p>{record?.error_message || 'An unexpected error occurred.'}</p>
            </div>
          )}

          {/* Completed */}
          {!loading && status === 'completed' && education && (
            <>
              <div className="edu-topic-header">
                <h2>{education.topic}</h2>
                <span className="edu-reading-badge">{education.reading_level}</span>
              </div>

              <div className="edu-sections">
                {(education.sections || []).map((section) => (
                  <div key={section.id} className="edu-section-card">
                    <button
                      className="edu-section-toggle"
                      onClick={() => toggleSection(section.id)}
                    >
                      <span>{section.title}</span>
                      <span className="edu-toggle-icon">
                        {expandedSections.has(section.id) ? '▼' : '▶'}
                      </span>
                    </button>

                    {expandedSections.has(section.id) && (
                      <div className="edu-section-body">
                        <div className="edu-section-markdown">
                          <ReactMarkdown>{section.content_markdown}</ReactMarkdown>
                        </div>

                        {section.key_points && section.key_points.length > 0 && (
                          <div className="edu-key-points">
                            <h4>Key Points</h4>
                            <ul>
                              {section.key_points.map((pt, i) => (
                                <li key={i}>{pt}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Sources */}
              {education.sources && education.sources.length > 0 && (
                <div className="edu-sources">
                  <h3>Sources</h3>
                  {education.sources.map((src, i) => (
                    <div key={i} className="edu-source-item">
                      <span className="edu-source-badge">[{src.type.toUpperCase()}]</span>
                      <span className="edu-source-title">{src.title}</span>
                      {src.url && (
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className="edu-source-link">
                          View →
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Disclaimer */}
              {education.disclaimer && (
                <div className="edu-disclaimer">
                  <strong>Disclaimer:</strong> {education.disclaimer}
                </div>
              )}
            </>
          )}

        </div>
      </main>
    </div>
  );
};

export default PatientOCDEducation;
