import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getPatientFearLadder } from '../api/fear-ladder.api';
import './TherapistFearLadderLadderList.css';

const TherapistFearLadderLadderList = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { patientId } = useParams();
  const { logout } = useAuthStore();

  const patientName = location.state?.patientName || `Patient ${patientId}`;
  const patientEmail = location.state?.patientEmail || '';

  const [ladder, setLadder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchLadder();
  }, [patientId]);

  const fetchLadder = async () => {
    try {
      setLoading(true);
      const response = await getPatientFearLadder(patientId);
      setLadder(response.data);
    } catch (err) {
      console.error('Error fetching ladder:', err);
      setError('Could not load this patient\'s ladder.');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/therapist/dashboard/fear-ladder/patients');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleOpenLadder = () => {
    navigate(`/therapist/dashboard/fear-ladder/patient/${patientId}/view`, {
      state: { patientName, patientEmail }
    });
  };

  const getCreatedDate = (ladder) => {
    if (ladder?.created_at) {
      return new Date(ladder.created_at).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    }
    return null;
  };

  const statusClass = {
    approved: 'fll-status-approved',
    pending: 'fll-status-pending',
    rejected: 'fll-status-rejected',
  };

  return (
    <div className="fll-container">
      {/* Background */}
      <div className="fll-bg">
        <div className="fll-bg-pattern"></div>
        <div className="fll-deco fll-deco-top"></div>
        <div className="fll-deco fll-deco-bottom"></div>
      </div>

      {/* Header */}
      <header className="fll-header">
        <div className="fll-header-inner">
          <div className="fll-header-left">
            <h1 className="fll-logo">Fear Ladder</h1>
            <p className="fll-logo-sub">{patientName}</p>
          </div>
          <div className="fll-header-actions">
            <button onClick={handleBack} className="fll-ghost-btn">← Back to Patients</button>
            <button onClick={handleLogout} className="fll-logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="fll-main">
        {error && <p className="fll-error">{error}</p>}

        {loading ? (
          <p className="fll-loading">Loading ladder…</p>
        ) : !ladder ? (
          <div className="fll-empty">
            <span className="fll-empty-icon">🪜</span>
            <p>No fear ladder found for this patient.</p>
            <p className="fll-empty-sub">The patient hasn't submitted a fear ladder yet.</p>
          </div>
        ) : (
          <>
            <p className="fll-section-label">Fear Ladders</p>
            <div className="fll-ladder-list">
              <button className="fll-ladder-card" onClick={handleOpenLadder}>
                <div className="fll-card-left">
                  <span className="fll-card-icon">🪜</span>
                  <div className="fll-card-info">
                    <span className="fll-card-title">Fear Exposure Ladder</span>
                    <span className="fll-card-meta">
                      {ladder.items?.length || 0} item{(ladder.items?.length || 0) !== 1 ? 's' : ''}
                      {getCreatedDate(ladder) && ` · ${getCreatedDate(ladder)}`}
                    </span>
                  </div>
                </div>
                <div className="fll-card-right">
                  <span className={`fll-status-badge ${statusClass[ladder.status] || ''}`}>
                    {ladder.status}
                  </span>
                  <span className="fll-card-arrow">→</span>
                </div>
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default TherapistFearLadderLadderList;
