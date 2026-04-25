import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import '../dashboards/PatientDashboard.css';
import './ERPWorkspace.css';

const ERPWorkspace = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/select-role');
  };

  return (
    <div className="erp-workspace-root">
      {/* Background */}
      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      {/* Header */}
      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>ERP Workspace</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={() => navigate('/patient/dashboard/tools/ocd')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="erp-main">
        <p className="erp-subtitle">
          Exposure &amp; Response Prevention — choose how to proceed
        </p>

        <div className="erp-boxes-grid">
          {/* Plan your recovery */}
          <button
            className="pd-tile erp-tile"
            onClick={() => navigate('/patient/dashboard/erp/plan')}
          >
            <div className="pd-tile-icon">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="8" y="6" width="32" height="36" rx="3" stroke="currentColor" strokeWidth="2.5" fill="none"/>
                <line x1="15" y1="16" x2="33" y2="16" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                <line x1="15" y1="23" x2="33" y2="23" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                <line x1="15" y1="30" x2="25" y2="30" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                <circle cx="11" cy="16" r="1.5" fill="currentColor"/>
                <circle cx="11" cy="23" r="1.5" fill="currentColor"/>
                <circle cx="11" cy="30" r="1.5" fill="currentColor"/>
              </svg>
            </div>
            <h2 className="pd-tile-label">Plan Your Recovery</h2>
            <p className="erp-tile-desc">
              Map out your obsessions, compulsions, and prescribed exercises to build
              a personalised ERP plan.
            </p>
          </button>

          {/* Dive in */}
          <button
            className="pd-tile erp-tile"
            onClick={() => navigate('/patient/dashboard/erp/dive-in')}
          >
            <div className="pd-tile-icon">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="24" cy="24" r="16" stroke="currentColor" strokeWidth="2.5" fill="none"/>
                <polygon points="20,17 34,24 20,31" fill="currentColor" opacity="0.85"/>
              </svg>
            </div>
            <h2 className="pd-tile-label">Dive In</h2>
            <p className="erp-tile-desc">
              Start your exposure exercises and track your progress session by session.
            </p>
          </button>

          {/* Education */}
          <button
            className="pd-tile erp-tile erp-tile--education"
            onClick={() => navigate('/patient/dashboard/erp/education')}
          >
            <div className="pd-tile-icon">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="8" y="10" width="32" height="28" rx="3" stroke="currentColor" strokeWidth="2.5" fill="none"/>
                <line x1="16" y1="19" x2="32" y2="19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <line x1="16" y1="25" x2="32" y2="25" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <line x1="16" y1="31" x2="24" y2="31" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="24" cy="7" r="3" stroke="currentColor" strokeWidth="2" fill="none"/>
                <line x1="24" y1="10" x2="24" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <h2 className="pd-tile-label">Learn About ERP</h2>
            <p className="erp-tile-desc">
              Understand what Exposure &amp; Response Prevention is, how it works, and what to expect.
            </p>
          </button>
        </div>
      </main>
    </div>
  );
};

export default ERPWorkspace;
