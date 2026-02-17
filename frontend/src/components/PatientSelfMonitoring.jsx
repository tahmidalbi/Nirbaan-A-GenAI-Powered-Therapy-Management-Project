import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { 
  createMonitoringDay, 
  getMyMonitoringDays, 
  createMonitoringEntry, 
  deleteMonitoringEntry 
} from '../api/self-monitoring.api';
import './PatientSelfMonitoring.css';

const PatientSelfMonitoring = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [days, setDays] = useState([]);
  const [selectedDay, setSelectedDay] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentEntry, setCurrentEntry] = useState({
    date: '',
    time: '',
    event: '',
    ritual: '',
    timeSpent: '',
    anxietyLevel: ''
  });

  useEffect(() => {
    fetchDays();
  }, []);

  const fetchDays = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getMyMonitoringDays();
      setDays(data);
    } catch (err) {
      console.error('Failed to fetch monitoring days:', err);
      setError('Failed to load monitoring days');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard/tools/ocd');
  };

  const handleAddDay = async () => {
    try {
      setError('');
      const newDayNumber = days.length + 1;
      const newDay = await createMonitoringDay(newDayNumber);
      
      setDays([...days, newDay]);
      setSelectedDay(newDay);
      setEntries([]);
      setShowForm(true);
    } catch (err) {
      console.error('Failed to create monitoring day:', err);
      setError('Failed to create monitoring day');
    }
  };

  const handleDayClick = (day) => {
    setSelectedDay(day);
    setEntries(day.entries || []);
    setShowForm(false);
  };

  const handleAddEntry = () => {
    setShowForm(true);
    setCurrentEntry({
      date: new Date().toISOString().split('T')[0],
      time: new Date().toTimeString().split(' ')[0].substring(0, 5),
      event: '',
      ritual: '',
      timeSpent: '',
      anxietyLevel: ''
    });
  };

  const handleInputChange = (field, value) => {
    setCurrentEntry(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSaveEntry = async () => {
    if (!selectedDay) return;

    try {
      setError('');
      const newEntry = await createMonitoringEntry(selectedDay.id, currentEntry);

      const updatedEntries = [...entries, newEntry];
      setEntries(updatedEntries);

      // Update the day's entries in local state
      const updatedDays = days.map(day => 
        day.id === selectedDay.id 
          ? { ...day, entries: updatedEntries }
          : day
      );
      setDays(updatedDays);

      // Reset form
      setCurrentEntry({
        date: new Date().toISOString().split('T')[0],
        time: new Date().toTimeString().split(' ')[0].substring(0, 5),
        event: '',
        ritual: '',
        timeSpent: '',
        anxietyLevel: ''
      });
      setShowForm(false);
    } catch (err) {
      console.error('Failed to save entry:', err);
      setError('Failed to save entry');
    }
  };

  const handleCancelEntry = () => {
    setShowForm(false);
    setCurrentEntry({
      date: '',
      time: '',
      event: '',
      ritual: '',
      timeSpent: '',
      anxietyLevel: ''
    });
  };

  const handleDeleteEntry = async (entryId) => {
    if (!selectedDay) return;
    
    try {
      setError('');
      await deleteMonitoringEntry(entryId);
      
      const updatedEntries = entries.filter(entry => entry.id !== entryId);
      setEntries(updatedEntries);

      const updatedDays = days.map(day => 
        day.id === selectedDay.id 
          ? { ...day, entries: updatedEntries }
          : day
      );
      setDays(updatedDays);
    } catch (err) {
      console.error('Failed to delete entry:', err);
      setError('Failed to delete entry');
    }
  };

  return (
    <div className="condition-dashboard-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Daily Self Monitoring Log</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="dashboard-main">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        {loading ? (
          <div className="loading-state">Loading your monitoring data...</div>
        ) : (
          <div className="monitoring-container">
          {/* Days List */}
          <div className="days-section">
            <div className="days-header">
              <h2>Monitoring Days</h2>
              <button className="add-day-btn" onClick={handleAddDay}>
                <span className="plus-icon">+</span>
                Add Day {days.length + 1} Self Monitoring
              </button>
            </div>
            <div className="days-list">
              {days.map(day => (
                <div 
                  key={day.id}
                  className={`day-item ${selectedDay?.id === day.id ? 'active' : ''}`}
                  onClick={() => handleDayClick(day)}
                >
                  <span className="day-number">Day {day.day_number}</span>
                  <span className="entry-count">{day.entries?.length || 0} entries</span>
                </div>
              ))}
            </div>
          </div>

          {/* Entries Section */}
          {selectedDay && (
            <div className="entries-section">
              <div className="entries-header">
                <h2>Day {selectedDay.day_number} Entries</h2>
                {!showForm && (
                  <button className="add-entry-btn" onClick={handleAddEntry}>
                    <span className="plus-icon">+</span>
                    Add Entry
                  </button>
                )}
              </div>

              {/* Entry Form */}
              {showForm && (
                <div className="entry-form">
                  <div className="form-grid">
                    <div className="form-field">
                      <label>Date</label>
                      <input 
                        type="date" 
                        value={currentEntry.date}
                        onChange={(e) => handleInputChange('date', e.target.value)}
                      />
                    </div>
                    <div className="form-field">
                      <label>Time</label>
                      <input 
                        type="time" 
                        value={currentEntry.time}
                        onChange={(e) => handleInputChange('time', e.target.value)}
                      />
                    </div>
                    <div className="form-field">
                      <label>Event</label>
                      <textarea 
                        value={currentEntry.event}
                        onChange={(e) => handleInputChange('event', e.target.value)}
                        placeholder="Describe the event..."
                      />
                    </div>
                    <div className="form-field">
                      <label>Ritual</label>
                      <textarea 
                        value={currentEntry.ritual}
                        onChange={(e) => handleInputChange('ritual', e.target.value)}
                        placeholder="Describe the ritual..."
                      />
                    </div>
                    <div className="form-field">
                      <label>Time Spent (minutes)</label>
                      <input 
                        type="number" 
                        value={currentEntry.timeSpent}
                        onChange={(e) => handleInputChange('timeSpent', e.target.value)}
                        placeholder="0"
                      />
                    </div>
                    <div className="form-field">
                      <label>Anxiety Level (0-10)</label>
                      <input 
                        type="number" 
                        min="0" 
                        max="10"
                        value={currentEntry.anxietyLevel}
                        onChange={(e) => handleInputChange('anxietyLevel', e.target.value)}
                        placeholder="0"
                      />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="save-btn" onClick={handleSaveEntry}>Save Entry</button>
                    <button className="cancel-btn" onClick={handleCancelEntry}>Cancel</button>
                  </div>
                </div>
              )}

              {/* Entries Table */}
              {entries.length > 0 && (
                <div className="entries-table-container">
                  <table className="entries-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Event</th>
                        <th>Ritual</th>
                        <th>Time Spent</th>
                        <th>Anxiety Level</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entries.map(entry => (
                        <tr key={entry.id}>
                          <td>{entry.date}</td>
                          <td>{entry.time}</td>
                          <td>{entry.event}</td>
                          <td>{entry.ritual}</td>
                          <td>{entry.timeSpent} min</td>
                          <td>{entry.anxietyLevel}/10</td>
                          <td>
                            <button 
                              className="delete-btn"
                              onClick={() => handleDeleteEntry(entry.id)}
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {entries.length === 0 && !showForm && (
                <div className="no-entries">
                  <p>No entries yet. Click "Add Entry" to create your first entry.</p>
                </div>
              )}
            </div>
          )}

          {!selectedDay && days.length === 0 && (
            <div className="no-days-message">
              <div className="empty-state">
                <div className="empty-icon">📊</div>
                <h3>Start Your Self-Monitoring Journey</h3>
                <p>Click the button above to add your first day of self-monitoring</p>
              </div>
            </div>
          )}

          {!selectedDay && days.length > 0 && (
            <div className="no-days-message">
              <div className="empty-state">
                <div className="empty-icon">👈</div>
                <h3>Select a Day</h3>
                <p>Choose a day from the list to view or add entries</p>
              </div>
            </div>
          )}
        </div>
        )}
      </main>
    </div>
  );
};

export default PatientSelfMonitoring;
