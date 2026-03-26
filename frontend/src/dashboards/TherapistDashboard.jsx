import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { getPatients } from '../api/patient.api';
import { getEmergencyPersonnel } from '../api/emergency-personnel.api';
import {
  getPatientSessionsTherapist,
  createTherapySession,
  deleteTherapySession,
} from '../api/sessions.api';
import AddPatient from'../components/AddPatient';
import AddEmergencyPersonnel from '../components/AddEmergencyPersonnel';
import ResourceManager from '../components/ResourceManager';
import PatientHistory from '../components/PatientHistory';
import ActiveSessions from '../components/ActiveSessions';
import './TherapistDashboard.css';

const TherapistDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const [patients, setPatients] = useState([]);
  const [emergencyPersonnel, setEmergencyPersonnel] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeSection, setActiveSection] = useState(null);

  // Sessions section state
  const [sessionsPatients, setSessionsPatients] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState('');
  const [selectedSessionPatient, setSelectedSessionPatient] = useState(null); // patient object
  const [patientSessions, setPatientSessions] = useState([]);
  const [patientSessionsLoading, setPatientSessionsLoading] = useState(false);
  const [expandedSession, setExpandedSession] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [sessionForm, setSessionForm] = useState({
    session_date: new Date().toISOString().slice(0, 10),
    title: '',
    transcript: '',
    therapist_notes: '',
  });
  const [sessionSaving, setSessionSaving] = useState(false);
  const [sessionFormError, setSessionFormError] = useState('');

  useEffect(() => {
    if (activeSection === 'patients') {
      fetchPatients();
    } else if (activeSection === 'emergency') {
      fetchEmergencyPersonnel();
    } else if (activeSection === 'sessionLog') {
      fetchSessionsPatients();
    }
  }, [activeSection]);

  const fetchPatients = async () => {
    try {
      setLoading(true);
      const data = await getPatients();
      setPatients(data);
    } catch (err) {
      console.error('Failed to fetch patients:', err);
      setError(typeof err === 'string' ? err : 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmergencyPersonnel = async () => {
    try {
      setLoading(true);
      const data = await getEmergencyPersonnel();
      setEmergencyPersonnel(data);
    } catch (err) {
      console.error('Failed to fetch emergency personnel:', err);
      setError(typeof err === 'string' ? err : 'Failed to load emergency personnel');
    } finally {
      setLoading(false);
    }
  };

  const handlePatientAdded = (newPatient) => {
    setPatients([...patients, newPatient]);
  };

  const handleEmergencyPersonnelAdded = (newPersonnel) => {
    setEmergencyPersonnel([...emergencyPersonnel, newPersonnel]);
  };

  // Sessions helpers
  const fetchSessionsPatients = async () => {
    setSessionsLoading(true);
    setSessionsError('');
    try {
      const data = await getPatients();
      setSessionsPatients(data);
    } catch (err) {
      setSessionsError(typeof err === 'string' ? err : 'Failed to load patients');
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleSelectSessionPatient = async (patient) => {
    setSelectedSessionPatient(patient);
    setPatientSessions([]);
    setExpandedSession(null);
    setPatientSessionsLoading(true);
    try {
      const data = await getPatientSessionsTherapist(patient.id);
      setPatientSessions(data);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setPatientSessionsLoading(false);
    }
  };

  const handleBackToSessionsPatients = () => {
    setSelectedSessionPatient(null);
    setPatientSessions([]);
    setExpandedSession(null);
  };

  const handleSessionFormChange = (e) => {
    setSessionForm({ ...sessionForm, [e.target.name]: e.target.value });
  };

  const handleAddSession = async () => {
    if (!sessionForm.title.trim() || !sessionForm.transcript.trim()) {
      setSessionFormError('Title and transcript are required.');
      return;
    }
    setSessionSaving(true);
    setSessionFormError('');
    try {
      const created = await createTherapySession({
        patient_id: selectedSessionPatient.id,
        ...sessionForm,
      });
      setPatientSessions([created, ...patientSessions]);
      setShowAddModal(false);
      setSessionForm({
        session_date: new Date().toISOString().slice(0, 10),
        title: '',
        transcript: '',
        therapist_notes: '',
      });
    } catch (err) {
      setSessionFormError(typeof err === 'string' ? err : 'Failed to save session');
    } finally {
      setSessionSaving(false);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm('Delete this session? This cannot be undone.')) return;
    try {
      await deleteTherapySession(sessionId);
      setPatientSessions(patientSessions.filter((s) => s.id !== sessionId));
      if (expandedSession === sessionId) setExpandedSession(null);
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handlePatientClick = (patientId) => {
    navigate(`/therapist/patients/${patientId}`);
  };

  const handleEmergencyPersonnelClick = (personnelId) => {
    navigate(`/therapist/emergency-personnel/${personnelId}`);
  };

  const handleStartCall = (patientId) => {
    navigate(`/video-session/therapist/${user.id}/${patientId}`);
  };

  return (
    <div className="therapist-dashboard-container">
      {/* Vintage background similar to landing page */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header with Navigation */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Nirbaan</h1>
          <nav className="nav-menu">
            <button 
              className={`nav-btn ${activeSection === 'patients' ? 'active' : ''}`}
              onClick={() => setActiveSection('patients')}
            >
              Patients
            </button>
            <button 
              className={`nav-btn ${activeSection === 'emergency' ? 'active' : ''}`}
              onClick={() => setActiveSection('emergency')}
            >
              Emergency Personnel
            </button>
            <button 
              className={`nav-btn ${activeSection === 'community' ? 'active' : ''}`}
              onClick={() => setActiveSection('community')}
            >
              Community
            </button>
            <button 
              className={`nav-btn ${activeSection === 'resources' ? 'active' : ''}`}
              onClick={() => setActiveSection('resources')}
            >
              Resources
            </button>
            <button 
              className={`nav-btn ${activeSection === 'tools' ? 'active' : ''}`}
              onClick={() => navigate('/therapist/dashboard/tools')}
            >
              Tools
            </button>
            <button 
              className={`nav-btn ${activeSection === 'history' ? 'active' : ''}`}
              onClick={() => setActiveSection('history')}
            >
              History
            </button>
            <button 
              className="nav-btn"
              onClick={() => navigate('/therapist/nirbaanai')}
            >
              Nirbaan AI
            </button>
            <button
              className="nav-btn"
              onClick={() => navigate('/therapist/chat')}
            >
              Chat
            </button>
            <button
              className={`nav-btn ${activeSection === 'sessions' ? 'active' : ''}`}
              onClick={() => setActiveSection('sessions')}
            >
              Active Sessions
            </button>
            <button
              className={`nav-btn ${activeSection === 'sessionLog' ? 'active' : ''}`}
              onClick={() => setActiveSection('sessionLog')}
            >
              Session Log
            </button>
          </nav>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      {/* Video Call Button - Only on landing page */}
      {!activeSection && (
        <button className="video-call-btn" title="Start Video Call">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
          </svg>
        </button>
      )}

      {/* Main Content */}
      <main className="dashboard-main">
        {activeSection === 'patients' && (
          <div className="patients-section">
            <div className="section-header">
              <h2>Your Patients</h2>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {loading ? (
              <div className="loading-state">
                <div className="spinner"></div>
                <p>Loading patients...</p>
              </div>
            ) : patients.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">👥</div>
                <h3>No Patients Yet</h3>
                <p>Add your first patient to get started with therapy management</p>
              </div>
            ) : (
              <div className="patients-grid">
                {patients.map((patient) => (
                  <div 
                    key={patient.id} 
                    className="patient-card"
                  >
                    <div className="patient-avatar">
                      {patient.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="patient-info">
                      <h3>{patient.name}</h3>
                      <p className="patient-email">{patient.email}</p>
                      <p className="patient-conditions">{patient.conditions}</p>
                    </div>
                    <div className="patient-meta">
                      <span className="patient-date">
                        Added {new Date(patient.created_at).toLocaleDateString()}
                      </span>
                      <div className="patient-actions">
                        <button 
                          className="view-patient-btn"
                          onClick={() => handlePatientClick(patient.id)}
                          title="View Patient"
                        >
                          👤 View
                        </button>
                        <button 
                          className="start-call-btn"
                          onClick={() => handleStartCall(patient.id)}
                          title="Start Video Call"
                        >
                          📹 Start Call
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSection === 'emergency' && (
          <div className="patients-section">
            <div className="section-header">
              <h2>Emergency Personnel</h2>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {loading ? (
              <div className="loading-state">
                <div className="spinner"></div>
                <p>Loading emergency personnel...</p>
              </div>
            ) : emergencyPersonnel.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🚨</div>
                <h3>No Emergency Personnel Yet</h3>
                <p>Add your first emergency personnel to build your crisis response team</p>
              </div>
            ) : (
              <div className="patients-grid">
                {emergencyPersonnel.map((personnel) => (
                  <div 
                    key={personnel.id} 
                    className="patient-card"
                    onClick={() => handleEmergencyPersonnelClick(personnel.id)}
                  >
                    <div className="patient-avatar">
                      {personnel.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="patient-info">
                      <h3>{personnel.name}</h3>
                      <p className="patient-email">{personnel.email}</p>
                      <p className="patient-conditions">{personnel.education}</p>
                    </div>
                    <div className="patient-meta">
                      <span className="patient-date">
                        Added {new Date(personnel.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSection === 'community' && (
          <div className="section-content-blank">
            {/* Community section - to be implemented */}
          </div>
        )}

        {activeSection === 'resources' && (
          <div className="section-content">
            <ResourceManager />
          </div>
        )}

        {activeSection === 'history' && (
          <div className="section-content">
            <PatientHistory />
          </div>
        )}



        {activeSection === 'sessions' && (
          <div className="section-content">
            <ActiveSessions />
          </div>
        )}

        {activeSection === 'sessionLog' && (
          <div className="sessions-section">

            {/* ── Step 1: patient picker ── */}
            {!selectedSessionPatient && (
              <>
                <div className="sessions-section-header">
                  <h2 className="sessions-section-title">Sessions — Select a Patient</h2>
                </div>

                {sessionsLoading && (
                  <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading patients...</p>
                  </div>
                )}
                {sessionsError && <div className="error-banner">{sessionsError}</div>}

                {!sessionsLoading && sessionsPatients.length === 0 && !sessionsError && (
                  <div className="empty-state">
                    <div className="empty-icon">👥</div>
                    <h3>No Patients Yet</h3>
                    <p>Add patients first before logging sessions.</p>
                  </div>
                )}

                {!sessionsLoading && (
                  <div className="patients-grid">
                    {sessionsPatients.map((patient) => (
                      <div
                        key={patient.id}
                        className="patient-card sessions-patient-card"
                        onClick={() => handleSelectSessionPatient(patient)}
                      >
                        <div className="patient-avatar">
                          {patient.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="patient-info">
                          <h3>{patient.name}</h3>
                          <p className="patient-email">{patient.email}</p>
                          <p className="patient-conditions">{patient.conditions}</p>
                        </div>
                        <div className="patient-meta">
                          <span className="view-sessions-hint">View Sessions →</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* ── Step 2: sessions list for selected patient ── */}
            {selectedSessionPatient && (
              <>
                <div className="sessions-section-header">
                  <div className="sessions-breadcrumb">
                    <button className="sessions-back-btn" onClick={handleBackToSessionsPatients}>
                      ← All Patients
                    </button>
                    <span className="sessions-breadcrumb-sep">/</span>
                    <span className="sessions-breadcrumb-patient">
                      {selectedSessionPatient.name}
                    </span>
                  </div>
                  <button
                    className="add-session-btn"
                    onClick={() => { setShowAddModal(true); setSessionFormError(''); }}
                  >
                    + Add Session
                  </button>
                </div>

                {patientSessionsLoading && (
                  <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading sessions...</p>
                  </div>
                )}

                {!patientSessionsLoading && patientSessions.length === 0 && (
                  <div className="sessions-empty">
                    <p>
                      No sessions logged yet for <strong>{selectedSessionPatient.name}</strong>.
                      Click <strong>+ Add Session</strong> to log the first one.
                    </p>
                  </div>
                )}

                <div className="sessions-list">
                  {patientSessions.map((s) => (
                    <div key={s.id} className="session-card">
                      <button
                        className="session-card-header"
                        onClick={() => setExpandedSession(expandedSession === s.id ? null : s.id)}
                      >
                        <div className="session-card-meta">
                          <span className="session-badge">Session {s.session_number}</span>
                          <span className="session-title-text">{s.title}</span>
                          <span className="session-date-text">
                            {new Date(s.session_date).toLocaleDateString('en-US', {
                              year: 'numeric', month: 'long', day: 'numeric',
                            })}
                          </span>
                        </div>
                        <span className="session-chevron">{expandedSession === s.id ? '▲' : '▼'}</span>
                      </button>

                      {expandedSession === s.id && (
                        <div className="session-card-body">
                          <div className="session-body-section">
                            <h4 className="session-body-label">Transcript</h4>
                            <pre className="session-transcript">{s.transcript}</pre>
                          </div>
                          {s.therapist_notes && (
                            <div className="session-body-section">
                              <h4 className="session-body-label">
                                Therapist Notes
                                <span className="notes-private-badge">Private</span>
                              </h4>
                              <p className="session-notes-text">{s.therapist_notes}</p>
                            </div>
                          )}
                          <div className="session-card-actions">
                            <button
                              className="session-delete-btn"
                              onClick={() => handleDeleteSession(s.id)}
                            >
                              Delete Session
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Add Session Modal */}
                {showAddModal && (
                  <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
                    <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                      <div className="modal-header">
                        <h3>Log New Session — {selectedSessionPatient.name}</h3>
                        <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>✕</button>
                      </div>

                      {sessionFormError && <p className="modal-error">{sessionFormError}</p>}

                      <div className="modal-field">
                        <label>Session Date</label>
                        <input
                          type="date"
                          name="session_date"
                          value={sessionForm.session_date}
                          onChange={handleSessionFormChange}
                          className="modal-input"
                        />
                      </div>

                      <div className="modal-field">
                        <label>Title</label>
                        <input
                          type="text"
                          name="title"
                          value={sessionForm.title}
                          onChange={handleSessionFormChange}
                          placeholder="e.g. Session 1 – Exposure Hierarchy"
                          className="modal-input"
                        />
                      </div>

                      <div className="modal-field">
                        <label>
                          Transcript
                          <span className="field-hint"> (full 60-min session transcript)</span>
                        </label>
                        <textarea
                          name="transcript"
                          value={sessionForm.transcript}
                          onChange={handleSessionFormChange}
                          rows={12}
                          placeholder="Paste or type the session transcript here..."
                          className="modal-textarea"
                        />
                      </div>

                      <div className="modal-field">
                        <label>
                          Therapist Notes
                          <span className="field-hint"> (private – not visible to patient)</span>
                        </label>
                        <textarea
                          name="therapist_notes"
                          value={sessionForm.therapist_notes}
                          onChange={handleSessionFormChange}
                          rows={4}
                          placeholder="Private notes for your reference..."
                          className="modal-textarea"
                        />
                      </div>

                      <div className="modal-actions">
                        <button className="modal-cancel-btn" onClick={() => setShowAddModal(false)}>Cancel</button>
                        <button className="modal-save-btn" onClick={handleAddSession} disabled={sessionSaving}>
                          {sessionSaving ? 'Saving...' : 'Save Session'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>

      {/* Floating Add Patient Button */}
      {activeSection === 'patients' && (
        <div className="floating-add-patient">
          <AddPatient onPatientAdded={handlePatientAdded} />
        </div>
      )}

      {/* Floating Add Emergency Personnel Button */}
      {activeSection === 'emergency' && (
        <div className="floating-add-patient">
          <AddEmergencyPersonnel onPersonnelAdded={handleEmergencyPersonnelAdded} />
        </div>
      )}
    </div>
  );
};

export default TherapistDashboard;