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
      console.log('[LOGIN] Starting patient login for:', formData.email);

      // Login and get token
      const loginResponse = await loginPatient(formData);
      console.log('[LOGIN] Login response:', loginResponse);

      // Decode JWT payload to get id immediately (no extra request needed)
      const jwtPayload = JSON.parse(atob(loginResponse.access_token.split('.')[1]));
      console.log('[LOGIN] JWT payload:', jwtPayload);

      // Store token and data parsed from JWT
      console.log('[LOGIN] Storing auth data with token...');
      login({
        email: formData.email,
        id: jwtPayload.id,
        role: 'patient'
      }, loginResponse.access_token);

      console.log('[LOGIN] Auth stored, checking localStorage...');
      const stored = localStorage.getItem('auth-storage');
      console.log('[LOGIN] Stored auth-storage:', stored);

      // Fetch full patient details in background (non-blocking)
      try {
        console.log('[LOGIN] Fetching patient details...');
        const patientData = await getCurrentPatient();
        console.log('[LOGIN] Patient data received:', patientData);

        // Update with full data (keep the same token)
        login({
          ...patientData,
          role: 'patient'
        }, loginResponse.access_token);
        console.log('[LOGIN] Updated auth with full patient data');
      } catch (err) {
        console.error('[LOGIN] Failed to fetch patient data:', err);
        console.error('[LOGIN] Error details:', err.response || err);
        // id is already set from JWT so this is non-fatal
        // Continue to dashboard even if fetching details fails
      }

      // Redirect to patient dashboard
      console.log('[LOGIN] Redirecting to patient dashboard...');
      navigate('/patient/dashboard');
    } catch (err) {
      console.error('[LOGIN] Login error:', err);
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
