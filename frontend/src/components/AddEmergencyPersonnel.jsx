import { useState } from 'react';
import { registerEmergencyPersonnel } from '../api/emergency-personnel.api';
import './AddPatient.css'; // Reuse the same styles

const AddEmergencyPersonnel = ({ onPersonnelAdded }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    education: '',
    experience: '',
    details: '',
    address: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);

    try {
      const { confirmPassword, ...registrationData } = formData;
      const personnel = await registerEmergencyPersonnel(registrationData);
      
      // Reset form
      setFormData({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        education: '',
        experience: '',
        details: '',
        address: ''
      });
      
      setShowForm(false);
      if (onPersonnelAdded) {
        onPersonnelAdded(personnel);
      }
    } catch (err) {
      console.error('Emergency personnel registration error:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Registration failed. Please check your details and try again.';
      setError(errorMsg);
      alert(`Registration Error: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  if (!showForm) {
    return (
      <button className="add-patient-btn" onClick={() => setShowForm(true)}>
        <span className="plus-icon">+</span> Add Emergency Personnel
      </button>
    );
  }

  return (
    <div className="add-patient-overlay" onClick={(e) => {
      if (e.target.className === 'add-patient-overlay') setShowForm(false);
    }}>
      <div className="add-patient-modal">
        <div className="modal-header">
          <h2>Add Emergency Personnel</h2>
          <button className="close-btn" onClick={() => setShowForm(false)}>×</button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="patient-form">
          <div className="form-group">
            <label htmlFor="name">Full Name *</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Enter full name"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email Address *</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter email address"
              required
              disabled={loading}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="password">Password *</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Minimum 8 characters"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password *</label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Re-enter password"
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="education">Education *</label>
            <input
              type="text"
              id="education"
              name="education"
              value={formData.education}
              onChange={handleChange}
              placeholder="e.g., MD, Psychiatry"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="experience">Experience *</label>
            <input
              type="text"
              id="experience"
              name="experience"
              value={formData.experience}
              onChange={handleChange}
              placeholder="e.g., 5 years in crisis intervention"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="details">Additional Details</label>
            <textarea
              id="details"
              name="details"
              value={formData.details}
              onChange={handleChange}
              placeholder="Certifications, specializations, etc."
              rows="3"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="address">Address *</label>
            <textarea
              id="address"
              name="address"
              value={formData.address}
              onChange={handleChange}
              placeholder="Enter full address"
              rows="2"
              required
              disabled={loading}
            />
          </div>

          <div className="form-actions">
            <button 
              type="button" 
              className="btn-cancel" 
              onClick={() => setShowForm(false)}
              disabled={loading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-submit"
              disabled={loading}
            >
              {loading ? 'Adding...' : 'Add Personnel'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddEmergencyPersonnel;
