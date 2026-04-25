import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import TherapistSelfMonitoringView from '../components/TherapistSelfMonitoringView';
import './TherapistFearLadderMonitoring.css';

const TherapistFearLadderMonitoring = () => {
  const navigate = useNavigate();
  const { logout } = useAuthStore();

  const handleBack = () => {
    navigate('/therapist/dashboard/fear-ladder');
  };

  const handleLogout = () => {
    logout();
    navigate('/select-role');
  };

  return (
    <div className="therapist-monitoring-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Patient Self-Monitoring Logs</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="therapist-monitoring-main">
        <div className="monitoring-content-wrapper">
          <TherapistSelfMonitoringView isEmbedded={false} />
        </div>
      </main>
    </div>
  );
};

export default TherapistFearLadderMonitoring;
