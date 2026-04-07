import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import FearLadderBuilder from '../components/FearLadderBuilder';
import { getMyFearLadder, createFearLadder, updateMyFearLadder, submitLadderForAIReview } from '../api/fear-ladder.api';
import '../dashboards/PatientDashboard.css';
import './PatientFearLadderPage.css';

const PatientFearLadderPage = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [existingLadder, setExistingLadder] = useState(null);
  const [ladderStatus, setLadderStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitMessage, setSubmitMessage] = useState('');
  const [aiReviewSubmitting, setAiReviewSubmitting] = useState(false);

  useEffect(() => {
    fetchExistingLadder();
  }, []);

  const fetchExistingLadder = async () => {
    try {
      setLoading(true);
      const response = await getMyFearLadder();
      if (response.data) {
        setExistingLadder(response.data);
        setLadderStatus(response.data.status);
      }
    } catch (error) {
      // No existing ladder, that's okay
      console.log('No existing ladder found');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard/fear-ladder');
  };

  const handleSubmitForAIReview = async () => {
    if (!existingLadder?.id) {
      setSubmitMessage('Please submit your fear ladder first before requesting AI analysis.');
      setTimeout(() => setSubmitMessage(''), 5000);
      return;
    }

    try {
      setAiReviewSubmitting(true);
      await submitLadderForAIReview(existingLadder.id);
      setSubmitMessage('✨ AI analysis requested! Your therapist will see the results once complete.');
      setTimeout(() => setSubmitMessage(''), 5000);
    } catch (error) {
      console.error('Error submitting for AI review:', error);
      if (error.includes('already in progress')) {
        setSubmitMessage('AI analysis is already in progress for this ladder.');
      } else {
        setSubmitMessage('Error requesting AI analysis. Please try again.');
      }
      setTimeout(() => setSubmitMessage(''), 5000);
    } finally {
      setAiReviewSubmitting(false);
    }
  };

  const handleFearLadderSubmit = async (ladderItems) => {
    try {
      const payload = {
        items: ladderItems.map((item, index) => ({
          item: item.item,
          suds: parseInt(item.suds),
          order_index: index
        }))
      };

      if (existingLadder) {
        // Update existing ladder (or create new if approved)
        await updateMyFearLadder(payload);
        if (ladderStatus === 'approved') {
          setSubmitMessage('New fear ladder submitted successfully! Your previous approved ladder has been saved. Status: Pending therapist approval.');
        } else {
          setSubmitMessage('Fear ladder updated successfully! Status: Pending therapist approval.');
        }
      } else {
        // Create new ladder
        const response = await createFearLadder(payload);
        setExistingLadder(response.data);
        setLadderStatus('pending');
        setSubmitMessage('Fear ladder submitted successfully! Status: Pending therapist approval.');
      }

      // Refresh the ladder data
      await fetchExistingLadder();
      
      // Clear message after 5 seconds
      setTimeout(() => setSubmitMessage(''), 5000);
    } catch (error) {
      console.error('Error submitting fear ladder:', error);
      setSubmitMessage('Error submitting fear ladder. Please try again.');
      setTimeout(() => setSubmitMessage(''), 5000);
    }
  };

  return (
    <div className="fear-ladder-page-container">
      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>Build Your Fear Ladder</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={handleBack}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="fear-ladder-main">
        <div className="builder-content-wrapper">
          {submitMessage && (
            <div className={`submit-message ${submitMessage.includes('Error') ? 'error' : 'success'}`}>
              {submitMessage}
            </div>
          )}
          
          {ladderStatus && (
            <div className={`status-badge status-${ladderStatus}`}>
              Status: {ladderStatus.charAt(0).toUpperCase() + ladderStatus.slice(1)}
            </div>
          )}
          
          {loading ? (
            <div className="loading-message">Loading your fear ladder...</div>
          ) : (
            <>
              <FearLadderBuilder 
                onSubmit={handleFearLadderSubmit}
                existingItems={existingLadder ? existingLadder.items : []}
                readOnly={false}
                submitButtonText={
                  ladderStatus === 'approved' 
                    ? 'Submit New Fear Ladder'
                    : existingLadder 
                      ? 'Update & Resubmit'
                      : 'Submit to Therapist'
                }
              />
              
              {existingLadder && (
                <div className="ai-review-section">
                  <div className="ai-review-info">
                    <h3>🤖 AI-Powered Analysis</h3>
                    <p>
                      Request an AI analysis of your fear ladder. The AI will review your intake 
                      responses and recent daily logs to identify any patterns that might be missing 
                      from your ladder. Your therapist will see these suggestions.
                    </p>
                  </div>
                  <button 
                    className="ai-review-btn"
                    onClick={handleSubmitForAIReview}
                    disabled={aiReviewSubmitting}
                  >
                    {aiReviewSubmitting ? 'Submitting...' : '✨ Request AI Analysis'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default PatientFearLadderPage;
