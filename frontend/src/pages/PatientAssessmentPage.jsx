import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Intake from '../components/Intake';
import '../dashboards/ConditionDashboard.css';
import './PatientAssessmentPage.css';

const PatientAssessmentPage = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [activeView, setActiveView] = useState(null); // null | 'intake'

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    if (activeView) {
      setActiveView(null);
    } else {
      navigate('/patient/dashboard/tools/ocd');
    }
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
          <h1 className="logo">
            {activeView === 'intake' ? 'Intake Form' : 'Assessment'}
          </h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="dashboard-main">
        {!activeView && (
          <div className="tools-grid assessment-grid">
            <div
              className="tool-box"
              onClick={() => setActiveView('intake')}
            >
              <div className="tool-icon">📋</div>
              <h3>Intake</h3>
              <p>Complete or review your intake assessment form</p>
            </div>

            <div
              className="tool-box"
              onClick={() => navigate('/patient/dashboard/tools/ocd/assessment/ocd-education')}
            >
              <div className="tool-icon">📚</div>
              <h3>Education</h3>
              <p>Learn about your condition and treatment approach</p>
            </div>
          </div>
        )}

        {activeView === 'intake' && (
          <div className="assessment-inline-view">
            <Intake />
          </div>
        )}
      </main>
    </div>
  );
};

export default PatientAssessmentPage;
