import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './PatientDashboard.css';

const OCDTools = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard');
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
              <span>OCD Tools</span>
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
        <div className="pd-home">
        <div className="pd-tiles-grid pd-tiles-grid--home">

          <button className="pd-tile" onClick={() => navigate('/patient/dashboard/tools/ocd/assessment')}>
            <span className="pd-tile-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" strokeLinecap="round" strokeLinejoin="round" />
                <rect x="9" y="3" width="6" height="4" rx="1" ry="1" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="9" y1="12" x2="15" y2="12" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="9" y1="16" x2="13" y2="16" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className="pd-tile-label">Assessment</span>
            <span className="pd-tile-sub">Intake form &amp; education</span>
          </button>

          <button className="pd-tile" onClick={() => navigate('/patient/dashboard/fear-ladder')}>
            <span className="pd-tile-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <line x1="4" y1="6" x2="20" y2="6" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="4" y1="10" x2="20" y2="10" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="4" y1="14" x2="20" y2="14" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="4" y1="18" x2="20" y2="18" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="8" y1="4" x2="8" y2="20" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="16" y1="4" x2="16" y2="20" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className="pd-tile-label">Fear Ladder Maker</span>
            <span className="pd-tile-sub">Build your exposure hierarchy</span>
          </button>

          <button className="pd-tile" onClick={() => navigate('/patient/dashboard/erp')}>
            <span className="pd-tile-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className="pd-tile-label">ERP Workspace</span>
            <span className="pd-tile-sub">Track exposure exercises</span>
          </button>

          <button className="pd-tile" onClick={() => navigate('/patient/dashboard/imaginal-scripts')}>
            <span className="pd-tile-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="9" y1="8" x2="15" y2="8" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="9" y1="12" x2="15" y2="12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className="pd-tile-label">Imaginal Scripts</span>
            <span className="pd-tile-sub">Therapist-approved scripts</span>
          </button>

          <button className="pd-tile pd-tile--ai" onClick={() => console.log('Anti-Reassurance Chatbot clicked')}>
            <span className="pd-tile-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="12" y1="16" x2="12.01" y2="16" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" />
              </svg>
            </span>
            <span className="pd-tile-label">Anti-Reassurance Chatbot</span>
            <span className="pd-tile-sub">Support without reassurance</span>
          </button>

        </div>
        </div>
      </main>
    </div>
  );
};

export default OCDTools;
