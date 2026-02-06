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
  const [showPatients, setShowPatients] = useState(false);

  useEffect(() => {
    fetchPatients();
  }, []);

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
              className={`nav-btn ${showPatients ? 'active' : ''}`}
              onClick={() => setShowPatients(!showPatients)}
            >
              Patients
            </button>
          </nav>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      {/* Main Content */}
      <main className="dashboard-main">
        {!showPatients ? (
          <div className="welcome-section">
            <h2>Welcome, Dr. {user?.name}</h2>
            <p className="subtitle">Manage your patients and therapy sessions</p>
            <div className="quick-actions">
              <button className="action-card" onClick={() => setShowPatients(true)}>
                <span className="action-icon">👥</span>
                <h3>View Patients</h3>
                <p>Access your patient list</p>
              </button>
            </div>
          </div>
        ) : (
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
      </main>

      {/* Floating Add Patient Button */}
      {showPatients && (
        <div className="floating-add-patient">
          <AddPatient onPatientAdded={handlePatientAdded} />
        </div>
      )}
    </div>
  );
};

export default TherapistDashboard;