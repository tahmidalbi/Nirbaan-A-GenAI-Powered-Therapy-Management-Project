import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { registerPatient } from '../api/patient.api';
import './AddPatient.css';

const AddPatient = ({ onPatientAdded }) => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    conditions: '',
    conditions_description: '',
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
      const patient = await registerPatient(registrationData);
      
      // Reset form
      setFormData({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        conditions: '',
        conditions_description: '',
        address: ''
      });
      
      setShowForm(false);
      if (onPatientAdded) {
        onPatientAdded(patient);
      }
    } catch (err) {
      console.error('Patient registration error:', err);
      console.error('Error details:', {
        message: err.message,
        response: err.response,
        data: err.response?.data,
        status: err.response?.status
      });
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
        <span className="plus-icon">+</span> Add New Patient
      </button>
    );
  }

  return (
    <div className="add-patient-overlay" onClick={(e) => {
      if (e.target.className === 'add-patient-overlay') setShowForm(false);
    }}>
      <div className="add-patient-modal">
        <div className="modal-header">
          <h2>Add New Patient</h2>
          <button className="close-btn" onClick={() => setShowForm(false)}>×</button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="patient-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="name">Full Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                placeholder="Patient's full name"
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
                required
                placeholder="patient@example.com"
              />
            </div>
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
                required
                placeholder="Minimum 8 characters"
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
                required
                placeholder="Re-enter password"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="conditions">Conditions *</label>
            <input
              type="text"
              id="conditions"
              name="conditions"
              value={formData.conditions}
              onChange={handleChange}
              required
              placeholder="e.g., OCD, ADHD, Anxiety"
            />
          </div>

          <div className="form-group">
            <label htmlFor="conditions_description">Conditions Description</label>
            <textarea
              id="conditions_description"
              name="conditions_description"
              value={formData.conditions_description}
              onChange={handleChange}
              rows={4}
              placeholder="Detailed description of patient's conditions, symptoms, and relevant history..."
            />
          </div>

          <div className="form-group">
            <label htmlFor="address">Address *</label>
            <textarea
              id="address"
              name="address"
              value={formData.address}
              onChange={handleChange}
              required
              rows={2}
              placeholder="Patient's residential address"
            />
          </div>

          <div className="form-actions">
            <button type="button" className="cancel-btn" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Adding Patient...' : 'Add Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddPatient;
