import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import './ConditionDashboard.css';

const OCDPatientDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [activeSection, setActiveSection] = useState(null);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard');
  };

  return (
    <div className="condition-dashboard-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header with Navigation */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">OCD Dashboard</h1>
          <nav className="nav-menu">
            <button 
              className={`nav-btn ${activeSection === 'progress' ? 'active' : ''}`}
              onClick={() => setActiveSection('progress')}
            >
              Progress
            </button>
            <button 
              className={`nav-btn ${activeSection === 'homework' ? 'active' : ''}`}
              onClick={() => setActiveSection('homework')}
            >
              Homework
            </button>
            <button 
              className={`nav-btn ${activeSection === 'resources' ? 'active' : ''}`}
              onClick={() => setActiveSection('resources')}
            >
              Resources
            </button>
            <button 
              className={`nav-btn ${activeSection === 'tools' ? 'active' : ''}`}
              onClick={() => setActiveSection('tools')}
            >
              Tools
            </button>
            <button 
              className={`nav-btn ${activeSection === 'mindfulness' ? 'active' : ''}`}
              onClick={() => setActiveSection('mindfulness')}
            >
              Mindfulness
            </button>
          </nav>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content - Empty sections */}
      <main className="dashboard-main">
        {activeSection === 'progress' && (
          <div className="empty-section">
            {/* Empty Progress section */}
          </div>
        )}

        {activeSection === 'homework' && (
          <div className="empty-section">
            {/* Empty Homework section */}
          </div>
        )}

        {activeSection === 'resources' && (
          <div className="empty-section">
            {/* Empty Resources section */}
          </div>
        )}

        {activeSection === 'tools' && (
          <div className="empty-section">
            {/* Empty Tools section */}
          </div>
        )}

        {activeSection === 'mindfulness' && (
          <div className="empty-section">
            {/* Empty Mindfulness section */}
          </div>
        )}
      </main>
    </div>
  );
};

export default OCDPatientDashboard;
