import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { loginPatient, getCurrentPatient } from '../api/patient.api';
import '../auth/Signup.css'; // Reuse the same styling

const PatientLogin = () => {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
    setLoading(true);

    try {
      // Login and get token
      const loginResponse = await loginPatient(formData);
      
      // Store token first
      login({ 
        email: formData.email,
        role: 'patient' 
      }, loginResponse.access_token);
      
      // Now get patient details with the stored token
      try {
        const patientData = await getCurrentPatient();
        // Update with full data
        login({ 
          ...patientData,
          role: 'patient' 
        }, loginResponse.access_token);
      } catch (err) {
        console.error('Failed to fetch patient data:', err);
      }
      
      // Redirect to patient dashboard
      navigate('/patient/dashboard');
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-container">
      <div className="signup-card">
        <div className="signup-header">
          <h1>Patient Login</h1>
          <p>Access your personalized therapy dashboard</p>
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="signup-form">
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="your.email@example.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Enter your password"
            />
          </div>

          <button type="submit" className="signup-btn" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="signup-footer">
          <p>
            Are you a therapist?{' '}
            <span onClick={() => navigate('/login')} className="link">
              Login here
            </span>
          </p>
        </div>

        <button onClick={() => navigate('/')} className="back-btn">
          ← Back to Home
        </button>
      </div>
    </div>
  );
};

export default PatientLogin;
