import { useState } from 'react';
import { registerPatient, createPatientInvitation, sendInviteEmail } from '../api/patient.api';
import './AddPatient.css';

const EMPTY_FORM = {
  name: '', email: '', password: '', confirmPassword: '',
  conditions: '', conditions_description: '', address: '',
};

const AddPatient = ({ onPatientAdded }) => {
  const [showForm, setShowForm]   = useState(false);
  const [activeTab, setActiveTab] = useState('direct');

  // Direct tab state
  const [formData, setFormData]   = useState(EMPTY_FORM);
  const [error, setError]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [createdCreds, setCreatedCreds] = useState(null);
  const [credsCopied, setCredsCopied]   = useState(false);

  // Invite tab state
  const [inviteEmail, setInviteEmail]   = useState('');
  const [inviteResult, setInviteResult] = useState(null);
  const [inviteError, setInviteError]   = useState('');
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteCopied, setInviteCopied]   = useState(false);

  // Email sending state (shown after invite link is generated)
  const [sendEmail, setSendEmail]       = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailSent, setEmailSent]       = useState(false);
  const [emailError, setEmailError]     = useState('');

  // ── helpers ──────────────────────────────────────────────────────────────

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleClose = () => {
    setShowForm(false);
    setActiveTab('direct');
    setFormData(EMPTY_FORM);
    setError('');
    setCreatedCreds(null);
    setCredsCopied(false);
    setInviteEmail('');
    setInviteResult(null);
    setInviteError('');
    setSendEmail('');
    setEmailSent(false);
    setEmailError('');
  };

  const copyToClipboard = (text, setCopiedFn) => {
    navigator.clipboard.writeText(text);
    setCopiedFn(true);
    setTimeout(() => setCopiedFn(false), 2000);
  };

  // ── direct registration ───────────────────────────────────────────────────

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (formData.password !== formData.confirmPassword) { setError('Passwords do not match'); return; }
    if (formData.password.length < 8) { setError('Password must be at least 8 characters long'); return; }

    setLoading(true);
    try {
      const { confirmPassword, ...registrationData } = formData;
      const patient = await registerPatient(registrationData);
      setCreatedCreds({ name: formData.name, email: formData.email, password: formData.password });
      setFormData(EMPTY_FORM);
      if (onPatientAdded) onPatientAdded(patient);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  // ── invite generation ─────────────────────────────────────────────────────

  const handleGenerateInvite = async () => {
    setInviteError('');
    setInviteResult(null);
    setInviteCopied(false);
    setSendEmail('');
    setEmailSent(false);
    setEmailError('');
    setInviteLoading(true);
    try {
      const data = await createPatientInvitation(inviteEmail.trim() || null);
      setInviteResult(data);
      if (inviteEmail.trim()) setSendEmail(inviteEmail.trim());
    } catch (err) {
      setInviteError(err?.response?.data?.detail || err || 'Failed to generate invitation.');
    } finally {
      setInviteLoading(false);
    }
  };

  // ── email sending ─────────────────────────────────────────────────────────

  const handleSendEmail = async () => {
    if (!sendEmail.trim()) return;
    setEmailError('');
    setEmailSending(true);
    try {
      await sendInviteEmail(inviteResult.token, sendEmail.trim());
      setEmailSent(true);
    } catch (err) {
      setEmailError(err?.response?.data?.detail || err?.message || 'Failed to send email.');
    } finally {
      setEmailSending(false);
    }
  };

  // ── render ────────────────────────────────────────────────────────────────

  if (!showForm) {
    return (
      <button className="add-patient-btn" onClick={() => setShowForm(true)}>
        <span className="plus-icon">+</span> Add New Patient
      </button>
    );
  }

  const loginUrl = `${window.location.origin}/patient/login`;

  return (
    <div className="add-patient-overlay" onClick={(e) => {
      if (e.target.className === 'add-patient-overlay') handleClose();
    }}>
      <div className="add-patient-modal">
        <div className="modal-header">
          <h2>Add New Patient</h2>
          <button className="close-btn" onClick={handleClose}>×</button>
        </div>

        <div className="invite-tabs">
          <button className={`invite-tab-btn${activeTab === 'direct' ? ' active' : ''}`} onClick={() => setActiveTab('direct')}>
            Create Account
          </button>
          <button className={`invite-tab-btn${activeTab === 'invite' ? ' active' : ''}`} onClick={() => setActiveTab('invite')}>
            Send Invitation Link
          </button>
        </div>

        {/* ── MODE 1: Therapist creates account ── */}
        {activeTab === 'direct' && !createdCreds && (
          <>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSubmit} className="patient-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Full Name *</label>
                  <input name="name" value={formData.name} onChange={handleChange} required placeholder="Patient's full name" />
                </div>
                <div className="form-group">
                  <label>Email Address *</label>
                  <input type="email" name="email" value={formData.email} onChange={handleChange} required placeholder="patient@example.com" />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Password *</label>
                  <input type="password" name="password" value={formData.password} onChange={handleChange} required placeholder="Minimum 8 characters" />
                </div>
                <div className="form-group">
                  <label>Confirm Password *</label>
                  <input type="password" name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} required placeholder="Re-enter password" />
                </div>
              </div>
              <div className="form-group">
                <label>Conditions *</label>
                <input name="conditions" value={formData.conditions} onChange={handleChange} required placeholder="e.g., OCD, ADHD, Anxiety" />
              </div>
              <div className="form-group">
                <label>Conditions Description</label>
                <textarea name="conditions_description" value={formData.conditions_description} onChange={handleChange} rows={4} placeholder="Detailed description…" />
              </div>
              <div className="form-group">
                <label>Address *</label>
                <textarea name="address" value={formData.address} onChange={handleChange} required rows={2} placeholder="Patient's residential address" />
              </div>
              <div className="form-actions">
                <button type="button" className="cancel-btn" onClick={handleClose}>Cancel</button>
                <button type="submit" className="submit-btn" disabled={loading}>
                  {loading ? 'Creating Account…' : 'Create Account & Get Credentials'}
                </button>
              </div>
            </form>
          </>
        )}

        {/* ── MODE 1 success: shareable credentials card ── */}
        {activeTab === 'direct' && createdCreds && (() => {
          const shareText =
`Your Nirbaan therapy account is ready.

Name: ${createdCreds.name}
Email: ${createdCreds.email}
Password: ${createdCreds.password}
Login at: ${loginUrl}

You can change your password after logging in.`;
          return (
            <div className="invite-panel">
              <p className="invite-result-label" style={{ color: '#4ecdc4', fontWeight: 600, marginBottom: '0.8rem' }}>
                ✓ Account created for {createdCreds.name}
              </p>
              <p className="invite-description">
                Copy the credentials below and share them with your patient via any channel (WhatsApp, email, etc.).
              </p>
              <div className="creds-card">
                <div className="creds-row"><span className="creds-label">Name</span><span className="creds-value">{createdCreds.name}</span></div>
                <div className="creds-row"><span className="creds-label">Email</span><span className="creds-value">{createdCreds.email}</span></div>
                <div className="creds-row"><span className="creds-label">Password</span><span className="creds-value creds-password">{createdCreds.password}</span></div>
                <div className="creds-row"><span className="creds-label">Login URL</span><span className="creds-value" style={{ fontSize: '0.78rem' }}>{loginUrl}</span></div>
              </div>
              <div className="form-actions" style={{ marginTop: '1rem' }}>
                <button type="button" className="cancel-btn" onClick={() => setCreatedCreds(null)}>
                  Add Another
                </button>
                <button type="button" className="submit-btn" onClick={() => copyToClipboard(shareText, setCredsCopied)}>
                  {credsCopied ? 'Copied!' : 'Copy Credentials'}
                </button>
              </div>
              <button type="button" className="close-text-btn" onClick={handleClose}>Done — close window</button>
            </div>
          );
        })()}

        {/* ── MODE 2: Invite link ── */}
        {activeTab === 'invite' && (
          <div className="invite-panel">
            <p className="invite-description">
              Generate a one-time link. The patient opens it and fills in their own details.
              Their account is automatically linked to your workspace. Link expires in 7 days.
            </p>
            <div className="form-group">
              <label>Restrict to email address <span style={{ color: '#8aa8a8' }}>(optional)</span></label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="patient@example.com — leave blank for open invite"
              />
            </div>
            {inviteError && <div className="error-message">{inviteError}</div>}

            {!inviteResult ? (
              <div className="form-actions">
                <button type="button" className="cancel-btn" onClick={handleClose}>Cancel</button>
                <button type="button" className="submit-btn" onClick={handleGenerateInvite} disabled={inviteLoading}>
                  {inviteLoading ? 'Generating…' : 'Generate Invite Link'}
                </button>
              </div>
            ) : (
              <div className="invite-result">
                <p className="invite-result-label">Share this link with your patient:</p>
                <div className="invite-link-row">
                  <input type="text" readOnly value={inviteResult.invite_url} className="invite-link-input" />
                  <button type="button" className="submit-btn" onClick={() => copyToClipboard(inviteResult.invite_url, setInviteCopied)}>
                    {inviteCopied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <p className="invite-expiry">
                  Expires: {new Date(inviteResult.expires_at).toLocaleString()}
                  {inviteResult.invited_email && ` · Locked to: ${inviteResult.invited_email}`}
                </p>

                {/* Email sending section */}
                <div className="invite-send-email">
                  <p className="invite-result-label" style={{ marginBottom: '0.5rem' }}>Or send directly to patient's email:</p>
                  <div className="invite-link-row">
                    <input
                      type="email"
                      className="invite-link-input"
                      placeholder="patient@example.com"
                      value={sendEmail}
                      onChange={(e) => { setSendEmail(e.target.value); setEmailSent(false); setEmailError(''); }}
                      disabled={emailSent}
                    />
                    <button
                      type="button"
                      className="submit-btn"
                      onClick={handleSendEmail}
                      disabled={emailSending || emailSent || !sendEmail.trim()}
                    >
                      {emailSending ? 'Sending…' : emailSent ? 'Sent!' : 'Send Email'}
                    </button>
                  </div>
                  {emailError && <p style={{ color: '#f87171', fontSize: '0.82rem', marginTop: '0.4rem' }}>{emailError}</p>}
                  {emailSent && <p style={{ color: '#4ecdc4', fontSize: '0.82rem', marginTop: '0.4rem' }}>Invitation email delivered successfully.</p>}
                </div>

                <div className="form-actions">
                  <button type="button" className="cancel-btn" onClick={() => { setInviteResult(null); setInviteEmail(''); setSendEmail(''); setEmailSent(false); setEmailError(''); }}>
                    Generate Another
                  </button>
                  <button type="button" className="submit-btn" onClick={handleClose}>Done</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AddPatient;
