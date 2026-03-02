import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './ERPWorkspace.css';

const ERPWorkspace = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="erp-workspace-container">
      {/* Background */}
      <div className="erp-background">
        <div className="erp-geometric-pattern" />
        <div className="erp-deco-line erp-deco-line-top" />
        <div className="erp-deco-line erp-deco-line-bottom" />
      </div>

      {/* Header */}
      <header className="erp-header">
        <div className="erp-header-content">
          <button className="erp-back-btn" onClick={() => navigate('/patient/dashboard/tools/ocd')}>
            ← Back
          </button>
          <h1 className="erp-logo">ERP Workspace</h1>
          <button className="erp-logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="erp-main">
        <div className="erp-subtitle">
          Exposure &amp; Response Prevention — choose how to proceed
        </div>

        <div className="erp-boxes-grid">
          {/* Plan your recovery */}
          <div
            className="erp-box"
            onClick={() => navigate('/patient/dashboard/erp/plan')}
          >
            <div className="erp-box-icon">📋</div>
            <h2 className="erp-box-title">Plan Your Recovery</h2>
            <p className="erp-box-description">
              Map out your obsessions, compulsions, and prescribed exercises to build
              a personalised ERP plan.
            </p>
          </div>

          {/* Dive in */}
          <div
            className="erp-box"
            onClick={() => navigate('/patient/dashboard/erp/dive-in')}
          >
            <div className="erp-box-icon">🚀</div>
            <h2 className="erp-box-title">Dive In</h2>
            <p className="erp-box-description">
              Start your exposure exercises and track your progress session by session.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ERPWorkspace;
