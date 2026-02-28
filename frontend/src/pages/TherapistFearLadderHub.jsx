import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './TherapistFearLadderHub.css';

const TherapistFearLadderHub = () => {
  const navigate = useNavigate();
  const { logout } = useAuthStore();

  const handleBack = () => {
    navigate('/therapist/dashboard/tools');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNavigate = (path) => {
    navigate(path);
  };

  return (
    <div className="therapist-hub-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Fear Ladder Maker - Therapist</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="therapist-hub-main">
        <div className="hub-intro">
          <h2>Fear Ladder Management</h2>
          <p>Review and manage patient fear ladders and monitor their progress</p>
        </div>

        <div className="hub-options-grid">
          {/* Patient Fear Ladders Card */}
          <div 
            className="option-card card-patients"
            onClick={() => handleNavigate('/therapist/dashboard/fear-ladder/patients')}
          >
            <div className="card-icon card-icon-hidden">📋</div>
            <div className="card-content">
              <h3>Patient Fear Ladders</h3>
              <p>View, edit, and approve fear ladders submitted by your patients</p>
              <div className="card-action">
                <span>View Patients →</span>
              </div>
            </div>
          </div>

          {/* Self-Monitoring Log Card */}
          <div 
            className="option-card card-monitoring"
            onClick={() => handleNavigate('/therapist/dashboard/fear-ladder/monitoring')}
          >
            <div className="card-icon card-icon-hidden">📊</div>
            <div className="card-content">
              <h3>Daily Self-Monitoring Log</h3>
              <p>Review patient self-monitoring entries and track their progress</p>
              <div className="card-action">
                <span>View Logs →</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TherapistFearLadderHub;
