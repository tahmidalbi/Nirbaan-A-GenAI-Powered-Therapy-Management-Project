import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { registerTherapist, loginTherapist } from '../api/auth.api';
import './Signup.css';

const Signup = () => {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    license_number: '',
    specialty: '',
    address: ''
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
    
    // Validate password match
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Validate password length
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);

    try {
      // Register therapist
      const { confirmPassword, ...registrationData } = formData;
      await registerTherapist(registrationData);
      
      // Automatically login after registration
      const loginResponse = await loginTherapist({
        email: formData.email,
        password: formData.password
      });
      
      // Store auth data
      login({ 
        email: formData.email,
        name: formData.name,
        role: 'therapist' 
      }, loginResponse.access_token);
      
      // Redirect to therapist dashboard
      navigate('/therapist/dashboard');
    } catch (err) {
      console.error('Registration error:', err);
      setError(typeof err === 'string' ? err : 'Registration failed. Please check your details and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-container">
      <div className="signup-card">
        <div className="signup-header">
          <h1>Therapist Registration</h1>
          <p>Join Nirbaan to transform your practice</p>
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="signup-form">
          <div className="form-group">
            <label htmlFor="name">Full Name *</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              minLength={2}
              maxLength={100}
              placeholder="Enter your full name"
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
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="license_number">License Number *</label>
            <input
              type="text"
              id="license_number"
              name="license_number"
              value={formData.license_number}
              onChange={handleChange}
              required
              minLength={3}
              maxLength={50}
              placeholder="Enter your professional license number"
            />
          </div>

          <div className="form-group">
            <label htmlFor="specialty">Specialty *</label>
            <input
              type="text"
              id="specialty"
              name="specialty"
              value={formData.specialty}
              onChange={handleChange}
              required
              minLength={2}
              maxLength={100}
              placeholder="e.g., Clinical Psychology, CBT, ADHD"
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
              minLength={5}
              maxLength={500}
              placeholder="Enter your professional address"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password *</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              minLength={8}
              maxLength={100}
              placeholder="Create a password (min 8 characters)"
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
              placeholder="Confirm your password"
            />
          </div>

          <button type="submit" className="signup-btn" disabled={loading}>
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <div className="signup-footer">
          <p>
            Already have an account?{' '}
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

export default Signup;
