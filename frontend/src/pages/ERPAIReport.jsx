import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './ERPAIReport.css';

const ERPAIReport = () => {
  const navigate   = useNavigate();
  const { itemId } = useParams();
  const location   = useLocation();
  const { logout } = useAuthStore();

  const obsession = location.state?.obsession || 'Your obsession';

  return (
    <div className="ai-report-container">
      {/* Background */}
      <div className="ai-report-bg">
        <div className="ai-report-bg-pattern" />
        <div className="ai-report-deco ai-report-deco-top" />
        <div className="ai-report-deco ai-report-deco-bottom" />
      </div>

      {/* Header */}
      <header className="ai-report-header">
        <div className="ai-report-header-inner">
          <button
            className="ai-report-ghost-btn"
            onClick={() => navigate('/patient/dashboard/erp/dive-in')}
          >
            ← Back
          </button>
          <h1 className="ai-report-logo">AI Report</h1>
          <button
            className="ai-report-ghost-btn"
            onClick={() => { logout(); navigate('/'); }}
          >
            Logout
          </button>
        </div>
      </header>

      <main className="ai-report-main">
        {/* Obsession context */}
        <div className="ai-report-context">
          <span className="ai-report-context-label">Obsession</span>
          <p className="ai-report-context-text">{obsession}</p>
        </div>

        {/* Placeholder card */}
        <div className="ai-report-placeholder">
          <div className="ai-report-icon">🤖</div>
          <h2 className="ai-report-title">Your AI Progress Report</h2>
          <p className="ai-report-desc">
            An AI-generated summary of your ERP progress for this obsession —
            including SUDS trend analysis, session insights, and personalised
            recommendations — will appear here.
          </p>
          <div className="ai-report-badge">Coming soon</div>
        </div>
      </main>
    </div>
  );
};

export default ERPAIReport;
