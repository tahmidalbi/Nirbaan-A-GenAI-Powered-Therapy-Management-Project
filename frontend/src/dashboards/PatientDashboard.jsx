import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './PatientDashboard.css';

const PatientDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="patient-dashboard-container">
      {/* Vintage background similar to therapist dashboard */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-lines"></div>
      </div>

      {/* Header with logout */}
      <header className="dashboard-header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-text">Nirbaan</span>
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="dashboard-content">
        <div className="welcome-section">
          <h1>Welcome, {user?.name || 'Patient'}</h1>
          <p className="subtitle">Your personalized therapy dashboard</p>
        </div>

        <div className="content-card">
          <div className="coming-soon">
            <div className="icon">🌿</div>
            <h2>Your Dashboard is Being Prepared</h2>
            <p>We\'re working on creating an amazing experience for you. Soon you\'ll be able to:</p>
            <ul className="features-list">
              <li>View your therapy sessions</li>
              <li>Access personalized resources</li>
              <li>Track your progress</li>
              <li>Communicate with your therapist</li>
              <li>Complete assigned exercises</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PatientDashboard;