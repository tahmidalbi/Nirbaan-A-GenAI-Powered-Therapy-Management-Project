import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import './PatientDashboard.css';

const PatientDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [activeSection, setActiveSection] = useState(null);
  const [showToolsDropdown, setShowToolsDropdown] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleToolsClick = () => {
    setShowToolsDropdown(!showToolsDropdown);
  };

  const handleOCDToolsClick = () => {
    navigate('/patient/dashboard/tools/ocd');
  };

  const handleADHDToolsClick = () => {
    navigate('/patient/dashboard/tools/adhd');
  };

  return (
    <div className="patient-dashboard-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header with Navigation */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Nirbaan</h1>
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
            <div className="nav-btn-wrapper">
              <button 
                className="nav-btn"
                onClick={handleToolsClick}
              >
                Tools ▾
              </button>
              {showToolsDropdown && (
                <div className="tools-dropdown">
                  <button onClick={handleOCDToolsClick}>OCD</button>
                  <button onClick={handleADHDToolsClick}>ADHD</button>
                </div>
              )}
            </div>
            <button 
              className={`nav-btn ${activeSection === 'mindfulness' ? 'active' : ''}`}
              onClick={() => setActiveSection('mindfulness')}
            >
              Mindfulness
            </button>
            <button 
              className={`nav-btn ${activeSection === 'sessions' ? 'active' : ''}`}
              onClick={() => setActiveSection('sessions')}
            >
              Sessions
            </button>
            <button 
              className={`nav-btn ${activeSection === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveSection('chat')}
            >
              Chat
            </button>
          </nav>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      {/* Video Call Button - Only on landing page */}
      {!activeSection && (
        <button className="video-call-btn" title="Start Video Call">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
          </svg>
        </button>
      )}

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

        {activeSection === 'mindfulness' && (
          <div className="empty-section">
            {/* Empty Mindfulness section */}
          </div>
        )}

        {activeSection === 'sessions' && (
          <div className="empty-section">
            {/* Empty Sessions section */}
          </div>
        )}

        {activeSection === 'chat' && (
          <div className="empty-section">
            {/* Empty Chat section */}
          </div>
        )}
      </main>
    </div>
  );
};

export default PatientDashboard;