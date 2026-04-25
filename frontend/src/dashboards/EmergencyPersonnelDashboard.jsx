import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './PatientDashboard.css';

const EmergencyPersonnelDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  const handleLogout = () => {
    logout();
    navigate('/select-role');
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
          </div>
          <div className="pd-header-actions">
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      <main className="pd-main">
        <div className="pd-home">
          <div className="pd-welcome">
            <p className="pd-welcome-greeting">Welcome back</p>
            <h2 className="pd-welcome-name">{user?.name || 'Emergency Personnel'}</h2>
            <p className="pd-welcome-sub">Crisis Response Dashboard</p>
          </div>

          <div className="pd-tiles-grid pd-tiles-grid--home">
            <button className="pd-tile" onClick={() => navigate('/emergency/chat')}>
              <span className="pd-tile-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <span className="pd-tile-label">Chat</span>
              <span className="pd-tile-sub">Message patients &amp; therapists</span>
            </button>

            <button className="pd-tile" onClick={() => navigate('/emergency/chat?tab=group')}>
              <span className="pd-tile-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="9" cy="7" r="4" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <span className="pd-tile-label">Group Chat</span>
              <span className="pd-tile-sub">Coordinate with your team</span>
            </button>

            <button className="pd-tile pd-tile--ai" onClick={() => navigate('/emergency/chat?tab=patients')}>
              <span className="pd-tile-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <span className="pd-tile-label">Patient Status</span>
              <span className="pd-tile-sub">Monitor active cases</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default EmergencyPersonnelDashboard;
