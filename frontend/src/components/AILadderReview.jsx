import React, { useState } from 'react';
import './AILadderReview.css';

const AILadderReview = ({ reviewData }) => {
  const [expandedSuggestions, setExpandedSuggestions] = useState(new Set());

  if (!reviewData) {
    return (
      <div className="ai-review-container">
        <div className="ai-review-empty">
          <div className="empty-icon">🤖</div>
          <h4>No AI Review Available</h4>
          <p>Patient needs to submit the ladder for AI analysis</p>
        </div>
      </div>
    );
  }

  const { status, suggestions, error_message } = reviewData;

  const toggleSuggestion = (suggestionId) => {
    const newExpanded = new Set(expandedSuggestions);
    if (newExpanded.has(suggestionId)) {
      newExpanded.delete(suggestionId);
    } else {
      newExpanded.add(suggestionId);
    }
    setExpandedSuggestions(newExpanded);
  };

  if (status === 'queued' || status === 'running') {
    return (
      <div className="ai-review-container">
        <div className="ai-review-loading">
          <div className="loading-spinner"></div>
          <h4>AI Analysis in Progress</h4>
          <p>Analyzing intake responses and daily logs...</p>
          <p className="status-text">Status: {status}</p>
        </div>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="ai-review-container">
        <div className="ai-review-error">
          <div className="error-icon">⚠️</div>
          <h4>AI Review Failed</h4>
          <p className="error-message">{error_message || 'An error occurred during analysis'}</p>
        </div>
      </div>
    );
  }

  if (status === 'completed' && (!suggestions || suggestions.length === 0)) {
    return (
      <div className="ai-review-container">
        <div className="ai-review-success">
          <div className="success-icon">✅</div>
          <h4>Comprehensive Ladder</h4>
          <p>No additional obsession-compulsion patterns detected. The fear ladder appears to cover the patterns found in the intake and recent logs.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-review-container">
      <div className="ai-review-header">
        <h3>Missing Patterns Detected</h3>
        <span className="suggestions-count">{suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''}</span>
      </div>

      <div className="suggestions-list">
        {suggestions.map((suggestion) => (
          <div key={suggestion.id} className="suggestion-card">
            <div 
              className="suggestion-header"
              onClick={() => toggleSuggestion(suggestion.id)}
            >
              <div className="suggestion-title">
                <div className="obsession-label">
                  <span className="label-tag">Obsession</span>
                  <h4>{suggestion.obsession_label}</h4>
                </div>
                <div className="compulsion-label">
                  <span className="label-tag">Compulsions</span>
                  <p>{suggestion.compulsion_summary}</p>
                </div>
              </div>
              <button className="expand-btn">
                {expandedSuggestions.has(suggestion.id) ? '▼' : '▶'}
              </button>
            </div>

            {expandedSuggestions.has(suggestion.id) && (
              <div className="suggestion-details">
                <div className="rationale-section">
                  <h5>AI Rationale</h5>
                  <p className="rationale-text">{suggestion.rationale}</p>
                </div>

                <div className="evidence-section">
                  <h5>Evidence ({suggestion.evidence?.length || 0} quotes)</h5>
                  <div className="evidence-list">
                    {suggestion.evidence?.map((evidence, idx) => (
                      <div key={evidence.id} className="evidence-item">
                        <div className="evidence-header">
                          <span className={`source-badge ${evidence.source_type}`}>
                            {evidence.source_type === 'intake' ? '📋 Intake' : '📊 Daily Log'}
                          </span>
                          {evidence.source_date && (
                            <span className="evidence-date">
                              {new Date(evidence.source_date).toLocaleDateString()}
                            </span>
                          )}
                          {evidence.field_name && (
                            <span className="field-name">{evidence.field_name}</span>
                          )}
                        </div>
                        <blockquote className="evidence-quote">
                          "{evidence.quote_text}"
                        </blockquote>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="ai-review-footer">
        <p className="disclaimer">
          💡 These are AI-detected patterns from intake responses and the last 7 days of self-monitoring logs. 
          Review with clinical judgment.
        </p>
      </div>
    </div>
  );
};

export default AILadderReview;
