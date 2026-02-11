import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAllPatientsProgress } from '../api/progress.api';
import './PatientHistoryList.css';

const PatientHistoryList = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  const handlePatientClick = (patientId) => {
    navigate(`/therapist/history/${patientId}`);
  };

  if (loading) {
    return (
      <div className="history-list-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading patient records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="history-list-container">
      {/* Decorative header */}
      <div className="history-header">
        <div className="header-ornament header-ornament-left"></div>
        <h1 className="history-title">Patient History</h1>
        <div className="header-ornament header-ornament-right"></div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Patient grid */}
      <div className="patient-grid">
        {patients.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No Patients Yet</h3>
            <p>Patients you add will appear here</p>
          </div>
        ) : (
          patients.map((patient) => (
            <div
              key={patient.patient_id}
              className="patient-card-elegant"
              onClick={() => handlePatientClick(patient.patient_id)}
            >
              <div className="card-decorative-corner top-left"></div>
              <div className="card-decorative-corner top-right"></div>
              <div className="card-decorative-corner bottom-left"></div>
              <div className="card-decorative-corner bottom-right"></div>
              
              <div className="patient-card-content">
                <div className="patient-initial">{patient.patient_name.charAt(0)}</div>
                
                <div className="patient-info">
                  <h3 className="patient-name">{patient.patient_name}</h3>
                  <p className="patient-email">{patient.patient_email}</p>
                  <div className="patient-conditions">
                    <span className="conditions-icon">⚕</span>
                    <span>{patient.conditions}</span>
                  </div>
                </div>

                <div className="patient-progress-badge">
                  {patient.current_week === 0 ? (
                    <span className="badge-initial">Not Started</span>
                  ) : (
                    <span className="badge-week">Week {patient.current_week}</span>
                  )}
                </div>

                <div className="card-action">
                  <span className="action-text">View Records</span>
                  <span className="action-arrow">→</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default PatientHistoryList;
