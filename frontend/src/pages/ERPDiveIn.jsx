import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { listERPItems } from '../api/erp.api';
import '../dashboards/PatientDashboard.css';
import './ERPDiveIn.css';

const ERPDiveIn = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    listERPItems()
      .then(({ data }) => setItems(data))
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load items.'))
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = () => { logout(); navigate('/'); };

  return (
    <div className="divein-root">
      {/* Background */}
      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      {/* Header */}
      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>Dive In</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={() => navigate('/patient/dashboard/erp')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      <main className="divein-main">
        <p className="divein-intro">
          Select an obsession to begin your ERP session.
        </p>

        {error && <div className="divein-error">{error}</div>}

        {loading ? (
          <div className="divein-loading">Loading…</div>
        ) : items.length === 0 ? (
          <div className="divein-empty">
            No obsession items found. Add some in{' '}
            <button
              className="divein-link-btn"
              onClick={() => navigate('/patient/dashboard/erp/plan')}
            >
              Plan Your Recovery
            </button>{' '}
            first.
          </div>
        ) : (
          <ul className="divein-list">
            {items.map((item) => (
              <li key={item.id} className="divein-list-item">
                <div className="divein-item-info">
                  <span className="divein-item-obsession">{item.obsession}</span>
                  {item.suds !== null && item.suds !== undefined && (
                    <span className="divein-suds-badge">SUDS {item.suds}</span>
                  )}
                </div>
                <div className="divein-item-actions">
                  <button
                    className="divein-ai-btn"
                    onClick={() =>
                      navigate(`/patient/dashboard/erp/item/${item.id}/ai-report`, {
                        state: { obsession: item.obsession },
                      })
                    }
                  >
                    AI Report
                  </button>
                  <button
                    className="divein-start-btn"
                    onClick={() => navigate(`/patient/dashboard/erp/session/${item.id}`)}
                  >
                    Start →
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
};

export default ERPDiveIn;

