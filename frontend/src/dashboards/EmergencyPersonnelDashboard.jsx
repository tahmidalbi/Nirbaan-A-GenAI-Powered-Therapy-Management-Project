import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './PatientDashboard.css'; // Reuse patient dashboard styles

const EmergencyPersonnelDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="patient-dashboard-container">
      {/* Vintage background */}
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

      {/* Main content - blank */}
      <div className="dashboard-content">
        <div className="welcome-section">
          <h1>Welcome, {user?.name || 'Emergency Personnel'}</h1>
          <p className="subtitle">Crisis Response Dashboard</p>
        </div>
      </div>
    </div>
  );
};

export default EmergencyPersonnelDashboard;
