import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Intake from '../components/Intake';
import '../dashboards/PatientDashboard.css';
import './PatientAssessmentPage.css';

const PatientAssessmentPage = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [activeView, setActiveView] = useState(null); // null | 'intake'

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    if (activeView) {
      setActiveView(null);
    } else {
      navigate('/patient/dashboard/tools/ocd');
    }
  };

  return (
    <div className="pd-root">
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
              <span>{activeView === 'intake' ? 'Intake Form' : 'Assessment'}</span>
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

      <main className="pd-main">
        {!activeView && (
          <div className="pd-home">
          <div className="pd-tiles-grid pd-tiles-grid--home">
            <button className="pd-tile" onClick={() => setActiveView('intake')}>
              <span className="pd-tile-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" strokeLinecap="round" strokeLinejoin="round" />
                  <rect x="9" y="3" width="6" height="4" rx="1" ry="1" strokeLinecap="round" strokeLinejoin="round" />
                  <line x1="9" y1="12" x2="15" y2="12" strokeLinecap="round" strokeLinejoin="round" />
                  <line x1="9" y1="16" x2="13" y2="16" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <span className="pd-tile-label">Intake</span>
              <span className="pd-tile-sub">Complete your assessment form</span>
            </button>

            <button className="pd-tile" onClick={() => navigate('/patient/dashboard/tools/ocd/assessment/ocd-education')}>
              <span className="pd-tile-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <span className="pd-tile-label">Education</span>
              <span className="pd-tile-sub">Learn about OCD &amp; treatment</span>
            </button>
          </div>
          </div>
        )}

        {activeView === 'intake' && (
          <div className="assessment-inline-view">
            <Intake />
          </div>
        )}
      </main>
    </div>
  );
};

export default PatientAssessmentPage;
