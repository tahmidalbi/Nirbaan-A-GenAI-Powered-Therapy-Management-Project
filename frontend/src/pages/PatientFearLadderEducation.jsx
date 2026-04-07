import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getMyEducation, generateEducation } from '../api/fear-ladder-education.api';
import ReactMarkdown from 'react-markdown';
import '../dashboards/PatientDashboard.css';
import './PatientFearLadderEducation.css';

const PatientFearLadderEducation = () => {
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
      const data = await getMyEducation();
      setEducation(data);
    } catch (err) {
      console.error('Error fetching education:', err);
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
      const data = await generateEducation(regenerate);
      setEducation(data);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to generate education. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard/fear-ladder');
  };

  // Render key points as list items
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

  // Render sources with proper formatting
  const renderSources = (sources) => {
    if (!sources || sources.length === 0) return null;
    return (
      <div className="sources-section">
        <h3>Sources</h3>
        <div className="sources-list">
          {sources.map((source, idx) => (
            <div key={idx} className="source-item">
              <span className="source-type">[{source.type.toUpperCase()}]</span>
              <span className="source-title">{source.title}</span>
              {source.url && (
                <a 
                  href={source.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="source-link"
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
    <div className="fear-ladder-education-container">
      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>Fear Ladder Education</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={handleBack}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="education-main">
        <div className="education-content">
          
          {/* Action Buttons */}
          <div className="education-actions">
            {!education ? (
              <button 
                onClick={() => handleGenerate(false)}
                disabled={generating || loading}
                className="generate-btn primary"
              >
                {generating ? 'Generating...' : 'Generate Education'}
              </button>
            ) : (
              <button 
                onClick={() => handleGenerate(true)}
                disabled={generating}
                className="generate-btn secondary"
              >
                {generating ? 'Regenerating...' : 'Regenerate Education'}
              </button>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="error-banner">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Loading education content...</p>
            </div>
          )}

          {/* No Education State */}
          {!loading && !education && !error && (
            <div className="empty-state">
              <div className="empty-icon">📚</div>
              <h3>No Education Content Yet</h3>
              <p>Click "Generate Education" to create personalized educational content about fear ladders.</p>
            </div>
          )}

          {/* Education Content */}
          {!loading && education && (
            <>
              <h2>{education.topic}</h2>
              
              {/* Sections */}
              {education.sections && education.sections.map((section) => (
                <div key={section.id} className="education-block">
                  <h3>{section.title}</h3>
                  <div className="section-content">
                    <ReactMarkdown>{section.content_markdown}</ReactMarkdown>
                  </div>
                  {renderKeyPoints(section.key_points)}
                </div>
              ))}

              {/* Sources */}
              {renderSources(education.sources)}

              {/* Disclaimer */}
              {education.disclaimer && (
                <div className="disclaimer-section">
                  <p className="disclaimer-text">
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

export default PatientFearLadderEducation;
