import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import PatientSelfMonitoring from '../components/PatientSelfMonitoring';
import '../dashboards/PatientDashboard.css';
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
      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>Daily Self-Monitoring Log</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={handleBack}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="monitoring-main">
        <div className="monitoring-content-wrapper">
          <PatientSelfMonitoring isEmbedded={true} />
        </div>
      </main>
    </div>
  );
};

export default PatientFearLadderMonitoring;
