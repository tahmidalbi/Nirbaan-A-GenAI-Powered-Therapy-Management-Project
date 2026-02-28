import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getAllFearLadders } from '../api/fear-ladder.api';
import './TherapistFearLadderPatientList.css';

const TherapistFearLadderPatientList = () => {
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  const [allLadders, setAllLadders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    fetchAllLadders();
  }, []);

  const fetchAllLadders = async () => {
    try {
      setLoading(true);
      const response = await getAllFearLadders();
      setAllLadders(response.data || []);
    } catch (error) {
      console.error('Error fetching fear ladders:', error);
      setErrorMessage('Error loading fear ladders.');
      setTimeout(() => setErrorMessage(''), 5000);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/therapist/dashboard/fear-ladder');
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

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved':
        return 'status-approved';
      case 'pending':
        return 'status-pending';
      case 'rejected':
        return 'status-rejected';
      default:
        return '';
    }
  };

  return (
    <div className="patient-list-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Patient Fear Ladders</h1>
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
            <div className="error-message">
              {errorMessage}
            </div>
          )}

          {loading ? (
            <div className="loading-message">Loading patient fear ladders...</div>
          ) : allLadders.length === 0 ? (
            <div className="no-data-message">
              <h3>No Fear Ladders Yet</h3>
              <p>Fear ladders submitted by patients will appear here</p>
            </div>
          ) : (
            <div className="patients-grid">
              {allLadders.map((ladder) => (
                <div 
                  key={ladder.patient_id} 
                  className="patient-card"
                  onClick={() => handlePatientClick(ladder)}
                >
                  <div className="patient-card-header">
                    <h3>{ladder.patient_name}</h3>
                    <span className={`status-badge ${getStatusColor(ladder.status)}`}>
                      {ladder.status.charAt(0).toUpperCase() + ladder.status.slice(1)}
                    </span>
                  </div>
                  <div className="patient-card-body">
                    <p className="patient-email">{ladder.patient_email}</p>
                    <p className="patient-items">
                      {ladder.items?.length || 0} fear ladder items
                    </p>
                  </div>
                  <div className="patient-card-footer">
                    <span className="view-link">View Details →</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default TherapistFearLadderPatientList;
