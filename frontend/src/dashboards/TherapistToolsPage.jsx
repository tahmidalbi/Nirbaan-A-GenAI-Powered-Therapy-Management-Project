import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './ConditionDashboard.css';

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
        <div className="tools-grid">
          <div className="tool-box" onClick={() => console.log('Fear Ladder Maker clicked')}>
            <div className="tool-icon">📋</div>
            <h3>Fear Ladder Maker</h3>
            <p>Create and manage exposure hierarchies for your patients</p>
          </div>
          
          <div className="tool-box" onClick={() => console.log('ERP Workspace clicked')}>
            <div className="tool-icon">🛠️</div>
            <h3>ERP Workspace</h3>
            <p>Monitor and guide patient exposure exercises</p>
          </div>
          
          <div className="tool-box" onClick={() => console.log('Imaginal Exposures clicked')}>
            <div className="tool-icon">💭</div>
            <h3>Imaginal Exposures</h3>
            <p>Design and track imaginal exposure protocols</p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TherapistToolsPage;
