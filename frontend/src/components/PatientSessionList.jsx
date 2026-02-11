import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPatientsWithSessions, createSession } from '../api/session.api';
import { getPatients } from '../api/patient.api';
import './PatientSessionList.css';

const PatientSessionList = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState([]);
  const [allPatients, setAllPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [weekNumber, setWeekNumber] = useState(1);
  const [transcript, setTranscript] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPatientsWithSessions();
    fetchAllPatients();
  }, []);

  const fetchPatientsWithSessions = async () => {
    try {
      setLoading(true);
      const data = await getPatientsWithSessions();
      setPatients(data);
    } catch (err) {
      setError('Failed to load patients with sessions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllPatients = async () => {
    try {
      const data = await getPatients();
      setAllPatients(data);
    } catch (err) {
      console.error('Failed to load all patients', err);
    }
  };

  const handlePatientClick = (patientId) => {
    navigate(`/therapist/sessions/${patientId}`);
  };

  const openAddModal = () => {
    setSelectedPatientId('');
    setWeekNumber(1);
    setTranscript('');
    setError('');
    setSuccess('');
    setShowAddModal(true);
  };

  const handleAddSession = async () => {
    if (!selectedPatientId) {
      setError('Please select a patient');
      return;
    }
    if (!transcript.trim()) {
      setError('Please enter a transcript');
      return;
    }

    try {
      setSaving(true);
      await createSession(parseInt(selectedPatientId), weekNumber, transcript);
      setSuccess('Session created successfully!');
      setShowAddModal(false);
      
      // Refresh patients list
      await fetchPatientsWithSessions();
      
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create session');
    } finally {
      setSaving(false);
    }
  };

  const getInitial = (name) => {
    return name ? name.charAt(0).toUpperCase() : '?';
  };

  if (loading) {
    return (
      <div className="patient-session-list-wrapper">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading patients...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="patient-session-list-wrapper">
      {/* Header */}
      <div className="session-list-header">
        <div className="header-ornament header-ornament-left"></div>
        <h1 className="session-list-title">Session Transcripts</h1>
        <div className="header-ornament header-ornament-right"></div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Patient Grid */}
      <div className="patient-session-grid">
        {patients.length === 0 ? (
          <div className="no-patients">
            <div className="no-patients-icon">📋</div>
            <h3>No Sessions Yet</h3>
            <p>Session transcripts will appear here once created</p>
          </div>
        ) : (
          patients.map((patient) => (
            <div
              key={patient.patient_id}
              className="patient-session-card"
              onClick={() => handlePatientClick(patient.patient_id)}
            >
              <div className="card-corner card-corner-tl"></div>
              <div className="card-corner card-corner-tr"></div>
              <div className="card-corner card-corner-bl"></div>
              <div className="card-corner card-corner-br"></div>

              <div className="card-header">
                <div className="patient-avatar">{getInitial(patient.patient_name)}</div>
                <div className="patient-info">
                  <h3 className="patient-name">{patient.patient_name}</h3>
                  <p className="patient-email">{patient.patient_email}</p>
                </div>
              </div>

              <div className="card-body">
                <div className="info-row">
                  <span className="info-label">Sessions:</span>
                  <span className="info-badge sessions-badge">
                    {patient.session_count}
                  </span>
                </div>
              </div>

              <div className="card-footer">
                <span className="view-link">View Transcripts →</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add Session FAB */}
      <button 
        className="add-session-fab"
        onClick={openAddModal}
        title="Add New Session"
      >
        <span className="fab-plus">+</span>
      </button>

      {/* Add Session Modal */}
      {showAddModal && (
        <div className="add-session-modal">
          <div className="modal-overlay" onClick={() => setShowAddModal(false)}></div>
          <div className="modal-content">
            <div className="modal-header">
              <h3>Add Session Transcript</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>✕</button>
            </div>
            
            <div className="modal-body">
              {error && <div className="alert alert-error">{error}</div>}
              
              <div className="form-group">
                <label className="modal-label">Select Patient</label>
                <select
                  className="modal-select"
                  value={selectedPatientId}
                  onChange={(e) => setSelectedPatientId(e.target.value)}
                >
                  <option value="">-- Choose Patient --</option>
                  {allPatients.map((patient) => (
                    <option key={patient.id} value={patient.id}>
                      {patient.name} ({patient.email})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="modal-label">Week Number</label>
                <input
                  type="number"
                  className="modal-input"
                  value={weekNumber}
                  onChange={(e) => setWeekNumber(parseInt(e.target.value) || 1)}
                  min="1"
                />
              </div>

              <div className="form-group">
                <label className="modal-label">Session Transcript</label>
                <textarea
                  className="modal-textarea"
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="Enter the session transcript here...&#10;&#10;(This is dummy data for now. Will be integrated with video pipeline and LangGraph later.)"
                  rows="12"
                />
              </div>
            </div>
            
            <div className="modal-footer">
              <button className="modal-button modal-button-cancel" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
              <button 
                className="modal-button modal-button-save"
                onClick={handleAddSession}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Session'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PatientSessionList;
