import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import PatientSelfMonitoring from '../components/PatientSelfMonitoring';
import './PatientFearLadderMonitoring.css';

const PatientFearLadderMonitoring = () => {
  const navigate = useNavigate();
  const { logout } = useAuthStore();

  const handleBack = () => {
    navigate('/patient/dashboard/fear-ladder');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="monitoring-page-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Daily Self-Monitoring Log</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="monitoring-main">
        <div className="monitoring-content-wrapper">
          <PatientSelfMonitoring isEmbedded={false} />
        </div>
      </main>
    </div>
  );
};

export default PatientFearLadderMonitoring;
