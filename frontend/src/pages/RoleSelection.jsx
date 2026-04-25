import { useNavigate } from 'react-router-dom';
import './RoleSelection.css';

const RoleSelection = () => {
  const navigate = useNavigate();

  return (
    <div className="role-selection-container">
      <div className="role-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      <div className="role-content">
        <div className="role-header">
          <h1 className="logo-text">Nirbaan</h1>
          <p className="tagline">Select Your Role</p>
        </div>

        <div className="role-cards">
          <div className="role-card" onClick={() => navigate('/login')}>
            <h2>Login as Therapist</h2>
            <p>Access your practice dashboard and manage patient care</p>
            <button className="role-btn">Continue as Therapist</button>
          </div>

          <div className="role-card" onClick={() => navigate('/patient/login')}>
            <h2>Login as Patient</h2>
            <p>Access your personalized therapy and wellness dashboard</p>
            <button className="role-btn">Continue as Patient</button>
          </div>

          <div className="role-card" onClick={() => navigate('/emergency-personnel/login')}>
            <h2>Login as Emergency Personnel</h2>
            <p>Access crisis response and emergency management tools</p>
            <button className="role-btn">Continue as Personnel</button>
          </div>
        </div>

        <div className="back-link">
          <button onClick={() => navigate('/')} className="back-btn">
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default RoleSelection;
