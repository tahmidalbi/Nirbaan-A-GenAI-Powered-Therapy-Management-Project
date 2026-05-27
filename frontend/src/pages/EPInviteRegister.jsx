import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { validateEPInvitation, registerViaEPInvitation } from '../api/emergency-personnel.api';

const EPInviteRegister = () => {
  const { token } = useParams();
  const navigate  = useNavigate();

  const [invite, setInvite]   = useState(null);   // null = loading, false = invalid
  const [formData, setFormData] = useState({
    name: '', email: '', password: '', confirmPassword: '',
    education: '', experience: '', details: '', address: '',
  });
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    validateEPInvitation(token)
      .then((data) => {
        if (!data.valid) { setInvite(false); return; }
        setInvite(data);
        if (data.invited_email) setFormData((prev) => ({ ...prev, email: data.invited_email }));
      })
      .catch(() => setInvite(false));
  }, [token]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) { setError('Passwords do not match.'); return; }
    if (formData.password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setLoading(true);
    try {
      const { confirmPassword, ...payload } = formData;
      await registerViaEPInvitation(token, payload);
      setSuccess(true);
    } catch (err) {
      setError(err?.response?.data?.detail || err || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  // ── States ────────────────────────────────────────────────────────────────

  if (invite === null) {
    return <div style={styles.center}><p style={styles.muted}>Validating invitation…</p></div>;
  }

  if (invite === false) {
    return (
      <div style={styles.center}>
        <div style={styles.card}>
          <h2 style={styles.heading}>Invalid or Expired Link</h2>
          <p style={styles.muted}>This invitation link is no longer valid. Please ask your therapist for a new one.</p>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div style={styles.center}>
        <div style={styles.card}>
          <h2 style={{ ...styles.heading, color: '#4ecdc4' }}>Account Created</h2>
          <p style={styles.muted}>
            Your emergency personnel account has been successfully linked to your therapist's workspace.
          </p>
          <button style={styles.btn} onClick={() => navigate('/emergency-personnel/login')}>
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.center}>
      <div style={styles.card}>
        <h2 style={styles.heading}>Create Your Account</h2>
        <p style={styles.muted}>
          You have been invited by <strong style={{ color: '#4ecdc4' }}>{invite.therapist_name}</strong> as emergency support personnel.
          Fill in your details below to complete registration.
        </p>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <Field label="Full Name *">
            <input style={styles.input} name="name" value={formData.name} onChange={handleChange} required placeholder="Your full name" />
          </Field>
          <Field label="Email Address *">
            <input
              style={styles.input}
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="your@email.com"
              readOnly={!!invite.invited_email}
            />
          </Field>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <Field label="Password *" style={{ flex: 1 }}>
              <input style={styles.input} name="password" type="password" value={formData.password} onChange={handleChange} required placeholder="Min. 8 characters" />
            </Field>
            <Field label="Confirm Password *" style={{ flex: 1 }}>
              <input style={styles.input} name="confirmPassword" type="password" value={formData.confirmPassword} onChange={handleChange} required placeholder="Re-enter password" />
            </Field>
          </div>
          <Field label="Education *">
            <input style={styles.input} name="education" value={formData.education} onChange={handleChange} required placeholder="e.g., MD, Psychiatry" />
          </Field>
          <Field label="Experience *">
            <input style={styles.input} name="experience" value={formData.experience} onChange={handleChange} required placeholder="e.g., 5 years in crisis intervention" />
          </Field>
          <Field label="Additional Details">
            <textarea style={{ ...styles.input, resize: 'vertical' }} name="details" value={formData.details} onChange={handleChange} rows={3} placeholder="Certifications, specializations, etc." />
          </Field>
          <Field label="Address *">
            <textarea style={{ ...styles.input, resize: 'vertical' }} name="address" value={formData.address} onChange={handleChange} required rows={2} placeholder="Your full address" />
          </Field>
          <button style={styles.btn} type="submit" disabled={loading}>
            {loading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
};

const Field = ({ label, children, style }) => (
  <div style={{ marginBottom: '0.9rem', ...style }}>
    <label style={{ display: 'block', color: '#8aa8a8', fontSize: '0.82rem', marginBottom: '0.3rem' }}>{label}</label>
    {children}
  </div>
);

const styles = {
  center: {
    minHeight: '100vh',
    background: '#0a1f1f',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
  },
  card: {
    background: '#112929',
    border: '1px solid #1a3a3a',
    borderRadius: '12px',
    padding: '2rem',
    width: '100%',
    maxWidth: '540px',
  },
  heading: { color: '#e0e0e0', marginBottom: '0.5rem', fontSize: '1.4rem' },
  muted: { color: '#8aa8a8', fontSize: '0.9rem', marginBottom: '1.2rem' },
  error: {
    background: '#2a1515',
    border: '1px solid #5c2020',
    color: '#f87171',
    borderRadius: '6px',
    padding: '0.6rem 0.9rem',
    fontSize: '0.85rem',
    marginBottom: '1rem',
  },
  input: {
    width: '100%',
    boxSizing: 'border-box',
    background: '#0d2525',
    border: '1px solid #1a3a3a',
    borderRadius: '6px',
    color: '#e0e0e0',
    padding: '0.55rem 0.75rem',
    fontSize: '0.9rem',
    outline: 'none',
  },
  btn: {
    width: '100%',
    marginTop: '1rem',
    padding: '0.7rem',
    background: '#4ecdc4',
    color: '#0a1f1f',
    border: 'none',
    borderRadius: '6px',
    fontWeight: '700',
    fontSize: '0.95rem',
    cursor: 'pointer',
  },
};

export default EPInviteRegister;
