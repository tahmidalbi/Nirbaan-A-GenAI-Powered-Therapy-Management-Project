import { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { therapistListPatientERPItems } from '../api/erp.api';
import './TherapistERPPatientList.css';
import './TherapistERPObsessionList.css';

const TherapistImaginalObsessionList = () => {
  const navigate = useNavigate();
  const { patientId } = useParams();
  const location = useLocation();
  const { logout } = useAuthStore();

  const patientName = location.state?.patientName || 'Patient';
  const patientEmail = location.state?.patientEmail || '';

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    therapistListPatientERPItems(patientId)
      .then(({ data }) => setItems(data))
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load obsessions.'))
      .finally(() => setLoading(false));
  }, [patientId]);

  const handleCreate = (item) => {
    navigate(
      `/therapist/dashboard/imaginal/patient/${patientId}/item/${item.id}`,
      {
        state: {
          patientName,
          patientEmail,
          obsession: item.obsession,
          compulsions: item.compulsions,
        },
      }
    );
  };

  return (
    <div className="terp-ol-container">
      <div className="terp-bg">
        <div className="terp-bg-pattern" />
        <div className="terp-deco terp-deco-top" />
        <div className="terp-deco terp-deco-bottom" />
      </div>

      <header className="terp-header">
        <div className="terp-header-inner">
          <button
            className="terp-ghost-btn"
            onClick={() => navigate('/therapist/dashboard/imaginal')}
          >
            ← Back
          </button>
          <div className="terp-header-title">
            <h1 className="terp-logo">Imaginal — {patientName}</h1>
            {patientEmail && <p className="terp-header-sub">{patientEmail}</p>}
          </div>
          <button className="terp-ghost-btn" onClick={() => { logout(); navigate('/login'); }}>
            Logout
          </button>
        </div>
      </header>

      <main className="terp-main">
        <p className="terp-intro">
          Select an obsession–compulsion pair to create a new imaginal exposure script or view past scripts.
        </p>

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
              <div key={item.id} className="terp-obs-card" onClick={() => handleCreate(item)}>
                <div className="terp-obs-index">{idx + 1}</div>
                <div className="terp-obs-info">
                  <h3 className="terp-obs-title">{item.obsession}</h3>
                  <div className="terp-obs-meta">
                    {item.compulsions?.length > 0 && (
                      <span className="terp-comp-badge">
                        {item.compulsions.join('; ')}
                      </span>
                    )}
                  </div>
                </div>
                <span className="terp-obs-create-label">Create ▸</span>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default TherapistImaginalObsessionList;
