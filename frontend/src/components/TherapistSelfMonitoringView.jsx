import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useAuthStore } from '../store/authStore';
import { getPatients } from '../api/patient.api';
import { getPatientMonitoringDays } from '../api/self-monitoring.api';
import './PatientSelfMonitoring.css';
import '../dashboards/ConditionDashboard.css';

const TherapistSelfMonitoringView = ({ isEmbedded = false }) => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [days, setDays] = useState([]);
  const [selectedDay, setSelectedDay] = useState(null);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchPatients();
  }, []);

  useEffect(() => {
    if (selectedPatient) {
      loadPatientMonitoringData(selectedPatient.id);
    }
  }, [selectedPatient]);

  const fetchPatients = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getPatients();
      setPatients(data);
    } catch (err) {
      console.error('Failed to fetch patients:', err);
      setError('Failed to load patients');
    } finally {
      setLoading(false);
    }
  };

  const loadPatientMonitoringData = async (patientId) => {
    try {
      setError('');
      const data = await getPatientMonitoringDays(patientId);
      setDays(data);
      setSelectedDay(null);
      setEntries([]);
    } catch (err) {
      console.error('Failed to load monitoring data:', err);
      setError('Failed to load monitoring data');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/select-role');
  };

  const handleBack = () => {
    navigate('/therapist/dashboard/tools');
  };

  const handlePatientSelect = (patient) => {
    setSelectedPatient(patient);
  };

  const handleDayClick = (day) => {
    setSelectedDay(day);
    setEntries(day.entries || []);
  };

  const handleBackToPatients = () => {
    setSelectedPatient(null);
    setDays([]);
    setSelectedDay(null);
    setEntries([]);
  };

  return (
    <div className={`condition-dashboard-container ${isEmbedded ? 'embedded' : ''}`}>
      {/* Vintage background */}
      {!isEmbedded && (
        <div className="dashboard-background">
          <div className="geometric-pattern"></div>
          <div className="art-deco-line art-deco-line-top"></div>
          <div className="art-deco-line art-deco-line-bottom"></div>
        </div>
      )}

      {/* Header */}
      {!isEmbedded && (
        <header className="dashboard-header">
          <div className="header-content">
            <h1 className="logo">Patient Self Monitoring Logs</h1>
            <div className="header-actions">
              {selectedPatient ? (
                <button onClick={handleBackToPatients} className="back-btn">← Back to Patients</button>
              ) : (
                <button onClick={handleBack} className="back-btn">← Back to Tools</button>
              )}
              <button onClick={handleLogout} className="logout-btn">Logout</button>
            </div>
          </div>
        </header>
      )}

      {/* Main Content */}
      <main className="dashboard-main">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        {!selectedPatient ? (
          /* Patient Selection View */
          <div className="patient-selection">
            <h2 className="section-title">Select a Patient</h2>
            {loading ? (
              <div className="loading-state">Loading patients...</div>
            ) : patients.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">👥</div>
                <h3>No Patients Yet</h3>
                <p>Add patients to view their self-monitoring logs</p>
              </div>
            ) : (
              <div className="patients-grid">
                {patients.map(patient => (
                  <div 
                    key={patient.id}
                    className="patient-card"
                    onClick={() => handlePatientSelect(patient)}
                  >
                    <div className="patient-icon">👤</div>
                    <h3>{patient.name}</h3>
                    <p className="patient-email">{patient.email}</p>
                    <p className="patient-condition">{patient.condition || 'OCD'}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* Monitoring Data View */
          <div className="monitoring-container">
            {/* Days List */}
            <div className="days-section">
              <div className="days-header">
                <h2>Monitoring Days</h2>
                <div className="patient-info">
                  <strong>{selectedPatient.name}</strong>
                </div>
              </div>
              {days.length === 0 ? (
                <div className="no-data">
                  <p>No monitoring data yet</p>
                </div>
              ) : (
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
              )}
            </div>

            {/* Entries Section */}
            {selectedDay ? (
              <div className="entries-section">
                <div className="entries-header">
                  <h2>Day {selectedDay.day_number} Entries</h2>
                </div>

                {/* Entries Table */}
                {entries.length > 0 ? (
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
                            <td>
                              <span className={`anxiety-badge anxiety-${Math.floor(entry.anxietyLevel / 3)}`}>
                                {entry.anxietyLevel}/10
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    
                    {/* Summary Statistics */}
                    <div className="summary-stats">
                      <div className="stat-card">
                        <div className="stat-label">Total Entries</div>
                        <div className="stat-value">{entries.length}</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Avg. Time Spent</div>
                        <div className="stat-value">
                          {Math.round(entries.reduce((sum, e) => sum + (parseFloat(e.timeSpent) || 0), 0) / entries.length)} min
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Avg. Anxiety</div>
                        <div className="stat-value">
                          {(entries.reduce((sum, e) => sum + (parseFloat(e.anxietyLevel) || 0), 0) / entries.length).toFixed(1)}/10
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="no-entries">
                    <p>No entries for this day</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="no-days-message">
                <div className="empty-state">
                  <div className="empty-icon">👈</div>
                  <h3>Select a Day</h3>
                  <p>Choose a day from the list to view entries</p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

TherapistSelfMonitoringView.propTypes = {
  isEmbedded: PropTypes.bool
};

export default TherapistSelfMonitoringView;
