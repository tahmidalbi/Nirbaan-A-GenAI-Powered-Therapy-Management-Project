import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getEmergencyPersonnelById, updateEmergencyPersonnel } from '../api/emergency-personnel.api';
import './PatientDetail.css'; // Reuse patient detail styles

const EmergencyPersonnelDetail = () => {
  const { personnelId } = useParams();
  const navigate = useNavigate();
  const [personnel, setPersonnel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPersonnel();
  }, [personnelId]);

  const fetchPersonnel = async () => {
    try {
      setLoading(true);
      const data = await getEmergencyPersonnelById(personnelId);
      setPersonnel(data);
      setFormData({
        name: data.name,
        email: data.email,
        education: data.education,
        experience: data.experience,
        details: data.details || '',
        address: data.address
      });
    } catch (err) {
      console.error('Failed to fetch emergency personnel:', err);
      setError(typeof err === 'string' ? err : 'Failed to load personnel details');
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
      const updated = await updateEmergencyPersonnel(personnelId, formData);
      setPersonnel(updated);
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to update emergency personnel:', err);
      setError(typeof err === 'string' ? err : 'Failed to update personnel');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      name: personnel.name,
      email: personnel.email,
      education: personnel.education,
      experience: personnel.experience,
      details: personnel.details || '',
      address: personnel.address
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
          <p>Loading personnel details...</p>
        </div>
      </div>
    );
  }

  if (error && !personnel) {
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

      <div className="patient-detail-content">
        <div className="detail-header">
          <button className="back-btn" onClick={() => navigate('/therapist/dashboard')}>
            ← Back to Dashboard
          </button>
          <h1 className="page-title">Emergency Personnel Profile</h1>
          {!isEditing ? (
            <button className="edit-btn" onClick={() => setIsEditing(true)}>
              ✏️ Edit Profile
            </button>
          ) : (
            <div className="edit-actions">
              <button className="cancel-btn" onClick={handleCancel} disabled={saving}>
                Cancel
              </button>
              <button className="save-btn" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : '💾 Save Changes'}
              </button>
            </div>
          )}
        </div>

        {error && <div className="error-banner">⚠️ {error}</div>}

        <div className="patient-detail-card">
          <div className="patient-header">
            <div className="patient-avatar-large">
              {personnel.name.charAt(0).toUpperCase()}
            </div>
            <div className="patient-title">
              {isEditing ? (
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  disabled={saving}
                  className="edit-input large"
                  placeholder="Full Name"
                />
              ) : (
                <h1>{personnel.name}</h1>
              )}
              {isEditing ? (
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  disabled={saving}
                  className="edit-input"
                  placeholder="Email Address"
                  style={{ marginTop: '0.5rem' }}
                />
              ) : (
                <p className="patient-email-large">{personnel.email}</p>
              )}
            </div>
          </div>

          <div className="patient-details-grid">
            <div className="detail-section">
              <h3>🎓 Education</h3>
              {isEditing ? (
                <input
                  type="text"
                  name="education"
                  value={formData.education}
                  onChange={handleChange}
                  disabled={saving}
                  className="edit-input"
                  placeholder="Educational Background"
                />
              ) : (
                <p className="conditions-text">{personnel.education}</p>
              )}
            </div>

            <div className="detail-section">
              <h3>💼 Experience</h3>
              {isEditing ? (
                <input
                  type="text"
                  name="experience"
                  value={formData.experience}
                  onChange={handleChange}
                  disabled={saving}
                  className="edit-input"
                  placeholder="Years of Experience"
                />
              ) : (
                <p className="conditions-text">{personnel.experience}</p>
              )}
            </div>

            <div className="detail-section full-width">
              <h3>📋 Additional Details</h3>
              {isEditing ? (
                <textarea
                  name="details"
                  value={formData.details}
                  onChange={handleChange}
                  rows="4"
                  disabled={saving}
                  className="edit-textarea"
                  placeholder="Certifications, skills, specializations, etc."
                />
              ) : (
                <p className="description-text">{personnel.details || 'No additional details provided'}</p>
              )}
            </div>

            <div className="detail-section full-width">
              <h3>📍 Address</h3>
              {isEditing ? (
                <textarea
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  rows="2"
                  disabled={saving}
                  className="edit-textarea"
                  placeholder="Complete Address"
                />
              ) : (
                <p className="address-text">{personnel.address}</p>
              )}
            </div>

            <div className="detail-section">
              <h3>📅 Date Added</h3>
              <p className="meta-text">{new Date(personnel.created_at).toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}</p>
            </div>

            {personnel.updated_at && personnel.updated_at !== personnel.created_at && (
              <div className="detail-section">
                <h3>🔄 Last Updated</h3>
                <p className="meta-text">{new Date(personnel.updated_at).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmergencyPersonnelDetail;
