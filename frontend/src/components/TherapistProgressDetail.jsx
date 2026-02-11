import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPatientProgress, createOrUpdateTherapistNote, updateAIProtocol } from '../api/progress.api';
import './TherapistProgressDetail.css';

const TherapistProgressDetail = () => {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [patientData, setPatientData] = useState(null);
  const [selectedKey, setSelectedKey] = useState(null);
  const [selectedData, setSelectedData] = useState(null);
  const [note, setNote] = useState('');
  const [aiProtocol, setAiProtocol] = useState('');
 const [showAIPrompt, setShowAIPrompt] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchPatientData();
  }, [patientId]);

  const fetchPatientData = async () => {
    try {
      setLoading(true);
      const data = await getPatientProgress(patientId);
      setPatientData(data);
      setAiProtocol(data.therapist_note?.ai_protocol_instruction || '');
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch patient data:', err);
      setError('Failed to load patient data');
      setLoading(false);
    }
  };

  const handleSelectEntry = (key) => {
    setSelectedKey(key);
    setSuccess('');
    setError('');

    if (key === 'initial') {
      setSelectedData({
        title: 'Initial Symptoms',
        content: patientData.initial_condition || 'No data'
      });
      setNote(patientData.therapist_note?.week_notes?.['initial'] || '');
    } else {
      const weekNum = key.split('_')[1];
      setSelectedData({
        title: `Week ${weekNum}`,
        content: patientData.weekly_progress?.[key] || 'No data'
      });
      setNote(patientData.therapist_note?.week_notes?.[key] || '');
    }
  };

  const handleSaveNote = async () => {
    if (!selectedKey) return;

    try {
      setSaving(true);
      await createOrUpdateTherapistNote(patientId, selectedKey, note);
      setSuccess('Note saved successfully');
      
      // Refresh data
      const updatedData = await getPatientProgress(patientId);
      setPatientData(updatedData);
      
      setSaving(false);
    } catch (err) {
      console.error('Failed to save note:', err);
      setError('Failed to save note');
      setSaving(false);
    }
  };

  const handleSaveAIProtocol = async () => {
    try {
      setSaving(true);
      await updateAIProtocol(patientId, aiProtocol);
      setSuccess('AI protocol updated successfully');
      setShowAIPrompt(false);
      
      // Refresh data
      const updatedData = await getPatientProgress(patientId);
      setPatientData(updatedData);
      
      setSaving(false);
    } catch (err) {
      console.error('Failed to save AI protocol:', err);
      setError('Failed to save AI protocol');
      setSaving(false);
    }
  };

  const getProgressEntries = () => {
    if (!patientData) return [];
    
    const entries = [];
    
    // Add initial if exists
    if (patientData.initial_condition) {
      entries.push({ key: 'initial', label: 'Initial Symptoms' });
    }
    
    // Add weeks
    if (patientData.weekly_progress) {
      Object.keys(patientData.weekly_progress)
        .sort((a, b) => {
          const weekA = parseInt(a.split('_')[1]);
          const weekB = parseInt(b.split('_')[1]);
          return weekA - weekB;
        })
        .forEach(weekKey => {
          const weekNum = weekKey.split('_')[1];
          entries.push({ key: weekKey, label: `Week ${weekNum}` });
        });
    }
    
    return entries;
  };

  if (loading) {
    return (
      <div className="therapist-detail-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading patient records...</p>
        </div>
      </div>
    );
  }

  if (!patientData) {
    return (
      <div className="therapist-detail-container">
        <div className="error-message">Patient not found</div>
      </div>
    );
  }

  const entries = getProgressEntries();

  return (
    <div className="therapist-detail-container">
      {/* Header */}
      <div className="detail-header">
        <button className="back-button" onClick={() => navigate('/therapist/dashboard')}>
          <span className="back-arrow">←</span>
          <span>Back to History</span>
        </button>
        
        <div className="patient-header-info">
          <h1 className="patient-detail-title">{patientData.patient_name}</h1>
          <p className="patient-detail-subtitle">
            <span className="subtitle-label">Conditions:</span>
            <span className="subtitle-value">{patientData.conditions}</span>
          </p>
        </div>
      </div>

      {/* Main Layout */}
      <div className="detail-layout">
        {/* Left Sidebar - Entry List */}
        <div className="entry-sidebar">
          <div className="sidebar-title">Progress Records</div>
          <div className="entry-list">
            {entries.length === 0 ? (
              <div className="no-entries">No records yet</div>
            ) : (
              entries.map((entry) => (
                <div
                  key={entry.key}
                  className={`entry-item ${selectedKey === entry.key ? 'active' : ''}`}
                  onClick={() => handleSelectEntry(entry.key)}
                >
                  <span className="entry-bullet">◆</span>
                  <span className="entry-label">{entry.label}</span>
                  {patientData.therapist_note?.week_notes?.[entry.key] && (
                    <span className="has-note-indicator">📝</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Main Content */}
        <div className="entry-detail-main">
          {!selectedKey ? (
            <div className="no-selection">
              <div className="no-selection-icon">📄</div>
              <h3>Select a Record</h3>
              <p>Choose an entry from the left to view details</p>
            </div>
          ) : (
            <div className="detail-content">
              {error && <div className="alert alert-error">{error}</div>}
              {success && <div className="alert alert-success">{success}</div>}

              {/* Entry Title */}
              <div className="content-section">
                <h2 className="section-heading">{selectedData.title}</h2>
                <div className="decorative-separator"></div>
              </div>

              {/* Patient Progress */}
              <div className="content-section">
                <h3 className="subsection-title">Patient Report</h3>
                <div className="content-box">
                  <p className="content-text">{selectedData.content}</p>
                </div>
              </div>

              {/* Therapist Notes */}
              <div className="content-section">
                <h3 className="subsection-title">Your Notes</h3>
                <textarea
                  className="therapist-textarea"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add your professional notes for this entry..."
                  rows="6"
                />
                <button 
                  className="save-button"
                  onClick={handleSaveNote}
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Note'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Protocol Button - Bottom Right */}
      <button 
        className="ai-protocol-fab"
        onClick={() => setShowAIPrompt(!showAIPrompt)}
        title="AI Protocol Instructions"
      >
        <span className="fab-icon">🤖</span>
      </button>

      {/* AI Protocol Modal */}
      {showAIPrompt && (
        <div className="ai-protocol-modal">
          <div className="modal-overlay" onClick={() => setShowAIPrompt(false)}></div>
          <div className="modal-content">
            <div className="modal-header">
              <h3>AI Protocol Instructions</h3>
              <button className="modal-close" onClick={() => setShowAIPrompt(false)}>✕</button>
            </div>
            
            <div className="modal-body">
              <label className="modal-label">
                How do you want the AI to suggest protocols for {patientData.patient_name}?
              </label>
              <textarea
                className="ai-protocol-textarea"
                value={aiProtocol}
                onChange={(e) => setAiProtocol(e.target.value)}
                placeholder="e.g., Focus on gradual exposure techniques with emphasis on patient autonomy..."
                rows="8"
              />
            </div>
            
            <div className="modal-footer">
              <button className="modal-button modal-button-cancel" onClick={() => setShowAIPrompt(false)}>
                Cancel
              </button>
              <button 
                className="modal-button modal-button-save"
                onClick={handleSaveAIProtocol}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Protocol'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TherapistProgressDetail;
