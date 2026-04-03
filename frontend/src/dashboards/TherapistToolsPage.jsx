import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './ConditionDashboard.css';
import './TherapistDashboard.css';

const TherapistToolsPage = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/therapist/dashboard');
  };

  return (
    <div className="condition-dashboard-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Therapist Tools</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content - Tools Grid */}
      <main className="dashboard-main">
        <div className="td-content-panel">
          <div className="td-panel-header">
            <h2>Clinical Tools</h2>
          </div>
          <div className="td-tools-grid">
            <button className="td-tool-card" onClick={() => navigate('/therapist/dashboard/fear-ladder/patients')}>
              <span className="td-tool-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <line x1="8" y1="6" x2="21" y2="6" strokeLinecap="round"/><line x1="8" y1="12" x2="21" y2="12" strokeLinecap="round"/><line x1="8" y1="18" x2="21" y2="18" strokeLinecap="round"/>
                  <line x1="3" y1="6" x2="3.01" y2="6" strokeLinecap="round"/><line x1="3" y1="12" x2="3.01" y2="12" strokeLinecap="round"/><line x1="3" y1="18" x2="3.01" y2="18" strokeLinecap="round"/>
                </svg>
              </span>
              <h3>Fear Ladder Maker</h3>
              <p>Create and manage exposure hierarchies for your patients</p>
              <span className="td-tool-arrow">→</span>
            </button>

            <button className="td-tool-card" onClick={() => navigate('/therapist/dashboard/erp')}>
              <span className="td-tool-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </span>
              <h3>ERP Workspace</h3>
              <p>Monitor and guide patient exposure exercises</p>
              <span className="td-tool-arrow">→</span>
            </button>

            <button className="td-tool-card" onClick={() => navigate('/therapist/dashboard/imaginal')}>
              <span className="td-tool-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" strokeLinecap="round"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" strokeLinecap="round"/><line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round"/>
                </svg>
              </span>
              <h3>Imaginal Exposures</h3>
              <p>Design and track imaginal exposure protocols</p>
              <span className="td-tool-arrow">→</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TherapistToolsPage;
