import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { listERPItems } from '../api/erp.api';
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

  return (
    <div className="divein-container">
      {/* background */}
      <div className="divein-bg">
        <div className="divein-bg-pattern" />
        <div className="divein-deco divein-deco-top" />
        <div className="divein-deco divein-deco-bottom" />
      </div>

      {/* header */}
      <header className="divein-header">
        <div className="divein-header-inner">
          <button className="divein-ghost-btn" onClick={() => navigate('/patient/dashboard/erp')}>
            ← Back
          </button>
          <h1 className="divein-logo">Dive In</h1>
          <button className="divein-ghost-btn" onClick={() => { logout(); navigate('/'); }}>
            Logout
          </button>
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

