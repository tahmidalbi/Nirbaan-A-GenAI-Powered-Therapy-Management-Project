import { useState, useEffect } from 'react';
import { getMyProgress, createInitialCondition, addWeeklyProgress, updateProgress } from '../api/progress.api';
import './ProgressTracker.css';

const ProgressTracker = () => {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState(null);
  const [selectedData, setSelectedData] = useState(null);
  const [editText, setEditText] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newWeekText, setNewWeekText] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    try {
      setLoading(true);
      const data = await getMyProgress();
      setProgress(data);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch progress:', err);
      setError('Failed to load progress');
      setLoading(false);
    }
  };

  const handleSelectEntry = (key) => {
    setSelectedKey(key);
    setIsEditing(false);
    setSuccess('');
    setError('');

    if (key === 'initial') {
      setSelectedData({
        title: 'Initial Symptoms',
        content: progress.initial_condition || ''
      });
      setEditText(progress.initial_condition || '');
    } else {
      const weekNum = key.split('_')[1];
      setSelectedData({
        title: `Week ${weekNum}`,
        content: progress.weekly_progress?.[key] || ''
      });
      setEditText(progress.weekly_progress?.[key] || '');
    }
  };

  const handleSave = async () => {
    try {
      if (selectedKey === 'initial') {
        await createInitialCondition(editText);
        setSuccess('Initial symptoms updated successfully');
      } else {
        const weekNum = parseInt(selectedKey.split('_')[1]);
        await updateProgress(weekNum, editText);
        setSuccess(`${selectedData.title} updated successfully`);
      }
      
      const updatedProgress = await getMyProgress();
      setProgress(updatedProgress);
      setSelectedData({ ...selectedData, content: editText });
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save:', err);
      setError('Failed to save changes');
    }
  };

  const handleAddWeeklyReport = async () => {
    if (!newWeekText.trim()) {
      setError('Please enter your progress');
      return;
    }

    try {
      setError('');
      const nextWeek = progress.current_week + 1;
      await addWeeklyProgress(nextWeek, newWeekText);
      setSuccess(`Week ${nextWeek} report added successfully!`);
      
      const updatedProgress = await getMyProgress();
      setProgress(updatedProgress);
      setNewWeekText('');
      setShowAddModal(false);
    } catch (err) {
      console.error('Failed to add weekly report:', err);
      setError('Failed to add report');
    }
  };

  const getProgressEntries = () => {
    if (!progress) return [];
    
    const entries = [];
    
    if (progress.initial_condition) {
      entries.push({ key: 'initial', label: 'Initial Symptoms' });
    }
    
    if (progress.weekly_progress) {
      Object.keys(progress.weekly_progress)
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
      <div className="progress-tracker-wrapper">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading your progress...</p>
        </div>
      </div>
    );
  }

  const entries = getProgressEntries();
  const canAddInitial = !progress.initial_condition;
  const canAddNextWeek = progress.initial_condition && progress.id !== 0;

  return (
    <div className="progress-tracker-wrapper">
      {/* Header */}
      <div className="progress-header">
        <div className="header-ornament header-ornament-left"></div>
        <h1 className="progress-title">My Progress</h1>
        <div className="header-ornament header-ornament-right"></div>
      </div>

      {/* Main Layout */}
      <div className="progress-layout">
        {/* Left Sidebar - Entry List */}
        <div className="progress-sidebar">
          <div className="sidebar-title">Progress Records</div>
          <div className="progress-entry-list">
            {entries.length === 0 ? (
              <div className="no-entries">No records yet</div>
            ) : (
              entries.map((entry) => (
                <div
                  key={entry.key}
                  className={`progress-entry-item ${selectedKey === entry.key ? 'active' : ''}`}
                  onClick={() => handleSelectEntry(entry.key)}
                >
                  <span className="entry-bullet">◆</span>
                  <span className="entry-label">{entry.label}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Main Content */}
        <div className="progress-detail-main">
          {!selectedKey ? (
            <div className="no-selection">
              <div className="no-selection-icon">📝</div>
              <h3>Select a Record</h3>
              <p>Choose an entry from the left to view or edit</p>
            </div>
          ) : (
            <div className="progress-detail-content">
              {error && <div className="alert alert-error">{error}</div>}
              {success && <div className="alert alert-success">{success}</div>}

              {/* Entry Title */}
              <div className="content-section">
                <h2 className="section-heading">{selectedData.title}</h2>
                <div className="decorative-separator"></div>
              </div>

              {/* Content Display/Edit */}
              <div className="content-section">
                {isEditing ? (
                  <>
                    <textarea
                      className="progress-textarea"
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      placeholder="Describe your progress..."
                      rows="12"
                    />
                    <div className="action-buttons">
                      <button className="save-button" onClick={handleSave}>
                        Save Changes
                      </button>
                      <button 
                        className="cancel-button" 
                        onClick={() => {
                          setIsEditing(false);
                          setEditText(selectedData.content);
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="content-display-box">
                      <p className="content-display-text">{selectedData.content}</p>
                    </div>
                    <button className="edit-button" onClick={() => setIsEditing(true)}>
                      Edit Report
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Report FAB */}
      {(canAddInitial || canAddNextWeek) && (
        <button 
          className="add-report-fab"
          onClick={() => setShowAddModal(true)}
          title={canAddInitial ? "Add Initial Symptoms" : `Add Week ${progress.current_week + 1} Report`}
        >
          <span className="fab-plus">+</span>
        </button>
      )}

      {/* Add Report Modal */}
      {showAddModal && (
        <div className="add-report-modal">
          <div className="modal-overlay" onClick={() => setShowAddModal(false)}></div>
          <div className="modal-content">
            <div className="modal-header">
              <h3>
                {canAddInitial 
                  ? 'Add Initial Symptoms' 
                  : `Add Week ${progress.current_week + 1} Report`}
              </h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>✕</button>
            </div>
            
            <div className="modal-body">
              {canAddInitial ? (
                <>
                  <label className="modal-label">
                    Describe your condition, symptoms, and everything in detail
                  </label>
                  <textarea
                    className="modal-textarea"
                    value={newWeekText}
                    onChange={(e) => setNewWeekText(e.target.value)}
                    placeholder="Describe your symptoms, feelings, and any relevant details..."
                    rows="10"
                  />
                </>
              ) : (
                <>
                  <label className="modal-label">
                    How has Week {progress.current_week + 1} been?
                  </label>
                  <textarea
                    className="modal-textarea"
                    value={newWeekText}
                    onChange={(e) => setNewWeekText(e.target.value)}
                    placeholder="Describe your progress, challenges, improvements, or any changes this week..."
                    rows="10"
                  />
                </>
              )}
            </div>
            
            <div className="modal-footer">
              <button className="modal-button modal-button-cancel" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
              <button 
                className="modal-button modal-button-save"
                onClick={canAddInitial ? async () => {
                  if (!newWeekText.trim()) {
                    setError('Please describe your condition');
                    return;
                  }
                  try {
                    await createInitialCondition(newWeekText);
                    setSuccess('Initial symptoms saved successfully!');
                    const updatedProgress = await getMyProgress();
                    setProgress(updatedProgress);
                    setNewWeekText('');
                    setShowAddModal(false);
                  } catch (err) {
                    setError('Failed to save');
                  }
                } : handleAddWeeklyReport}
              >
                Save Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProgressTracker;
