import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import FearLadderBuilder from '../components/FearLadderBuilder';
import AILadderReview from '../components/AILadderReview';
import { getPatientFearLadder, updatePatientFearLadder, approveFearLadder, getLadderAIReview } from '../api/fear-ladder.api';
import './TherapistFearLadderPatientView.css';

const TherapistFearLadderPatientView = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { patientId } = useParams();
  const { logout } = useAuthStore();
  const [ladder, setLadder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState('');
  const [patientInfo, setPatientInfo] = useState({
    name: location.state?.patientName || '',
    email: location.state?.patientEmail || ''
  });
  const [aiReview, setAiReview] = useState(null);
  const [aiReviewLoading, setAiReviewLoading] = useState(false);

  useEffect(() => {
    if (patientId) {
      fetchPatientLadder();
    }
  }, [patientId]);

  const fetchPatientLadder = async () => {
    try {
      setLoading(true);
      const response = await getPatientFearLadder(patientId);
      setLadder(response.data);
      
      // Fetch AI review if ladder exists
      if (response.data?.id) {
        fetchAIReview(response.data.id);
      }
    } catch (error) {
      console.error('Error fetching patient fear ladder:', error);
      setActionMessage('Error loading patient fear ladder.');
      setTimeout(() => setActionMessage(''), 5000);
    } finally {
      setLoading(false);
    }
  };

  const fetchAIReview = async (ladderId) => {
    try {
      setAiReviewLoading(true);
      const response = await getLadderAIReview(ladderId);
      setAiReview(response.data);
    } catch (error) {
      console.log('No AI review available yet:', error);
      setAiReview(null);
    } finally {
      setAiReviewLoading(false);
    }
  };

  const handleFearLadderUpdate = async (ladderItems) => {
    try {
      const payload = {
        items: ladderItems.map((item, index) => ({
          item: item.item,
          suds: parseInt(item.suds),
          order_index: index
        }))
      };

      await updatePatientFearLadder(patientId, payload);
      setActionMessage('Fear ladder updated successfully!');
      
      // Refresh the ladder data
      await fetchPatientLadder();
      
      setTimeout(() => setActionMessage(''), 5000);
    } catch (error) {
      console.error('Error updating fear ladder:', error);
      setActionMessage('Error updating fear ladder. Please try again.');
      setTimeout(() => setActionMessage(''), 5000);
    }
  };

  const handleApproveLadder = async () => {
    if (!ladder) return;

    try {
      await approveFearLadder(patientId);
      setActionMessage('Fear ladder approved successfully!');
      
      // Refresh the ladder data
      await fetchPatientLadder();
      
      setTimeout(() => setActionMessage(''), 5000);
    } catch (error) {
      console.error('Error approving fear ladder:', error);
      setActionMessage('Error approving fear ladder. Please try again.');
      setTimeout(() => setActionMessage(''), 5000);
    }
  };

  const handleBack = () => {
    navigate('/therapist/dashboard/fear-ladder/patients');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="patient-view-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Patient Fear Ladder Review</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back to List</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="patient-view-main">
        {actionMessage && (
          <div className={`action-message ${actionMessage.includes('Error') ? 'error' : 'success'}`}>
            {actionMessage}
          </div>
        )}

        {loading ? (
          <div className="loading-message">Loading patient fear ladder...</div>
        ) : !ladder ? (
          <div className="no-data-message">
            <h3>No Fear Ladder Found</h3>
            <p>This patient hasn't submitted a fear ladder yet</p>
          </div>
        ) : (
          <div className="split-view-layout">
            {/* Left Section - Fear Ladder (70%) */}
            <div className="ladder-section">
              <div className="section-header">
                <div className="patient-info">
                  <h2>{patientInfo.name || `Patient ${ladder.patient_id}`}</h2>
                  {patientInfo.email && (
                    <p className="patient-email">{patientInfo.email}</p>
                  )}
                </div>
                <span className={`status-badge status-${ladder.status}`}>
                  {ladder.status.charAt(0).toUpperCase() + ladder.status.slice(1)}
                </span>
              </div>

              <div className="ladder-content">
                <FearLadderBuilder 
                  onSubmit={handleFearLadderUpdate}
                  existingItems={ladder.items || []}
                  submitButtonText="Update Fear Ladder"
                />

                {ladder.status !== 'approved' && (
                  <div className="therapist-actions">
                    <button 
                      className="approve-btn"
                      onClick={handleApproveLadder}
                    >
                      Approve Fear Ladder
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Right Section - AI Details (30%) */}
            <div className="ai-details-section">
              <div className="section-header">
                <h3>AI Analysis</h3>
                {aiReviewLoading && <span className="loading-indicator">Loading...</span>}
              </div>
              <div className="ai-content">
                <AILadderReview reviewData={aiReview} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default TherapistFearLadderPatientView;
