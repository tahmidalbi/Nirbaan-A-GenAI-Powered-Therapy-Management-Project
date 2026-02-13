/**
 * Nirbaan AI Protocol Generator Component
 *
 * FIXED: protocol not showing because backend returns `final_protocol`
 * but UI expects `protocol`.
 *
 * This version normalizes the backend response so:
 * - generatedProtocol.protocol always exists on success
 * - thread_id is mapped correctly
 * - confidence + timing fields are safely handled with fallbacks
 */

import { useState, useEffect } from 'react';
import { generateProtocol, getPatientsForProtocol } from '../api/nirbaan-ai.api';
import './NirbaanAI.css';

const NirbaanAI = () => {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [sessionFocus, setSessionFocus] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [error, setError] = useState('');
  const [generatedProtocol, setGeneratedProtocol] = useState(null);
  const [clarificationQuestions, setClarificationQuestions] = useState(null);
  const [threadId, setThreadId] = useState(null);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      setLoadingPatients(true);
      const data = await getPatientsForProtocol();
      setPatients(data?.patients || []);
    } catch (err) {
      console.error('Failed to fetch patients:', err);
      setError(typeof err === 'string' ? err : 'Failed to load patients');
    } finally {
      setLoadingPatients(false);
    }
  };

  // Normalize backend response to what UI expects
  const normalizeResponse = (response) => {
    console.log('🔍 [NORMALIZE] Input response:', response);
    console.log('🔍 [NORMALIZE] response.status:', response?.status);
    console.log('🔍 [NORMALIZE] response.protocol:', response?.protocol);
    console.log('🔍 [NORMALIZE] response.final_protocol:', response?.final_protocol);

    let protocol = response?.protocol || response?.final_protocol || null;

    // ✅ Validate protocol has actual data (not just empty object {})
    if (protocol) {
      const isEmptyObject = typeof protocol === 'object' && Object.keys(protocol).length === 0;
      const phases = protocol?.phases || protocol?.session_protocol?.phases || [];
      
      console.log('🔍 [NORMALIZE] Protocol validation:');
      console.log('  - Is empty object:', isEmptyObject);
      console.log('  - Phases count:', phases.length);
      
      if (isEmptyObject || phases.length === 0) {
        console.warn('⚠️ [NORMALIZE] Protocol is empty or has no phases, treating as null');
        protocol = null;
      }
    }

    console.log('🔍 [NORMALIZE] Final extracted protocol:', protocol);
    console.log('🔍 [NORMALIZE] Protocol type:', typeof protocol);
    console.log('🔍 [NORMALIZE] Protocol keys:', protocol ? Object.keys(protocol) : 'null');

    const thread_id = response?.thread_id || response?.threadId || null;

    // confidence may be missing; keep null-safe
    const confidence_score =
      typeof response?.confidence_score === 'number'
        ? response.confidence_score
        : typeof response?.global_confidence === 'number'
          ? response.global_confidence
          : null;

    const confidence_tier =
      typeof confidence_score === 'number'
        ? confidence_score >= 0.7
          ? 'high'
          : confidence_score >= 0.5
            ? 'moderate'
            : 'low'
        : null;

    const normalized = {
      ...response,
      protocol, // ✅ ensures generatedProtocol.protocol exists
      thread_id,
      confidence_score,
      confidence_tier,
    };

    console.log('✅ [NORMALIZE] Final normalized response:', normalized);
    return normalized;
  };

  const handleGenerateProtocol = async () => {
    if (!selectedPatient) {
      setError('Please select a patient first');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setGeneratedProtocol(null);
      setClarificationQuestions(null);

      console.log(`🔍 [FRONTEND] Calling generateProtocol with patientId=${selectedPatient.id}`);
      const response = await generateProtocol(selectedPatient.id, sessionFocus || null, false);

      console.log('🔍 [FRONTEND] RAW RESPONSE:', response);

      const normalized = normalizeResponse(response);

      console.log('✅ [FRONTEND] NORMALIZED RESPONSE:', normalized);
      console.log('✅ [FRONTEND] normalized.protocol:', normalized.protocol);
      console.log(
        '✅ [FRONTEND] normalized phases:',
        normalized.protocol?.phases || normalized.protocol?.session_protocol?.phases
      );

      if (normalized.status === 'success') {
        // ✅ Validate that protocol actually exists and has data
        if (!normalized.protocol) {
          setError('Protocol generation succeeded but no protocol data was returned. The backend may have encountered an issue during generation. Check console for details.');
          console.error('❌ [FRONTEND] Success status but protocol is null/undefined/empty');
          console.error('❌ Full backend response:', normalized);
          console.error('❌ Possible causes:');
          console.error('   1. Protocol Generator returned empty protocol');
          console.error('   2. Uncertainty Scorer did not set final_protocol');
          console.error('   3. LangGraph workflow state was not propagated correctly');
        } else {
          setGeneratedProtocol(normalized);
          setThreadId(normalized.thread_id);
        }
      } else if (normalized.status === 'needs_clarification') {
        setClarificationQuestions(normalized.clarification_questions || []);
        setThreadId(normalized.thread_id);
      } else if (normalized.status === 'halted') {
        setError(`Protocol generation halted: ${normalized.halt_reason || 'Unknown reason'}`);
      } else if (normalized.status === 'error') {
        setError(normalized.halt_reason || 'An error occurred during generation');
      } else {
        setError(`Unexpected status: ${normalized.status || 'missing status'}`);
      }
    } catch (err) {
      console.error('Protocol generation error:', err);
      setError(typeof err === 'string' ? err : 'Failed to generate protocol');
    } finally {
      setLoading(false);
    }
  };

  const handlePatientSelect = (patient) => {
    setSelectedPatient(patient);
    setGeneratedProtocol(null);
    setClarificationQuestions(null);
    setThreadId(null); // ✅ prevent stale thread ids
    setError('');
  };

  const getConfidenceBadgeClass = (score) => {
    if (typeof score !== 'number') return 'confidence-low';
    if (score >= 0.7) return 'confidence-high';
    if (score >= 0.5) return 'confidence-moderate';
    return 'confidence-low';
  };

  const formatTime = (minutes) => {
    if (typeof minutes !== 'number') return '';
    return `${Math.floor(minutes / 60) > 0 ? Math.floor(minutes / 60) + 'h ' : ''}${minutes % 60}min`;
  };

  // DEBUG render state
  console.log('🎨 [RENDER] Current state:');
  console.log('  - generatedProtocol:', generatedProtocol);
  console.log('  - generatedProtocol?.protocol:', generatedProtocol?.protocol);
  console.log('  - loading:', loading);
  console.log('  - error:', error);
  console.log('  - clarificationQuestions:', clarificationQuestions);
  
  // Check what will render
  const willRenderEmpty = !generatedProtocol && !loading && !clarificationQuestions && !error;
  const willRenderError = error && !loading && !generatedProtocol && !clarificationQuestions;
  const willRenderLoading = loading;
  const willRenderProtocol = generatedProtocol && generatedProtocol.protocol;
  const willRenderClarification = clarificationQuestions && clarificationQuestions.length > 0;
  
  console.log('🎨 [RENDER] Will render:');
  console.log('  - Empty state:', willRenderEmpty);
  console.log('  - Error state:', willRenderError);
  console.log('  - Loading state:', willRenderLoading);
  console.log('  - Protocol:', willRenderProtocol);
  console.log('  - Clarification:', willRenderClarification);

  if (!willRenderEmpty && !willRenderError && !willRenderLoading && !willRenderProtocol && !willRenderClarification) {
    console.error('⚠️ [RENDER] NO CONDITION MATCHED - BLANK SCREEN!');
    console.error('  State dump:', { generatedProtocol, loading, error, clarificationQuestions });
  }

  return (
    <div className="nirbaan-ai">
      {/* Left Sidebar */}
      <div className="nirbaan-sidebar">
        <div className="sidebar-header">
          <div className="ai-icon">🧠</div>
          <h2>Nirbaan AI</h2>
          <p>Protocol Generator</p>
        </div>

        {/* Patient Selector */}
        <div className="patient-selector">
          <label>Select Patient</label>
          {loadingPatients ? (
            <div className="loading-small">Loading patients...</div>
          ) : patients.length === 0 ? (
            <div className="no-patients">No patients available</div>
          ) : (
            <div className="patient-list">
              {patients.map((patient) => {
                const conditionsText = Array.isArray(patient.conditions)
                  ? patient.conditions.join(', ')
                  : patient.conditions || '';

                return (
                  <div
                    key={patient.id}
                    className={`patient-option ${selectedPatient?.id === patient.id ? 'selected' : ''}`}
                    onClick={() => handlePatientSelect(patient)}
                  >
                    <div className="patient-avatar">{patient.name?.charAt(0)?.toUpperCase() || '?'}</div>
                    <div className="patient-details">
                      <span className="patient-name">{patient.name}</span>
                      <span className="patient-condition">{conditionsText}</span>
                      <span className="patient-sessions">{patient.session_count} sessions</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Session Focus Input */}
        <div className="session-focus-section">
          <label>Session Focus (Optional)</label>
          <textarea
            value={sessionFocus}
            onChange={(e) => setSessionFocus(e.target.value)}
            placeholder={`Describe what you want to focus on in this session...

Examples:
• Focus on harm OCD exposure today
• Work on social anxiety hierarchy
• Practice cognitive restructuring
• Address avoidance behaviors`}
            rows={6}
          />
        </div>

        {/* Generate Button */}
        <button className="generate-btn" onClick={handleGenerateProtocol} disabled={loading || !selectedPatient}>
          {loading ? (
            <>
              <span className="spinner"></span>
              Generating Protocol...
            </>
          ) : (
            <>
              <span className="btn-icon">✨</span>
              Generate Protocol
            </>
          )}
        </button>

        {error && <div className="error-message">{error}</div>}

        {selectedPatient && (
          <div className="selected-patient-info">
            <h4>Selected Patient</h4>
            <p>
              <strong>{selectedPatient.name}</strong>
            </p>
            <p>
              Conditions:{' '}
              {Array.isArray(selectedPatient.conditions)
                ? selectedPatient.conditions.join(', ')
                : selectedPatient.conditions}
            </p>
            {selectedPatient.conditions_description && (
              <p className="condition-desc">{selectedPatient.conditions_description}</p>
            )}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="nirbaan-main">
        {!generatedProtocol && !loading && !clarificationQuestions && !error && (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>Generate a Therapy Protocol</h3>
            <p>Select a patient and click "Generate Protocol" to create a personalized 60-minute therapy session plan.</p>
          </div>
        )}

        {/* Show error in main area if not loading and no other content */}
        {error && !loading && !generatedProtocol && !clarificationQuestions && (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <h3>Unable to Generate Protocol</h3>
            <p className="error-details">{error}</p>
            <button className="retry-btn" onClick={handleGenerateProtocol} disabled={!selectedPatient}>
              Try Again
            </button>
          </div>
        )}

        {loading && (
          <div className="loading-state">
            <div className="loading-spinner-large"></div>
            <h3>Generating Protocol...</h3>
            <p>Analyzing patient history and transcripts to create a personalized protocol.</p>
          </div>
        )}

        {generatedProtocol && generatedProtocol.protocol && (
          <div className="protocol-container">
            {/* Header */}
            <div className="protocol-header">
              <div className="protocol-title">
                <h2>60-Minute Therapy Protocol</h2>
                <span className="patient-badge">{selectedPatient?.name || 'Patient'}</span>
              </div>

              <div className="protocol-meta">
                <div className={`confidence-badge ${getConfidenceBadgeClass(generatedProtocol.confidence_score)}`}>
                  <span className="confidence-label">Confidence:</span>
                  <span className="confidence-value">
                    {typeof generatedProtocol.confidence_score === 'number'
                      ? `${(generatedProtocol.confidence_score * 100).toFixed(0)}%`
                      : '—'}
                  </span>
                  <span className="confidence-tier">
                    {generatedProtocol.confidence_tier ? `(${generatedProtocol.confidence_tier})` : ''}
                  </span>
                </div>
              </div>
            </div>

            {/* Session Context */}
            <div className="session-context">
              <h4>Session Context</h4>
              <p>
                <strong>Patient:</strong> {selectedPatient?.name}
              </p>
              <p>
                <strong>Conditions:</strong>{' '}
                {Array.isArray(selectedPatient?.conditions)
                  ? selectedPatient.conditions.join(', ')
                  : selectedPatient?.conditions}
              </p>
              {sessionFocus && (
                <p>
                  <strong>Session Focus:</strong> {sessionFocus}
                </p>
              )}
            </div>

            {/* Phases */}
            {(() => {
              const protocol = generatedProtocol.protocol || {};
              const phases = protocol.phases || protocol.session_protocol?.phases || [];

              if (!phases || phases.length === 0) {
                return (
                  <div className="error-message" style={{ marginTop: '1rem' }}>
                    ⚠️ Protocol generated but no phases found.
                    <details style={{ marginTop: '1rem' }}>
                      <summary>Debug: View Raw Protocol Data</summary>
                      <pre
                        style={{
                          fontSize: '10px',
                          maxHeight: '300px',
                          overflow: 'auto',
                          background: '#000',
                          padding: '1rem',
                          borderRadius: '8px'
                        }}
                      >
                        {JSON.stringify(protocol, null, 2)}
                      </pre>
                    </details>
                  </div>
                );
              }

              return (
                <div className="protocol-phases">
                  {phases.map((phase, index) => {
                    const phaseNumber = phase.phase_number || index + 1;
                    const phaseName = phase.phase_name || phase.name || `Phase ${phaseNumber}`;
                    const timeDisplay =
                      phase.time_range ||
                      (phase.time_start && phase.time_end ? `${phase.time_start}-${phase.time_end} min` : '') ||
                      (phase.time_allocation_minutes ? `${phase.time_allocation_minutes} min` : '');

                    const objective = phase.objective || (phase.objectives && phase.objectives[0]) || '';

                    const activities = phase.activities || [];
                    return (
                      <div key={index} className="phase-card">
                        <div className="phase-header">
                          <div className="phase-number">Phase {phaseNumber}</div>
                          {timeDisplay && <div className="phase-time">{timeDisplay}</div>}
                        </div>

                        <h3 className="phase-name">{phaseName}</h3>
                        {objective && <p className="phase-objective">{objective}</p>}

                        {activities.length > 0 && (
                          <div className="phase-activities">
                            <h5>Activities</h5>
                            {activities.map((activity, actIdx) => (
                              <div key={actIdx} className="activity-item">
                                <div className="activity-name">
                                  {activity.activity_name || activity.name || `Activity ${actIdx + 1}`}
                                </div>
                                <div className="activity-desc">{activity.description || activity.instructions || ''}</div>
                                {(activity.time_allocation || activity.duration_minutes) && (
                                  <div className="activity-time">
                                    {activity.time_allocation || `${activity.duration_minutes} min`}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        )}

        {/* Clarification */}
        {clarificationQuestions && clarificationQuestions.length > 0 && (
          <div className="clarification-section">
            <h3>🤔 Clarification Needed</h3>
            <p>The AI needs clarification before generating the protocol:</p>
            <div className="clarification-questions">
              {clarificationQuestions.map((q, idx) => (
                <div key={idx} className="clarification-question">
                  <label>{q.question}</label>
                </div>
              ))}
            </div>
            {threadId && (
              <div style={{ marginTop: '0.75rem', fontSize: '12px', opacity: 0.8 }}>
                Thread ID: {threadId}
              </div>
            )}
          </div>
        )}

        {/* Safety Net: If protocol exists but can't be displayed, show debug info */}
        {generatedProtocol && !generatedProtocol.protocol && !loading && !error && (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <h3>Protocol Data Issue</h3>
            <p className="error-details">
              A protocol was generated but the data structure is invalid or missing.
            </p>
            <details style={{ marginTop: '1rem', textAlign: 'left', maxWidth: '600px' }}>
              <summary style={{ cursor: 'pointer', color: '#7fc4b0' }}>Show Debug Information</summary>
              <pre style={{
                fontSize: '11px',
                maxHeight: '400px',
                overflow: 'auto',
                background: 'rgba(0,0,0,0.4)',
                padding: '1rem',
                borderRadius: '8px',
                marginTop: '0.5rem',
                color: '#e0f0ea'
              }}>
                {JSON.stringify(generatedProtocol, null, 2)}
              </pre>
            </details>
            <button className="retry-btn" onClick={handleGenerateProtocol} disabled={!selectedPatient}>
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default NirbaanAI;
