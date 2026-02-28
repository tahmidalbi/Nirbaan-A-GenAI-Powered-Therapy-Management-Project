import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import TherapistSelfMonitoringView from '../components/TherapistSelfMonitoringView';
import FearLadderBuilder from '../components/FearLadderBuilder';
import { getAllFearLadders, getPatientFearLadder, updatePatientFearLadder, approveFearLadder } from '../api/fear-ladder.api';
import './TherapistFearLadderPage.css';

const TherapistFearLadderPage = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [activeSection, setActiveSection] = useState('ladder');
  const [allLadders, setAllLadders] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [selectedLadder, setSelectedLadder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState('');

  useEffect(() => {
    if (activeSection === 'ladder') {
      fetchAllLadders();
    }
  }, [activeSection]);

  const fetchAllLadders = async () => {
    try {
      setLoading(true);
      const response = await getAllFearLadders();
      setAllLadders(response.data || []);
    } catch (error) {
      console.error('Error fetching fear ladders:', error);
      setActionMessage('Error loading fear ladders.');
      setTimeout(() => setActionMessage(''), 5000);
    } finally {
      setLoading(false);
    }
  };

  const handlePatientSelect = async (patientId) => {
    if (!patientId) {
      setSelectedPatientId('');
      setSelectedLadder(null);
      return;
    }

    try {
      setSelectedPatientId(patientId);
      const response = await getPatientFearLadder(patientId);
      setSelectedLadder(response.data);
    } catch (error) {
      console.error('Error fetching patient fear ladder:', error);
      setActionMessage('Error loading patient fear ladder.');
      setTimeout(() => setActionMessage(''), 5000);
    }
  };

  const handleFearLadderUpdate = async (ladderItems) => {
    if (!selectedPatientId) return;

    try {
      const payload = {
        items: ladderItems.map((item, index) => ({
          item: item.item,
          suds: parseInt(item.suds),
          order_index: index
        }))
      };

      await updatePatientFearLadder(selectedPatientId, payload);
      setActionMessage('Fear ladder updated successfully!');
      
      // Refresh the ladder data
      await handlePatientSelect(selectedPatientId);
      await fetchAllLadders();
      
      setTimeout(() => setActionMessage(''), 5000);
    } catch (error) {
      console.error('Error updating fear ladder:', error);
      setActionMessage('Error updating fear ladder. Please try again.');
      setTimeout(() => setActionMessage(''), 5000);
    }
  };

  const handleApproveLadder = async () => {
    if (!selectedPatientId || !selectedLadder) return;

    try {
      await approveFearLadder(selectedPatientId);
      setActionMessage('Fear ladder approved successfully!');
      
      // Refresh the ladder data
      await handlePatientSelect(selectedPatientId);
      await fetchAllLadders();
      
      setTimeout(() => setActionMessage(''), 5000);
    } catch (error) {
      console.error('Error approving fear ladder:', error);
      setActionMessage('Error approving fear ladder. Please try again.');
      setTimeout(() => setActionMessage(''), 5000);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/therapist/dashboard/tools');
  };

  const renderContent = () => {
    switch(activeSection) {
      case 'ladder':
        return (
          <div className="section-content ladder-content">
            <h2>Patient Fear Ladders</h2>
            
            {actionMessage && (
              <div className={`action-message ${actionMessage.includes('Error') ? 'error' : 'success'}`}>
                {actionMessage}
              </div>
            )}

            <div className="info-message">
              <p>
                View, edit, and approve fear ladders submitted by your patients. You can modify
                their exposure hierarchy and provide approval when ready.
              </p>
            </div>

            {loading ? (
              <div className="loading-message">Loading patient fear ladders...</div>
            ) : allLadders.length === 0 ? (
              <div className="no-data-message">
                <p>No fear ladders have been submitted yet</p>
                <p className="subtext">Fear ladders submitted by patients will appear here</p>
              </div>
            ) : (
              <>
                <div className="patient-selection">
                  <label htmlFor="patient-select">Select Patient:</label>
                  <select 
                    id="patient-select" 
                    className="patient-dropdown"
                    value={selectedPatientId}
                    onChange={(e) => handlePatientSelect(e.target.value)}
                  >
                    <option value="">-- Select a patient --</option>
                    {allLadders.map((ladder) => (
                      <option key={ladder.patient_id} value={ladder.patient_id}>
                        {ladder.patient_name} ({ladder.patient_email}) - {ladder.status.charAt(0).toUpperCase() + ladder.status.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedLadder ? (
                  <div className="fear-ladder-display">
                    <div className="patient-info">
                      <div className="patient-details">
                        <h3>{allLadders.find(l => l.patient_id === Number(selectedPatientId))?.patient_name || `Patient ${selectedLadder.patient_id}`}</h3>
                        <p className="patient-email">{allLadders.find(l => l.patient_id === Number(selectedPatientId))?.patient_email}</p>
                      </div>
                      <span className={`status-badge status-${selectedLadder.status}`}>
                        Status: {selectedLadder.status.charAt(0).toUpperCase() + selectedLadder.status.slice(1)}
                      </span>
                    </div>

                    <FearLadderBuilder 
                      onSubmit={handleFearLadderUpdate}
                      existingItems={selectedLadder.items || []}
                      submitButtonText="Update Fear Ladder"
                    />

                    {selectedLadder.status !== 'approved' && (
                      <div className="therapist-actions">
                        <button 
                          className="approve-btn"
                          onClick={handleApproveLadder}
                        >
                          ✓ Approve Fear Ladder
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="no-data-message">
                    <p>Select a patient to view their fear ladder</p>
                  </div>
                )}
              </>
            )}
          </div>
        );
      
      case 'monitoring':
        return (
          <div className="section-content monitoring-content">
            <TherapistSelfMonitoringView isEmbedded={true} />
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="therapist-fear-ladder-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Fear Ladder Maker - Therapist View</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back to Tools</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="fear-ladder-main">
        {/* Navigation Tabs */}
        <div className="section-tabs">
          <button 
            className={`tab-btn ${activeSection === 'ladder' ? 'active' : ''}`}
            onClick={() => setActiveSection('ladder')}
          >
            <span className="tab-icon">🪜</span>
            Patient Fear Ladders
          </button>
          <button 
            className={`tab-btn ${activeSection === 'monitoring' ? 'active' : ''}`}
            onClick={() => setActiveSection('monitoring')}
          >
            <span className="tab-icon">📊</span>
            Daily Self Monitoring Log
          </button>
        </div>

        {/* Content Area */}
        <div className="content-area">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default TherapistFearLadderPage;
