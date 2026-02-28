import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './ConditionDashboard.css';

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
          <h1 className="logo">OCD Tools</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="dashboard-main">
        <div className="tools-grid">
          <div className="tool-box" onClick={() => navigate('/patient/dashboard/tools/ocd/assessment')}>
            <div className="tool-icon">🩺</div>
            <h3>Assessment</h3>
            <p>Complete your intake form and access educational resources</p>
          </div>

          <div className="tool-box" onClick={() => navigate('/patient/dashboard/fear-ladder')}>
            <div className="tool-icon">📋</div>
            <h3>Fear Ladder Maker</h3>
            <p>Create and manage your exposure hierarchy</p>
          </div>
          
          <div className="tool-box" onClick={() => console.log('ERP Workspace clicked')}>
            <div className="tool-icon">🛠️</div>
            <h3>ERP Workspace</h3>
            <p>Track your exposure and response prevention exercises</p>
          </div>
          
          <div className="tool-box" onClick={() => console.log('Imaginal Exposures clicked')}>
            <div className="tool-icon">💭</div>
            <h3>Imaginal Exposures</h3>
            <p>Practice imaginal exposure exercises</p>
          </div>
          
          <div className="tool-box" onClick={() => console.log('Anti-Reassurance Chatbot clicked')}>
            <div className="tool-icon">🤖</div>
            <h3>Anti-Reassurance Chatbot</h3>
            <p>Get support without seeking reassurance</p>
          </div>

          <div className="tool-box" onClick={() => console.log('Relapse Prevention clicked')}>
            <div className="tool-icon">🛡️</div>
            <h3>Relapse Prevention</h3>
            <p>Strategies and plans to maintain your progress</p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default OCDTools;
