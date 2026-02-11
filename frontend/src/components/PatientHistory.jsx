import { useState, useEffect } from 'react';
import { getAllPatientsProgress, getPatientProgress, createOrUpdateTherapistNote } from '../api/progress.api';
import './PatientHistory.css';

const PatientHistory = () => {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientDetail, setPatientDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastWeekNote, setLastWeekNote] = useState('');
  const [aiInstruction, setAiInstruction] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editingAI, setEditingAI] = useState(false);

  useEffect(() => {
    fetchAllPatients();
  }, []);

  const fetchAllPatients = async () => {
    try {
      setLoading(true);
      const data = await getAllPatientsProgress();
      setPatients(data);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch patients:', err);
      setError('Failed to load patients');
      setLoading(false);
    }
  };

  const handlePatientClick = async (patient) => {
    try {
      setError('');
      setSuccess('');
      setSelectedPatient(patient);
      
      const data = await getPatientProgress(patient.patient_id);
      setPatientDetail(data);
      
      // Set existing notes
      setLastWeekNote(data.therapist_note?.last_week_note || '');
      setAiInstruction(data.therapist_note?.ai_protocol_instruction || '');
    } catch (err) {
      console.error('Failed to fetch patient detail:', err);
      setError('Failed to load patient details');
    }
  };

  const handleSaveNote = async () => {
    if (!selectedPatient) return;

    try {
      setError('');
      setSuccess('');
      await createOrUpdateTherapistNote(
        selectedPatient.patient_id,
        lastWeekNote,
        aiInstruction
      );
      setSuccess('Note saved successfully!');
      setEditingAI(false);
      
      // Refresh patient detail
      const updatedData = await getPatientProgress(selectedPatient.patient_id);
      setPatientDetail(updatedData);
    } catch (err) {
      console.error('Failed to save note:', err);
      setError('Failed to save note');
    }
  };

  const getLastWeekNumber = () => {
    if (!patientDetail?.weekly_progress) return 0;
    const weeks = Object.keys(patientDetail.weekly_progress);
    if (weeks.length === 0) return 0;
    
    const weekNumbers = weeks.map(w => parseInt(w.split('_')[1]));
    return Math.max(...weekNumbers);
  };

  if (loading) {
    return (
      <div className="patient-history-container">
        <div className="vintage-card">
          <p className="loading-text">Loading patient history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="patient-history-container">
      <div className="history-layout">
        {/* Left sidebar - Patient list */}
        <div className="patient-list-sidebar">
          <div className="sidebar-header">
            <h2 className="sidebar-title">Patient List</h2>
            <div className="decorative-divider"></div>
          </div>
          
          <div className="patient-cards">
            {patients.length === 0 ? (
              <p className="no-patients">No patients assigned yet</p>
            ) : (
              patients.map((patient) => (
                <div
                  key={patient.patient_id}
                  className={`patient-card ${selectedPatient?.patient_id === patient.patient_id ? 'active' : ''}`}
                  onClick={() => handlePatientClick(patient)}
                >
                  <div className="patient-card-content">
                    <h3 className="patient-name">{patient.patient_name}</h3>
                    <p className="patient-condition">{patient.conditions}</p>
                    <div className="patient-week-badge">
                      {patient.current_week > 0 ? `Week ${patient.current_week}` : 'Not started'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right main content - Patient details */}
        <div className="patient-detail-main">
          {!selectedPatient ? (
            <div className="no-selection">
              <div className="no-selection-icon">📋</div>
              <h3>Select a Patient</h3>
              <p>Choose a patient from the list to view their progress history</p>
            </div>
          ) : (
            <div className="patient-detail-content">
              {/* Header */}
              <div className="detail-header">
                <div>
                  <h2 className="patient-detail-name">{patientDetail?.patient_name}</h2>
                  <p className="patient-detail-email">{patientDetail?.patient_email}</p>
                  <p className="patient-detail-conditions">
                    <span className="conditions-label">Conditions:</span> {patientDetail?.conditions}
                  </p>
                </div>
              </div>

              {error && <div className="alert alert-error">{error}</div>}
              {success && <div className="alert alert-success">{success}</div>}

              {/* Initial Condition */}
              {patientDetail?.initial_condition && (
                <div className="history-section">
                  <h3 className="history-section-title">Initial Condition</h3>
                  <div className="history-content-box">
                    <p className="history-text">{patientDetail.initial_condition}</p>
                  </div>
                </div>
              )}

              {/* Weekly Progress Timeline */}
              {patientDetail?.weekly_progress && Object.keys(patientDetail.weekly_progress).length > 0 && (
                <div className="history-section">
                  <h3 className="history-section-title">Weekly Progress History</h3>
                  <div className="progress-timeline">
                    {Object.entries(patientDetail.weekly_progress)
                      .sort((a, b) => {
                        const weekA = parseInt(a[0].split('_')[1]);
                        const weekB = parseInt(b[0].split('_')[1]);
                        return weekA - weekB;
                      })
                      .map(([weekKey, weekText], index, array) => {
                        const weekNum = parseInt(weekKey.split('_')[1]);
                        const isLastWeek = index === array.length - 1;
                        
                        return (
                          <div key={weekKey} className={`timeline-item ${isLastWeek ? 'last-week' : ''}`}>
                            <div className="timeline-marker">
                              <div className="timeline-dot"></div>
                              <div className="timeline-week-label">Week {weekNum}</div>
                            </div>
                            <div className="timeline-content">
                              <div className="timeline-progress-box">
                                <p className="timeline-text">{weekText}</p>
                              </div>
                              
                              {/* Show note input for last week */}
                              {isLastWeek && (
                                <div className="therapist-note-section">
                                  <label className="note-label">
                                    <span className="note-icon">📝</span>
                                    Your Note for Week {weekNum}
                                  </label>
                                  <textarea
                                    className="therapist-note-textarea"
                                    value={lastWeekNote}
                                    onChange={(e) => setLastWeekNote(e.target.value)}
                                    placeholder="Add your specific note about this week's progress..."
                                    rows="4"
                                  />
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}

              {/* AI Protocol Instructions */}
              <div className="history-section ai-section">
                <div className="ai-header">
                  <h3 className="history-section-title">
                    <span className="ai-icon">🤖</span>
                    AI Protocol Instructions
                  </h3>
                  <button
                    className="edit-ai-btn"
                    onClick={() => setEditingAI(!editingAI)}
                  >
                    {editingAI ? 'Cancel' : 'Edit'}
                  </button>
                </div>
                
                <div className="ai-instruction-box">
                  {editingAI || !aiInstruction ? (
                    <>
                      <label className="ai-label">
                        How do you want the AI to suggest protocols for this patient?
                      </label>
                      <textarea
                        className="ai-instruction-textarea"
                        value={aiInstruction}
                        onChange={(e) => setAiInstruction(e.target.value)}
                        placeholder="Describe your preferences for AI protocol suggestions. For example: 'Focus on gradual exposure techniques' or 'Emphasize mindfulness-based approaches'..."
                        rows="6"
                      />
                    </>
                  ) : (
                    <div className="ai-instruction-display">
                      <p className="ai-instruction-text">{aiInstruction}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Save button */}
              <div className="action-footer">
                <button className="vintage-btn vintage-btn-save" onClick={handleSaveNote}>
                  <span className="btn-text">Save All Notes</span>
                  <span className="btn-ornament">✦</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatientHistory;
