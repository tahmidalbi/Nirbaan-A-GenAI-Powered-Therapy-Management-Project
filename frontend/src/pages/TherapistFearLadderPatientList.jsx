import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getAllFearLadders } from '../api/fear-ladder.api';
import './TherapistFearLadderPatientList.css';

const TherapistFearLadderPatientList = () => {
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    fetchAllLadders();
  }, []);

  const fetchAllLadders = async () => {
    try {
      setLoading(true);
      const response = await getAllFearLadders();
      const ladders = response.data || [];
      // Deduplicate by patient_id — keep the most recent per patient
      const seen = new Set();
      const unique = [];
      ladders.forEach((l) => {
        if (!seen.has(l.patient_id)) {
          seen.add(l.patient_id);
          unique.push(l);
        }
      });
      setPatients(unique);
    } catch (error) {
      console.error('Error fetching fear ladders:', error);
      setErrorMessage('Error loading patients.');
      setTimeout(() => setErrorMessage(''), 5000);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/therapist/dashboard');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handlePatientClick = (ladder) => {
    navigate(`/therapist/dashboard/fear-ladder/patient/${ladder.patient_id}`, {
      state: {
        patientName: ladder.patient_name,
        patientEmail: ladder.patient_email
      }
    });
  };

  return (
    <div className="patient-list-container">
      {/* Background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Fear Ladder — Patients</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="patient-list-main">
        <div className="list-content-wrapper">
          {errorMessage && (
            <div className="fl-error-message">{errorMessage}</div>
          )}

          {loading ? (
            <div className="loading-message">Loading patients…</div>
          ) : patients.length === 0 ? (
            <div className="no-data-message">
              <h3>No Patients Yet</h3>
              <p>Patients who have submitted fear ladders will appear here</p>
            </div>
          ) : (
            <div className="fl-patient-list">
              <p className="fl-list-intro">{patients.length} patient{patients.length !== 1 ? 's' : ''} with fear ladders</p>
              {patients.map((ladder) => (
                <button
                  key={ladder.patient_id}
                  className="fl-patient-row"
                  onClick={() => handlePatientClick(ladder)}
                >
                  <div className="fl-patient-row-left">
                    <span className="fl-patient-avatar">
                      {(ladder.patient_name || 'P').charAt(0).toUpperCase()}
                    </span>
                    <span className="fl-patient-name">{ladder.patient_name || `Patient ${ladder.patient_id}`}</span>
                  </div>
                  <div className="fl-patient-row-right">
                    <span className={`fl-status-badge fl-status-${ladder.status}`}>
                      {ladder.status}
                    </span>
                    <span className="fl-arrow">→</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default TherapistFearLadderPatientList;
