import { useState, useEffect } from 'react';
import { getPatients } from '../api/patient.api';
import { getPatientIntake } from '../api/intake.api';
import './PatientHistory.css';

const PatientHistory = () => {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [selectedIntake, setSelectedIntake] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pollInterval, setPollInterval] = useState(null);

  useEffect(() => {
    fetchPatients();
  }, []);

  // Poll for AI summary updates when intake is pending or running
  useEffect(() => {
    if (!selectedIntake) {
      if (pollInterval) {
        clearInterval(pollInterval);
        setPollInterval(null);
      }
      return;
    }

    const status = selectedIntake.ai_summary_status;
    if (status === 'pending' || status === 'running') {
      // Start polling every 3 seconds
      const interval = setInterval(async () => {
        try {
          const intake = await getPatientIntake(selectedPatient.id);
          setSelectedIntake(intake);
          
          // Stop polling if status is done or failed
          if (intake.ai_summary_status === 'done' || intake.ai_summary_status === 'failed') {
            clearInterval(interval);
            setPollInterval(null);
          }
        } catch (err) {
          // If error fetching, keep trying
          console.error('Error polling intake:', err);
        }
      }, 3000);

      setPollInterval(interval);

      return () => {
        clearInterval(interval);
      };
    } else {
      if (pollInterval) {
        clearInterval(pollInterval);
        setPollInterval(null);
      }
    }
  }, [selectedIntake?.id, selectedIntake?.ai_summary_status, selectedPatient?.id]);

  const fetchPatients = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getPatients();
      setPatients(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  };

  const handlePatientClick = async (patient) => {
    setSelectedPatient(patient);
    setSelectedIntake(null);
    setError('');

    try {
      setLoading(true);
      const intake = await getPatientIntake(patient.id);
      setSelectedIntake(intake);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'No intake form found for this patient');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setSelectedPatient(null);
    setSelectedIntake(null);
    setError('');
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="ph-page">
      <div className="ph-shell">
        <div className="ph-topbar">
          <div className="ph-brand">
            <div className="ph-brandDot" />
            <div>
              <h1 className="ph-title">Patient History</h1>
              <p className="ph-subtitle">
                {selectedPatient
                  ? 'Review intake details and key information'
                  : 'Select a patient to view their intake information'}
              </p>
            </div>
          </div>

          {!selectedPatient && (
            <button className="ph-refreshBtn" onClick={fetchPatients} disabled={loading}>
              {loading ? 'Refreshing…' : 'Refresh'}
            </button>
          )}
        </div>

        {!selectedPatient ? (
          <div className="ph-card">
            {loading ? (
              <div className="ph-state">
                <div className="ph-spinner" />
                <p>Loading patients…</p>
              </div>
            ) : patients.length === 0 ? (
              <div className="ph-empty">
                <div className="ph-emptyIcon">👤</div>
                <h3>No patients found</h3>
                <p>Add a patient from the therapist dashboard to see them here.</p>
              </div>
            ) : (
              <div className="ph-grid">
                {patients.map((patient) => (
                  <button
                    key={patient.id}
                    className="ph-patientCard"
                    onClick={() => handlePatientClick(patient)}
                    type="button"
                  >
                    <div className="ph-patientHead">
                      <h3 className="ph-patientName">{patient.name}</h3>
                      <span className="ph-chip">{patient.conditions || '—'}</span>
                    </div>

                    <div className="ph-patientBody">
                      <div className="ph-row">
                        <span className="ph-label">Email</span>
                        <span className="ph-value">{patient.email || '—'}</span>
                      </div>
                      <div className="ph-row">
                        <span className="ph-label">Address</span>
                        <span className="ph-value">{patient.address || '—'}</span>
                      </div>
                    </div>

                    <div className="ph-patientFoot">
                      <span className="ph-link">View Intake</span>
                      <span className="ph-arrow">→</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="ph-details">
            <div className="ph-detailsHeader">
              <button onClick={handleBack} className="ph-backBtn" type="button">
                ← Back
              </button>

              <div className="ph-patientSummary">
                <div className="ph-avatar">
                  {(selectedPatient?.name || '?').slice(0, 1).toUpperCase()}
                </div>
                <div>
                  <h2 className="ph-patientTitle">{selectedPatient?.name}</h2>
                  <div className="ph-metaLine">
                    <span>{selectedPatient?.email}</span>
                    <span className="ph-dot">•</span>
                    <span>{selectedPatient?.conditions || '—'}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="ph-card">
              <div className="ph-tabs">
                <button className="ph-tab ph-tabActive" type="button">
                  Initial Intake
                </button>
                <button className="ph-tab" type="button" disabled>
                  Week 1 Update
                </button>
                <button className="ph-tab" type="button" disabled>
                  Week 2 Update
                </button>
              </div>

              {loading ? (
                <div className="ph-state">
                  <div className="ph-spinner" />
                  <p>Loading intake…</p>
                </div>
              ) : error ? (
                <div className="ph-error">
                  <div className="ph-errorIcon">⚠️</div>
                  <div>
                    <h4>Couldn’t load intake</h4>
                    <p>{error}</p>
                  </div>
                </div>
              ) : selectedIntake ? (
                <div className="ph-content">
                  <div className="ph-section">
                    <h3>Your Story</h3>
                    <p>{selectedIntake.your_story || '—'}</p>
                  </div>

                  <div className="ph-section">
                    <h3>When It Started</h3>
                    <p>{selectedIntake.when_started || '—'}</p>
                  </div>

                  <div className="ph-split">
                    <div className="ph-section">
                      <h3>Previous Therapy</h3>
                      <div className="ph-badgeRow">
                        <span className={`ph-badge ${selectedIntake.tried_previous_therapy ? 'ok' : 'no'}`}>
                          {selectedIntake.tried_previous_therapy ? 'Yes' : 'No'}
                        </span>
                      </div>

                      {selectedIntake.tried_previous_therapy && selectedIntake.previous_therapy_details ? (
                        <div className="ph-box">
                          <p>{selectedIntake.previous_therapy_details}</p>
                        </div>
                      ) : null}
                    </div>

                    <div className="ph-section">
                      <h3>Medication History</h3>
                      <div className="ph-badgeRow">
                        <span className={`ph-badge ${selectedIntake.taken_medication ? 'ok' : 'no'}`}>
                          {selectedIntake.taken_medication ? 'Yes' : 'No'}
                        </span>
                      </div>

                      {selectedIntake.taken_medication && selectedIntake.medication_details ? (
                        <div className="ph-box">
                          <p>{selectedIntake.medication_details}</p>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {!!selectedIntake.affected_life_areas && (
                    <div className="ph-section">
                      <h3>Life Areas Affected</h3>
                      <p>{selectedIntake.affected_life_areas}</p>
                    </div>
                  )}

                  {!!selectedIntake.other_conditions && (
                    <div className="ph-section">
                      <h3>Other Physical or Mental Conditions</h3>
                      <p>{selectedIntake.other_conditions}</p>
                    </div>
                  )}

                  <div className="ph-section">
                    <div className="ph-sectionHead">
                      <h3>Issues & Severity</h3>
                      <span className="ph-muted">
                        {(selectedIntake.issues?.length ?? 0)} item(s)
                      </span>
                    </div>

                    {Array.isArray(selectedIntake.issues) && selectedIntake.issues.length > 0 ? (
                      <div className="ph-issues">
                        {selectedIntake.issues.map((issue, index) => {
                          const sev = Math.max(0, Math.min(10, Number(issue?.severity ?? 0)));
                          return (
                            <div key={index} className="ph-issueCard">
                              <div className="ph-issueTop">
                                <span className="ph-issueName">{issue?.issue || '—'}</span>
                                <span className="ph-sevPill">
                                  <strong>{sev}</strong>
                                  <span>/10</span>
                                </span>
                              </div>

                              <div className="ph-bar">
                                <div className="ph-barFill" style={{ width: `${sev * 10}%` }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="ph-emptyInline">
                        No issues were provided in this intake.
                      </div>
                    )}
                  </div>

                  <div className="ph-section ph-ai">
                    <div className="ph-sectionHead">
                      <h3>🤖 AI Analysis Summary</h3>
                      {selectedIntake.ai_summary_status === 'pending' && (
                        <span className="ph-statusBadge ph-statusPending">Queued</span>
                      )}
                      {selectedIntake.ai_summary_status === 'running' && (
                        <span className="ph-statusBadge ph-statusRunning">Generating...</span>
                      )}
                      {selectedIntake.ai_summary_status === 'done' && (
                        <span className="ph-statusBadge ph-statusDone">✓ Complete</span>
                      )}
                      {selectedIntake.ai_summary_status === 'failed' && (
                        <span className="ph-statusBadge ph-statusFailed">✗ Failed</span>
                      )}
                    </div>
                    
                    {(selectedIntake.ai_summary_status === 'pending' || selectedIntake.ai_summary_status === 'running') && (
                      <div className="ph-aiBox ph-aiLoading">
                        <div className="ph-spinner" />
                        <p>
                          {selectedIntake.ai_summary_status === 'pending' 
                            ? 'Waiting for AI analysis to start...' 
                            : 'AI is analyzing the intake form...'}
                        </p>
                        <p className="ph-muted">This usually takes 10-30 seconds</p>
                      </div>
                    )}

                    {selectedIntake.ai_summary_status === 'done' && selectedIntake.ai_summary_text && (
                      <div className="ph-aiBox ph-aiSuccess">
                        <div className="ph-summaryBullets">
                          {selectedIntake.ai_summary_text.split('\n').filter(line => line.trim()).map((bullet, idx) => (
                            <div key={idx} className="ph-bullet">
                              <span className="ph-bulletDot">•</span>
                              <span>{bullet.replace(/^[•\-*]\s*/, '')}</span>
                            </div>
                          ))}
                        </div>
                        {selectedIntake.ai_summary_updated_at && (
                          <p className="ph-aiTimestamp">
                            Generated {formatDateTime(selectedIntake.ai_summary_updated_at)}
                          </p>
                        )}
                      </div>
                    )}

                    {selectedIntake.ai_summary_status === 'failed' && (
                      <div className="ph-aiBox ph-aiError">
                        <div className="ph-errorIcon">⚠️</div>
                        <div>
                          <h4>AI Summary Generation Failed</h4>
                          <p>{selectedIntake.ai_summary_error || 'An error occurred while generating the summary.'}</p>
                          <p className="ph-muted">The intake data is still available above. You can manually review the information.</p>
                        </div>
                      </div>
                    )}

                    {!selectedIntake.ai_summary_status && (
                      <div className="ph-aiBox">
                        <p>AI summary not available for this intake.</p>
                      </div>
                    )}
                  </div>

                  <div className="ph-footer">
                    <div className="ph-footItem">
                      <span className="ph-footLabel">Submitted</span>
                      <span className="ph-footValue">{formatDateTime(selectedIntake.created_at) || '—'}</span>
                    </div>

                    {selectedIntake.updated_at && selectedIntake.updated_at !== selectedIntake.created_at ? (
                      <div className="ph-footItem">
                        <span className="ph-footLabel">Last Updated</span>
                        <span className="ph-footValue">{formatDateTime(selectedIntake.updated_at) || '—'}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientHistory;
