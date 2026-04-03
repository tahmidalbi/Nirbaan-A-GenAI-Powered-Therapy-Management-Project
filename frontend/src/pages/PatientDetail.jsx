import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPatient, updatePatient } from '../api/patient.api';
import './PatientDetail.css';

const PatientDetail = () => {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPatient();
  }, [patientId]);

  const fetchPatient = async () => {
    try {
      setLoading(true);
      const data = await getPatient(patientId);
      setPatient(data);
      setFormData({
        name: data.name,
        email: data.email,
        conditions: data.conditions,
        conditions_description: data.conditions_description || '',
        address: data.address
      });
    } catch (err) {
      console.error('Failed to fetch patient:', err);
      setError(typeof err === 'string' ? err : 'Failed to load patient details');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');

    try {
      const updated = await updatePatient(patientId, formData);
      setPatient(updated);
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to update patient:', err);
      setError(typeof err === 'string' ? err : 'Failed to update patient');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      name: patient.name,
      email: patient.email,
      conditions: patient.conditions,
      conditions_description: patient.conditions_description || '',
      address: patient.address
    });
    setIsEditing(false);
    setError('');
  };

  if (loading) {
    return (
      <div className="patient-detail-container">
        <div className="dashboard-background">
          <div className="geometric-pattern"></div>
          <div className="art-deco-lines"></div>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading patient details...</p>
        </div>
      </div>
    );
  }

  if (error && !patient) {
    return (
      <div className="patient-detail-container">
        <div className="dashboard-background">
          <div className="geometric-pattern"></div>
          <div className="art-deco-lines"></div>
        </div>
        <div className="error-state">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/therapist/dashboard')}>Back to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="patient-detail-container">
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-lines"></div>
      </div>

      <div className="detail-content">
        <div className="detail-header">
          <button className="back-btn" onClick={() => navigate('/therapist/dashboard')}>
            ← Back to Dashboard
          </button>
          {!isEditing && (
            <button className="edit-btn" onClick={() => setIsEditing(true)}>
              Edit Information
            </button>
          )}
          {isEditing && (
            <div className="edit-actions">
              <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
              <button className="save-btn" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="patient-detail-card">
          <div className="patient-header">
            <div className="patient-avatar-large">
              {patient.name.charAt(0).toUpperCase()}
            </div>
            <div className="patient-title">
              {isEditing ? (
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="edit-input large"
                />
              ) : (
                <h1>{patient.name}</h1>
              )}
              {isEditing ? (
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="edit-input"
                />
              ) : (
                <p className="patient-email-large">{patient.email}</p>
              )}
            </div>
          </div>

          <div className="patient-details-grid">
            <div className="detail-section">
              <h3>Conditions</h3>
              {isEditing ? (
                <input
                  type="text"
                  name="conditions"
                  value={formData.conditions}
                  onChange={handleChange}
                  className="edit-input"
                />
              ) : (
                <p className="conditions-text">{patient.conditions}</p>
              )}
            </div>

            <div className="detail-section full-width">
              <h3>Conditions Description</h3>
              {isEditing ? (
                <textarea
                  name="conditions_description"
                  value={formData.conditions_description}
                  onChange={handleChange}
                  rows={6}
                  className="edit-textarea"
                />
              ) : (
                <p className="description-text">
                  {patient.conditions_description || 'No description provided'}
                </p>
              )}
            </div>

            <div className="detail-section full-width">
              <h3>Address</h3>
              {isEditing ? (
                <textarea
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  rows={2}
                  className="edit-textarea"
                />
              ) : (
                <p className="address-text">{patient.address}</p>
              )}
            </div>

            <div className="detail-section">
              <h3>Patient Since</h3>
              <p className="meta-text">
                {new Date(patient.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </p>
            </div>

            <div className="detail-section">
              <h3>Last Updated</h3>
              <p className="meta-text">
                {new Date(patient.updated_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default PatientDetail;
