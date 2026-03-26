import { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { therapistListPatientERPItems } from '../api/erp.api';
import './TherapistERPPatientList.css'; // shared base styles
import './TherapistERPObsessionList.css';

const TherapistERPObsessionList = () => {
  const navigate = useNavigate();
  const { patientId } = useParams();
  const location = useLocation();
  const { logout } = useAuthStore();

  const patientName  = location.state?.patientName  || 'Patient';
  const patientEmail = location.state?.patientEmail || '';

  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    therapistListPatientERPItems(patientId)
      .then(({ data }) => setItems(data))
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load obsessions.'))
      .finally(() => setLoading(false));
  }, [patientId]);

  const handleItemClick = (item) => {
    navigate(`/therapist/dashboard/erp/patient/${patientId}/item/${item.id}`, {
      state: { patientName, patientEmail, obsession: item.obsession },
    });
  };

  return (
    <div className="terp-ol-container">
      {/* Background */}
      <div className="terp-bg">
        <div className="terp-bg-pattern" />
        <div className="terp-deco terp-deco-top" />
        <div className="terp-deco terp-deco-bottom" />
      </div>

      {/* Header */}
      <header className="terp-header">
        <div className="terp-header-inner">
          <button
            className="terp-ghost-btn"
            onClick={() => navigate('/therapist/dashboard/erp')}
          >
            ← Back
          </button>
          <div className="terp-header-title">
            <h1 className="terp-logo">ERP — {patientName}</h1>
            {patientEmail && <p className="terp-header-sub">{patientEmail}</p>}
          </div>
          <button className="terp-ghost-btn" onClick={() => { logout(); navigate('/login'); }}>
            Logout
          </button>
        </div>
      </header>

      <main className="terp-main">
        <p className="terp-intro">Select an obsession to view the full ERP detail.</p>

        {error && <div className="terp-error">{error}</div>}

        {loading ? (
          <div className="terp-loading">Loading obsessions…</div>
        ) : items.length === 0 ? (
          <div className="terp-empty">
            <h3>No ERP items yet</h3>
            <p>{patientName} hasn't added any obsessions to their ERP plan.</p>
          </div>
        ) : (
          <div className="terp-obs-list">
            {items.map((item, idx) => (
              <div
                key={item.id}
                className="terp-obs-card"
                onClick={() => handleItemClick(item)}
              >
                <div className="terp-obs-index">{idx + 1}</div>
                <div className="terp-obs-info">
                  <h3 className="terp-obs-title">{item.obsession}</h3>
                  <div className="terp-obs-meta">
                    {item.suds !== null && item.suds !== undefined && (
                      <span className="terp-suds-badge">SUDS {item.suds}</span>
                    )}
                    {item.compulsions?.length > 0 && (
                      <span className="terp-comp-badge">
                        {item.compulsions.length} compulsion{item.compulsions.length !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
                <div className="terp-obs-arrow">→</div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default TherapistERPObsessionList;
