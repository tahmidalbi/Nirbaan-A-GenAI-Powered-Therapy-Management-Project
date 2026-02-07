import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { getPatients } from '../api/patient.api';
import AddPatient from '../components/AddPatient';
import './TherapistDashboard.css';

const TherapistDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeSection, setActiveSection] = useState(null);

  useEffect(() => {
    if (activeSection === 'patients') {
      fetchPatients();
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

  const handlePatientAdded = (newPatient) => {
    setPatients([...patients, newPatient]);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handlePatientClick = (patientId) => {
    navigate(`/therapist/patients/${patientId}`);
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
              className={`nav-btn ${activeSection === 'history' ? 'active' : ''}`}
              onClick={() => setActiveSection('history')}
            >
              History
            </button>
            <button 
              className={`nav-btn ${activeSection === 'ai' ? 'active' : ''}`}
              onClick={() => setActiveSection('ai')}
            >
              Nirbaan AI
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
                    onClick={() => handlePatientClick(patient.id)}
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
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSection === 'emergency' && (
          <div className="section-content-blank">
            {/* Emergency Personnel section - to be implemented */}
          </div>
        )}

        {activeSection === 'community' && (
          <div className="section-content-blank">
            {/* Community section - to be implemented */}
          </div>
        )}

        {activeSection === 'resources' && (
          <div className="section-content-blank">
            {/* Resources section - to be implemented */}
          </div>
        )}

        {activeSection === 'history' && (
          <div className="section-content-blank">
            {/* History section - to be implemented */}
          </div>
        )}

        {activeSection === 'ai' && (
          <div className="section-content-blank">
            {/* Nirbaan AI section - to be implemented */}
          </div>
        )}
      </main>

      {/* Floating Add Patient Button */}
      {activeSection === 'patients' && (
        <div className="floating-add-patient">
          <AddPatient onPatientAdded={handlePatientAdded} />
        </div>
      )}
    </div>
  );
};

export default TherapistDashboard;