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
import AddPatient from '../components/AddPatient';
import AddEmergencyPersonnel from '../components/AddEmergencyPersonnel';
import ResourceManager from '../components/ResourceManager';
import PatientHistory from '../components/PatientHistory';
import ActiveSessions from '../components/ActiveSessions';
import TherapistChat from '../components/TherapistChat';
import NirbaanAITherapistChat from '../components/NirbaanAITherapistChat';
import './TherapistDashboard.css';

/* ─── Back-destination map ──────────────────────────────────────── */
const BACK_MAP = {
  patients: 'personnel',
  emergency: 'personnel',
  live_sessions: 'sessions',
  active_sessions: 'sessions',
  personnel: null,
  community: null,
  resources: null,
  tools: null,
  history: null,
  sessions: null,
  nirbaan_ai: null,
  payment: null,
};

const VIEW_LABELS = {
  personnel: 'Personnel',
  patients: 'Patients',
  emergency: 'Emergency Personnel',
  community: 'Community',
  resources: 'Resources',
  tools: 'Tools',
  history: 'History',
  sessions: 'Sessions',
  live_sessions: 'Live Sessions',
  active_sessions: 'Active Sessions',
  nirbaan_ai: 'Nirbaan AI',
};

const TherapistDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const [patients, setPatients] = useState([]);
  const [emergencyPersonnel, setEmergencyPersonnel] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [view, setView] = useState(null);

  // Sessions section state (therapy transcripts)
  const [sessionsPatients, setSessionsPatients] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState('');
  const [selectedSessionPatient, setSelectedSessionPatient] = useState(null);
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
    if (view === 'patients') {
      fetchPatients();
    } else if (view === 'emergency') {
      fetchEmergencyPersonnel();
    } else if (view === 'active_sessions') {
      fetchSessionsPatients();
    }
  }, [view]);

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

  // Sessions helpers (therapy transcripts)
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

  const goTo = (v) => setView(v);
  const goBack = () => setView(BACK_MAP[view] ?? null);

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
    <div className="td-root">
      {/* Decorative background */}
      <div className="td-bg">
        <div className="td-bg-grid" />
        <div className="td-bg-orb td-bg-orb--1" />
        <div className="td-bg-orb td-bg-orb--2" />
      </div>

      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="td-header">
        <div className="td-header-inner">
          <div className="td-brand">
            <span className="td-brand-logo">Nirbaan</span>
            {view && (
              <span className="td-brand-breadcrumb">
                <span className="td-brand-sep">/</span>
                {VIEW_LABELS[view] || view}
              </span>
            )}
          </div>
          <div className="td-header-actions">
            {view && (
              <button className="td-back-btn" onClick={goBack}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 12H5M12 5l-7 7 7 7" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Back
              </button>
            )}
            <button className="td-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────── */}
      <main className="td-main">

        {/* HOME — 7 main tiles */}
        {!view && (
          <div className="td-home">
            <div className="td-welcome">
              <p className="td-welcome-greeting">Welcome back,</p>
              <h1 className="td-welcome-name">{user?.name || 'Doctor'}</h1>
              <p className="td-welcome-sub">Your therapeutic practice dashboard</p>
            </div>

            <div className="td-tiles-grid td-tiles-grid--home">
              <button className="td-tile" onClick={() => goTo('personnel')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round"/>
                    <circle cx="9" cy="7" r="4" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Personnel</span>
                <span className="td-tile-sub">Patients &amp; emergency contacts</span>
              </button>

              <button className="td-tile" onClick={() => navigate('/therapist/chat')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Community</span>
                <span className="td-tile-sub">Group chat &amp; messaging</span>
              </button>

              <button className="td-tile" onClick={() => goTo('resources')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Resources</span>
                <span className="td-tile-sub">Therapeutic library</span>
              </button>

              <button className="td-tile" onClick={() => goTo('tools')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Tools</span>
                <span className="td-tile-sub">Clinical assessment tools</span>
              </button>

              <button className="td-tile" onClick={() => goTo('history')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10" strokeLinecap="round" strokeLinejoin="round"/>
                    <polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">History</span>
                <span className="td-tile-sub">Patient records &amp; notes</span>
              </button>

              <button className="td-tile" onClick={() => goTo('sessions')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <line x1="16" y1="2" x2="16" y2="6" strokeLinecap="round" strokeLinejoin="round"/>
                    <line x1="8" y1="2" x2="8" y2="6" strokeLinecap="round" strokeLinejoin="round"/>
                    <line x1="3" y1="10" x2="21" y2="10" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Sessions</span>
                <span className="td-tile-sub">Manage therapy sessions</span>
              </button>

              <button className="td-tile td-tile--ai" onClick={() => goTo('nirbaan_ai')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 2a6 6 0 0 1 6 6c0 4-6 12-6 12S6 12 6 8a6 6 0 0 1 6-6z" strokeLinecap="round" strokeLinejoin="round"/>
                    <circle cx="12" cy="8" r="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M8 21h8M9 18l1.5-3h3L15 18" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Nirbaan AI</span>
                <span className="td-tile-sub">AI-powered clinical support</span>
              </button>
            </div>
          </div>
        )}

        {/* PERSONNEL SUB-MENU */}
        {view === 'personnel' && (
          <div className="td-submenu">
            <h2 className="td-submenu-title">Personnel</h2>
            <p className="td-submenu-sub">Select a category to manage</p>
            <div className="td-tiles-grid td-tiles-grid--sub">
              <button className="td-tile td-tile--large" onClick={() => goTo('patients')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round"/>
                    <circle cx="12" cy="7" r="4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Patients</span>
                <span className="td-tile-sub">View &amp; manage patient list</span>
              </button>

              <button className="td-tile td-tile--large" onClick={() => goTo('emergency')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.22h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6 6l.91-.91a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7a2 2 0 0 1 1.72 2.02z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Emergency Personnel</span>
                <span className="td-tile-sub">Crisis response contacts</span>
              </button>
            </div>
          </div>
        )}

        {/* SESSIONS SUB-MENU */}
        {view === 'sessions' && (
          <div className="td-submenu">
            <h2 className="td-submenu-title">Sessions</h2>
            <p className="td-submenu-sub">Select a session type</p>
            <div className="td-tiles-grid td-tiles-grid--sub">
              <button className="td-tile td-tile--large" onClick={() => goTo('live_sessions')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <polygon points="23 7 16 12 23 17 23 7" strokeLinecap="round" strokeLinejoin="round"/>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Live Sessions</span>
                <span className="td-tile-sub">Real-time video consultations</span>
              </button>

              <button className="td-tile td-tile--large" onClick={() => goTo('active_sessions')}>
                <span className="td-tile-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round"/>
                    <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round"/>
                    <line x1="16" y1="13" x2="8" y2="13" strokeLinecap="round" strokeLinejoin="round"/>
                    <line x1="16" y1="17" x2="8" y2="17" strokeLinecap="round" strokeLinejoin="round"/>
                    <polyline points="10 9 9 9 8 9" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span className="td-tile-label">Active Sessions</span>
                <span className="td-tile-sub">Transcripts &amp; session records</span>
              </button>
            </div>
          </div>
        )}

        {/* PATIENTS LIST */}
        {view === 'patients' && (
          <div className="td-content-panel">
            <div className="td-panel-header">
              <h2>Patients</h2>
            </div>
            {error && <div className="td-error-banner">{error}</div>}
            {loading ? (
              <div className="td-loading"><span className="td-spinner" /><p>Loading patients…</p></div>
            ) : patients.length === 0 ? (
              <div className="td-empty">
                <span className="td-empty-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                  </svg>
                </span>
                <h3>No Patients Yet</h3>
                <p>Add your first patient to get started</p>
              </div>
            ) : (
              <div className="td-cards-grid">
                {patients.map((patient) => (
                  <div key={patient.id} className="td-card">
                    <div className="td-card-avatar">{patient.name.charAt(0).toUpperCase()}</div>
                    <div className="td-card-body">
                      <h3>{patient.name}</h3>
                      <p className="td-card-meta">{patient.email}</p>
                      <p className="td-card-tag">{patient.conditions}</p>
                    </div>
                    <div className="td-card-footer">
                      <span className="td-card-date">Added {new Date(patient.created_at).toLocaleDateString()}</span>
                      <div className="td-card-actions">
                        <button className="td-btn td-btn--outline" onClick={() => handlePatientClick(patient.id)}>View</button>
                        <button className="td-btn td-btn--primary" onClick={() => handleStartCall(patient.id)}>
                          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg>
                          Call
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* EMERGENCY PERSONNEL LIST */}
        {view === 'emergency' && (
          <div className="td-content-panel">
            <div className="td-panel-header">
              <h2>Emergency Personnel</h2>
            </div>
            {error && <div className="td-error-banner">{error}</div>}
            {loading ? (
              <div className="td-loading"><span className="td-spinner" /><p>Loading personnel…</p></div>
            ) : emergencyPersonnel.length === 0 ? (
              <div className="td-empty">
                <span className="td-empty-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6 6l.91-.91a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 18z"/>
                  </svg>
                </span>
                <h3>No Emergency Personnel Yet</h3>
                <p>Add emergency contacts to build your crisis response team</p>
              </div>
            ) : (
              <div className="td-cards-grid">
                {emergencyPersonnel.map((personnel) => (
                  <div key={personnel.id} className="td-card" onClick={() => handleEmergencyPersonnelClick(personnel.id)} style={{cursor:'pointer'}}>
                    <div className="td-card-avatar td-card-avatar--emergency">{personnel.name.charAt(0).toUpperCase()}</div>
                    <div className="td-card-body">
                      <h3>{personnel.name}</h3>
                      <p className="td-card-meta">{personnel.email}</p>
                      <p className="td-card-tag">{personnel.education}</p>
                    </div>
                    <div className="td-card-footer">
                      <span className="td-card-date">Added {new Date(personnel.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* COMMUNITY (Chat) */}
        {view === 'community' && (
          <div className="td-fullpage-view">
            <TherapistChat />
          </div>
        )}

        {/* RESOURCES */}
        {view === 'resources' && (
          <div className="td-fullpage-view">
            <ResourceManager />
          </div>
        )}

        {/* TOOLS */}
        {view === 'tools' && (
          <div className="td-content-panel">
            <div className="td-panel-header">
              <h2>Clinical Tools</h2>
            </div>
            <div className="td-tools-grid">
              <button className="td-tool-card" onClick={() => navigate('/therapist/dashboard/fear-ladder/patients')}>
                <span className="td-tool-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <line x1="8" y1="6" x2="21" y2="6" strokeLinecap="round"/><line x1="8" y1="12" x2="21" y2="12" strokeLinecap="round"/><line x1="8" y1="18" x2="21" y2="18" strokeLinecap="round"/>
                    <line x1="3" y1="6" x2="3.01" y2="6" strokeLinecap="round"/><line x1="3" y1="12" x2="3.01" y2="12" strokeLinecap="round"/><line x1="3" y1="18" x2="3.01" y2="18" strokeLinecap="round"/>
                  </svg>
                </span>
                <h3>Fear Ladder Maker</h3>
                <p>Create and manage exposure hierarchies for your patients</p>
                <span className="td-tool-arrow">→</span>
              </button>

              <button className="td-tool-card" onClick={() => navigate('/therapist/dashboard/erp')}>
                <span className="td-tool-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <h3>ERP Workspace</h3>
                <p>Monitor and guide patient exposure exercises</p>
                <span className="td-tool-arrow">→</span>
              </button>

              <button className="td-tool-card" onClick={() => navigate('/therapist/dashboard/imaginal')}>
                <span className="td-tool-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10" strokeLinecap="round"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" strokeLinecap="round"/><line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round"/>
                  </svg>
                </span>
                <h3>Imaginal Exposures</h3>
                <p>Design and track imaginal exposure protocols</p>
                <span className="td-tool-arrow">→</span>
              </button>
            </div>
          </div>
        )}

        {/* HISTORY */}
        {view === 'history' && (
          <div className="td-content-panel">
            <PatientHistory />
          </div>
        )}



        {/* LIVE SESSIONS */}
        {view === 'live_sessions' && (
          <div className="td-content-panel">
            <ActiveSessions />
          </div>
        )}

        {/* ACTIVE SESSIONS (transcripts) */}
        {view === 'active_sessions' && (
          <div className="td-content-panel">
            {/* Step 1: patient picker */}
            {!selectedSessionPatient && (
              <>
                <div className="td-panel-header">
                  <h2>Active Sessions — Select a Patient</h2>
                </div>
                {sessionsLoading && <div className="td-loading"><span className="td-spinner" /><p>Loading…</p></div>}
                {sessionsError && <div className="td-error-banner">{sessionsError}</div>}
                {!sessionsLoading && sessionsPatients.length === 0 && !sessionsError && (
                  <div className="td-empty"><h3>No Patients Yet</h3><p>Add patients first before logging sessions.</p></div>
                )}
                {!sessionsLoading && (
                  <div className="td-cards-grid">
                    {sessionsPatients.map((patient) => (
                      <div key={patient.id} className="td-card td-card--clickable" onClick={() => handleSelectSessionPatient(patient)}>
                        <div className="td-card-avatar">{patient.name.charAt(0).toUpperCase()}</div>
                        <div className="td-card-body">
                          <h3>{patient.name}</h3>
                          <p className="td-card-meta">{patient.email}</p>
                          <p className="td-card-tag">{patient.conditions}</p>
                        </div>
                        <div className="td-card-footer">
                          <span className="td-card-date">View Sessions →</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Step 2: sessions for selected patient */}
            {selectedSessionPatient && (
              <>
                <div className="td-panel-header td-panel-header--split">
                  <div className="td-breadcrumb-row">
                    <button className="td-back-inline" onClick={handleBackToSessionsPatients}>← All Patients</button>
                    <span className="td-sep">/</span>
                    <span className="td-crumb-name">{selectedSessionPatient.name}</span>
                  </div>
                  <button className="td-btn td-btn--primary" onClick={() => { setShowAddModal(true); setSessionFormError(''); }}>
                    + Add Session
                  </button>
                </div>

                {patientSessionsLoading && <div className="td-loading"><span className="td-spinner" /><p>Loading sessions…</p></div>}
                {!patientSessionsLoading && patientSessions.length === 0 && (
                  <div className="td-empty"><p>No sessions logged yet for <strong>{selectedSessionPatient.name}</strong>.</p></div>
                )}

                <div className="sessions-list">
                  {patientSessions.map((s) => (
                    <div key={s.id} className="session-card">
                      <button className="session-card-header" onClick={() => setExpandedSession(expandedSession === s.id ? null : s.id)}>
                        <div className="session-card-meta">
                          <span className="session-badge">Session {s.session_number}</span>
                          <span className="session-title-text">{s.title}</span>
                          <span className="session-date-text">{new Date(s.session_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
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
                              <h4 className="session-body-label">Therapist Notes <span className="notes-private-badge">Private</span></h4>
                              <p className="session-notes-text">{s.therapist_notes}</p>
                            </div>
                          )}
                          <div className="session-card-actions">
                            <button className="session-delete-btn" onClick={() => handleDeleteSession(s.id)}>Delete Session</button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {showAddModal && (
                  <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
                    <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                      <div className="modal-header">
                        <h3>Log New Session — {selectedSessionPatient.name}</h3>
                        <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>✕</button>
                      </div>
                      {sessionFormError && <p className="modal-error">{sessionFormError}</p>}
                      <div className="modal-field"><label>Session Date</label><input type="date" name="session_date" value={sessionForm.session_date} onChange={handleSessionFormChange} className="modal-input" /></div>
                      <div className="modal-field"><label>Title</label><input type="text" name="title" value={sessionForm.title} onChange={handleSessionFormChange} placeholder="e.g. Session 1 – Exposure Hierarchy" className="modal-input" /></div>
                      <div className="modal-field">
                        <label>Transcript <span className="field-hint">(full session transcript)</span></label>
                        <textarea name="transcript" value={sessionForm.transcript} onChange={handleSessionFormChange} rows={12} placeholder="Paste or type the session transcript here…" className="modal-textarea" />
                      </div>
                      <div className="modal-field">
                        <label>Therapist Notes <span className="field-hint">(private – not visible to patient)</span></label>
                        <textarea name="therapist_notes" value={sessionForm.therapist_notes} onChange={handleSessionFormChange} rows={4} placeholder="Private notes for your reference…" className="modal-textarea" />
                      </div>
                      <div className="modal-actions">
                        <button className="modal-cancel-btn" onClick={() => setShowAddModal(false)}>Cancel</button>
                        <button className="modal-save-btn" onClick={handleAddSession} disabled={sessionSaving}>{sessionSaving ? 'Saving…' : 'Save Session'}</button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* NIRBAAN AI */}
        {view === 'nirbaan_ai' && (
          <div className="td-fullpage-view td-fullpage-view--cover">
            <NirbaanAITherapistChat onBack={() => goTo(null)} />
          </div>
        )}

      </main>

      {/* Floating Add Patient */}
      {view === 'patients' && (
        <div className="td-fab-zone">
          <AddPatient onPatientAdded={handlePatientAdded} />
        </div>
      )}

      {/* Floating Add Emergency Personnel */}
      {view === 'emergency' && (
        <div className="td-fab-zone">
          <AddEmergencyPersonnel onPersonnelAdded={handleEmergencyPersonnelAdded} />
        </div>
      )}
    </div>
  );
};

export default TherapistDashboard;
