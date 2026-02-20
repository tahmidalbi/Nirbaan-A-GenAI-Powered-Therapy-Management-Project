import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './PatientFearLadderHub.css';

const PatientFearLadderHub = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard/tools/ocd');
  };

  const handleNavigate = (path) => {
    navigate(path);
  };

  return (
    <div className="fear-ladder-hub-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Fear Ladder Maker</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back to OCD Tools</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="fear-ladder-hub-main">
        <div className="hub-title">
          <h2>Select a Section</h2>
          <p>Choose from the options below to begin</p>
        </div>

        <div className="option-cards">
          <div 
            className="option-card education-card"
            onClick={() => handleNavigate('/patient/dashboard/fear-ladder/education')}
          >
            <div className="card-icon-wrapper">
              <div className="card-icon">📖</div>
            </div>
            <h3>Education</h3>
            <p>Learn about fear ladders and SUDS ratings</p>
            <div className="card-arrow">→</div>
          </div>

          <div 
            className="option-card builder-card"
            onClick={() => handleNavigate('/patient/dashboard/fear-ladder/builder')}
          >
            <div className="card-icon-wrapper">
              <div className="card-icon">⚒</div>
            </div>
            <h3>Build Your Fear Ladder</h3>
            <p>Create and manage your exposure hierarchy</p>
            <div className="card-arrow">→</div>
          </div>

          <div 
            className="option-card monitoring-card"
            onClick={() => handleNavigate('/patient/dashboard/fear-ladder/monitoring')}
          >
            <div className="card-icon-wrapper">
              <div className="card-icon">📋</div>
            </div>
            <h3>Self Monitoring Log</h3>
            <p>Track your daily progress and symptoms</p>
            <div className="card-arrow">→</div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PatientFearLadderHub;
