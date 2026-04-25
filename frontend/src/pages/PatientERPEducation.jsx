import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getMyERPEducation, generateERPEducation } from '../api/erp-education.api';
import ReactMarkdown from 'react-markdown';
import '../dashboards/PatientDashboard.css';
import './PatientERPEducation.css';

const PatientERPEducation = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const [education, setEducation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchEducation();
  }, []);

  const fetchEducation = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getMyERPEducation();
      setEducation(data);
    } catch (err) {
      console.error('Error fetching ERP education:', err);
      setError('');
      setEducation(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (regenerate = false) => {
    try {
      setGenerating(true);
      setError('');
      const data = await generateERPEducation(regenerate);
      setEducation(data);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to generate education. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/select-role');
  };

  const renderKeyPoints = (points) => {
    if (!points || points.length === 0) return null;
    return (
      <div className="key-points">
        <h4>Key Points:</h4>
        <ul>
          {points.map((point, idx) => (
            <li key={idx}>{point}</li>
          ))}
        </ul>
      </div>
    );
  };

  const renderSources = (sources) => {
    if (!sources || sources.length === 0) return null;
    return (
      <div className="erp-edu-sources-section">
        <h3>Sources</h3>
        <div className="erp-edu-sources-list">
          {sources.map((source, idx) => (
            <div key={idx} className="erp-edu-source-item">
              <span className="erp-edu-source-type">[{source.type.toUpperCase()}]</span>
              <span className="erp-edu-source-title">{source.title}</span>
              {source.url && (
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="erp-edu-source-link"
                >
                  View Source →
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="erp-education-container">
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
              <span>ERP Education</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={() => navigate('/patient/dashboard/erp')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="erp-edu-main">
        <div className="erp-edu-content">

          {/* Action Buttons */}
          <div className="erp-edu-actions">
            {!education ? (
              <button
                onClick={() => handleGenerate(false)}
                disabled={generating || loading}
                className="erp-edu-generate-btn primary"
              >
                {generating ? 'Generating...' : 'Generate Education'}
              </button>
            ) : (
              <button
                onClick={() => handleGenerate(true)}
                disabled={generating}
                className="erp-edu-generate-btn secondary"
              >
                {generating ? 'Regenerating...' : 'Regenerate Education'}
              </button>
            )}
          </div>

          {/* Error */}
          {error && <div className="erp-edu-error-banner">{error}</div>}

          {/* Loading */}
          {loading && (
            <div className="erp-edu-loading-state">
              <div className="erp-edu-spinner"></div>
              <p>Loading education content...</p>
            </div>
          )}

          {/* Empty state */}
          {!loading && !education && !error && (
            <div className="erp-edu-empty-state">
              <div className="erp-edu-empty-icon">📖</div>
              <h3>No Education Content Yet</h3>
              <p>
                Click "Generate Education" to create personalised educational content about
                Exposure &amp; Response Prevention.
              </p>
            </div>
          )}

          {/* Content */}
          {!loading && education && (
            <>
              <h2>{education.topic}</h2>

              {education.sections && education.sections.map((section) => (
                <div key={section.id} className="erp-edu-block">
                  <h3>{section.title}</h3>
                  <div className="erp-edu-section-content">
                    <ReactMarkdown>{section.content_markdown}</ReactMarkdown>
                  </div>
                  {renderKeyPoints(section.key_points)}
                </div>
              ))}

              {renderSources(education.sources)}

              {education.disclaimer && (
                <div className="erp-edu-disclaimer">
                  <p>
                    <strong>Disclaimer:</strong> {education.disclaimer}
                  </p>
                </div>
              )}
            </>
          )}

        </div>
      </main>
    </div>
  );
};

export default PatientERPEducation;
