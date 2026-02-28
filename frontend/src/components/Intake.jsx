import { useState, useEffect } from 'react';
import { createIntake, getMyIntake, updateMyIntake } from '../api/intake.api';
import './Intake.css';

const Intake = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isEditing, setIsEditing] = useState(true);
  const [existingIntake, setExistingIntake] = useState(null);

  const [formData, setFormData] = useState({
    your_story: '',
    when_started: '',
    tried_previous_therapy: false,
    previous_therapy_details: '',
    taken_medication: false,
    medication_details: '',
    affected_life_areas: '',
    other_conditions: '',
    issues: [{ issue: '', severity: 5 }]
  });

  useEffect(() => {
    fetchExistingIntake();
  }, []);

  const fetchExistingIntake = async () => {
    try {
      const intake = await getMyIntake();
      setExistingIntake(intake);
      setFormData({
        your_story: intake.your_story,
        when_started: intake.when_started,
        tried_previous_therapy: intake.tried_previous_therapy,
        previous_therapy_details: intake.previous_therapy_details || '',
        taken_medication: intake.taken_medication,
        medication_details: intake.medication_details || '',
        affected_life_areas: intake.affected_life_areas || '',
        other_conditions: intake.other_conditions || '',
        issues: intake.issues.length > 0 ? intake.issues : [{ issue: '', severity: 5 }]
      });
      setIsEditing(false);
    } catch (err) {
      // No existing intake, user can create new one
      setIsEditing(true);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleIssueChange = (index, field, value) => {
    const newIssues = [...formData.issues];
    newIssues[index][field] = field === 'severity' ? parseInt(value) : value;
    setFormData(prev => ({ ...prev, issues: newIssues }));
  };

  const addIssue = () => {
    setFormData(prev => ({
      ...prev,
      issues: [...prev.issues, { issue: '', severity: 5 }]
    }));
  };

  const removeIssue = (index) => {
    if (formData.issues.length > 1) {
      const newIssues = formData.issues.filter((_, i) => i !== index);
      setFormData(prev => ({ ...prev, issues: newIssues }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      // Validate issues
      const validIssues = formData.issues.filter(issue => issue.issue.trim() !== '');
      if (validIssues.length === 0) {
        throw new Error('Please add at least one issue');
      }

      const submitData = {
        ...formData,
        issues: validIssues
      };

      if (existingIntake) {
        await updateMyIntake(submitData);
        setSuccess('Intake form updated successfully!');
      } else {
        await createIntake(submitData);
        setSuccess('Intake form submitted successfully!');
      }
      
      setIsEditing(false);
      await fetchExistingIntake();
    } catch (err) {
      setError(typeof err === 'string' ? err : err.message || 'Failed to submit intake');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="intake-container">
      <div className="intake-card">
        <h2 className="intake-title">Patient Intake Form</h2>
        <p className="intake-subtitle">Please provide detailed information to help us understand your journey</p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        {!isEditing && existingIntake ? (
          <div className="intake-view">
            <div className="intake-section">
              <h3>Your Story</h3>
              <p className="intake-text">{existingIntake.your_story}</p>
            </div>

            <div className="intake-section">
              <h3>When It Started</h3>
              <p className="intake-text">{existingIntake.when_started}</p>
            </div>

            <div className="intake-section">
              <h3>Previous Therapy</h3>
              <p className="intake-text">
                {existingIntake.tried_previous_therapy ? 'Yes' : 'No'}
              </p>
              {existingIntake.tried_previous_therapy && existingIntake.previous_therapy_details && (
                <div className="intake-details">
                  <p>{existingIntake.previous_therapy_details}</p>
                </div>
              )}
            </div>

            <div className="intake-section">
              <h3>Medication History</h3>
              <p className="intake-text">
                {existingIntake.taken_medication ? 'Yes' : 'No'}
              </p>
              {existingIntake.taken_medication && existingIntake.medication_details && (
                <div className="intake-details">
                  <p>{existingIntake.medication_details}</p>
                </div>
              )}
            </div>

            {existingIntake.affected_life_areas && (
              <div className="intake-section">
                <h3>Life Areas Affected</h3>
                <p className="intake-text">{existingIntake.affected_life_areas}</p>
              </div>
            )}

            {existingIntake.other_conditions && (
              <div className="intake-section">
                <h3>Other Physical or Mental Conditions</h3>
                <p className="intake-text">{existingIntake.other_conditions}</p>
              </div>
            )}

            <div className="intake-section">
              <h3>Issues & Severity</h3>
              <div className="issues-list">
                {existingIntake.issues.map((issue, index) => (
                  <div key={index} className="issue-item-view">
                    <span className="issue-name">{issue.issue}</span>
                    <span className="severity-badge">Severity: {issue.severity}/10</span>
                  </div>
                ))}
              </div>
            </div>

            <button 
              onClick={() => setIsEditing(true)} 
              className="edit-btn"
            >
              Edit Intake Form
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="intake-form">
            {/* Your Story */}
            <div className="form-group">
              <label>Your Story (in detail)</label>
              <textarea
                name="your_story"
                value={formData.your_story}
                onChange={handleChange}
                required
                rows="6"
                placeholder="Please share your story in as much detail as you're comfortable with..."
                className="vintage-textarea"
              />
            </div>

            {/* When Started */}
            <div className="form-group">
              <label>When It Started</label>
              <input
                type="text"
                name="when_started"
                value={formData.when_started}
                onChange={handleChange}
                required
                placeholder="e.g., 2 years ago, since childhood..."
                className="vintage-input"
              />
            </div>

            {/* Previous Therapy */}
            <div className="form-group checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="tried_previous_therapy"
                  checked={formData.tried_previous_therapy}
                  onChange={handleChange}
                />
                <span>Have you tried any previous therapy?</span>
              </label>
            </div>

            {formData.tried_previous_therapy && (
              <div className="form-group nested-field">
                <label>Describe your previous therapy experience</label>
                <textarea
                  name="previous_therapy_details"
                  value={formData.previous_therapy_details}
                  onChange={handleChange}
                  rows="4"
                  placeholder="Type of therapy, duration, what worked, what didn't..."
                  className="vintage-textarea"
                />
              </div>
            )}

            {/* Medication */}
            <div className="form-group checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="taken_medication"
                  checked={formData.taken_medication}
                  onChange={handleChange}
                />
                <span>Have you taken any medication?</span>
              </label>
            </div>

            {formData.taken_medication && (
              <div className="form-group nested-field">
                <label>What medications have you taken?</label>
                <textarea
                  name="medication_details"
                  value={formData.medication_details}
                  onChange={handleChange}
                  rows="3"
                  placeholder="Medication names, dosages, duration, effects..."
                  className="vintage-textarea"
                />
              </div>
            )}

            {/* Life Areas Affected */}
            <div className="form-group">
              <label>Which areas of your life are getting affected?</label>
              <textarea
                name="affected_life_areas"
                value={formData.affected_life_areas}
                onChange={handleChange}
                rows="4"
                placeholder="e.g., Work performance, relationships, sleep, social life, daily routines..."
                className="vintage-textarea"
              />
            </div>

            {/* Other Conditions */}
            <div className="form-group">
              <label>Do you have any other physical or mental conditions?</label>
              <textarea
                name="other_conditions"
                value={formData.other_conditions}
                onChange={handleChange}
                rows="3"
                placeholder="Please list any other conditions you're dealing with..."
                className="vintage-textarea"
              />
            </div>

            {/* Issues List */}
            <div className="form-group">
              <label>Your Issues & Severity</label>
              <p className="field-hint">Describe your concerns with severity ratings (1-10)</p>
              
              {formData.issues.map((issue, index) => (
                <div key={index} className="issue-item">
                  <div className="issue-inputs">
                    <textarea
                      value={issue.issue}
                      onChange={(e) => handleIssueChange(index, 'issue', e.target.value)}
                      rows="3"
                      className="vintage-textarea issue-textarea"
                    />
                    <div className="severity-control">
                      <label className="severity-label">Severity:</label>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        value={issue.severity}
                        onChange={(e) => handleIssueChange(index, 'severity', e.target.value)}
                        className="severity-slider"
                      />
                      <span className="severity-value">{issue.severity}</span>
                    </div>
                    {formData.issues.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeIssue(index)}
                        className="remove-issue-btn"
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>
              ))}

              <button
                type="button"
                onClick={addIssue}
                className="add-issue-btn"
              >
                + Add Another Issue
              </button>
            </div>

            <div className="form-actions">
              <button type="submit" disabled={loading} className="submit-btn">
                {loading ? 'Submitting...' : existingIntake ? 'Update Intake' : 'Submit Intake'}
              </button>
              {existingIntake && (
                <button 
                  type="button" 
                  onClick={() => setIsEditing(false)} 
                  className="cancel-btn"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default Intake;
