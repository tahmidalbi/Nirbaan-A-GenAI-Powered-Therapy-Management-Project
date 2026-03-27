import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { therapistListERPPatients } from '../api/erp.api';
import './TherapistERPPatientList.css';

const TherapistERPPatientList = () => {
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    therapistListERPPatients()
      .then(({ data }) => setPatients(data))
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load patients.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="terp-pl-container">
      {/* Background */}
      <div className="terp-bg">
        <div className="terp-bg-pattern" />
        <div className="terp-deco terp-deco-top" />
        <div className="terp-deco terp-deco-bottom" />
      </div>

      {/* Header */}
      <header className="terp-header">
        <div className="terp-header-inner">
          <button className="terp-ghost-btn" onClick={() => navigate('/therapist/dashboard/tools')}>
            ← Back
          </button>
          <h1 className="terp-logo">ERP Workspace</h1>
          <button className="terp-ghost-btn" onClick={() => { logout(); navigate('/login'); }}>
            Logout
          </button>
        </div>
      </header>

      <main className="terp-main">
        <p className="terp-intro">Select a patient to review their ERP obsessions and sessions.</p>

        {error && <div className="terp-error">{error}</div>}

        {loading ? (
          <div className="terp-loading">Loading patients…</div>
        ) : patients.length === 0 ? (
          <div className="terp-empty">
            <h3>No ERP data yet</h3>
            <p>Patients will appear here once they start their ERP plan.</p>
          </div>
        ) : (
          <div className="terp-grid">
            {patients.map((p) => (
              <div
                key={p.patient_id}
                className="terp-card"
                onClick={() => navigate(`/therapist/dashboard/erp/patient/${p.patient_id}`, {
                  state: { patientName: p.patient_name, patientEmail: p.patient_email },
                })}
              >
                <div className="terp-card-avatar">
                  {p.patient_name.charAt(0).toUpperCase()}
                </div>
                <div className="terp-card-info">
                  <h3 className="terp-card-name">{p.patient_name}</h3>
                  <p className="terp-card-email">{p.patient_email}</p>
                </div>
                <div className="terp-card-badge">
                  {p.item_count} obsession{p.item_count !== 1 ? 's' : ''}
                </div>
                <div className="terp-card-arrow">→</div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default TherapistERPPatientList;
