import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { loginEmergencyPersonnel, getCurrentEmergencyPersonnel } from '../api/emergency-personnel.api';
import '../auth/Signup.css'; // Reuse the same styling

const EmergencyPersonnelLogin = () => {
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
      const loginResponse = await loginEmergencyPersonnel(formData);
      
      // Store token first
      login({ 
        email: formData.email,
        role: 'emergency_personnel' 
      }, loginResponse.access_token);
      
      // Now get personnel details with the stored token
      try {
        const personnelData = await getCurrentEmergencyPersonnel();
        // Update with full data
        login({ 
          ...personnelData,
          role: 'emergency_personnel' 
        }, loginResponse.access_token);
      } catch (err) {
        console.error('Failed to fetch personnel data:', err);
      }
      
      // Redirect to emergency personnel dashboard
      navigate('/emergency-personnel/dashboard');
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
          <h1>Emergency Personnel Login</h1>
          <p>Access your crisis response dashboard</p>
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
              disabled={loading}
              placeholder="Enter your email"
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
              disabled={loading}
              placeholder="Enter your password"
            />
          </div>

          <button 
            type="submit" 
            className="signup-btn"
            disabled={loading}
          >
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div className="signup-footer">
          <button onClick={() => navigate('/')} className="link-btn">
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default EmergencyPersonnelLogin;
