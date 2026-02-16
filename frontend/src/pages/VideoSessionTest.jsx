import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import VideoSession from '../components/VideoSession';
import { createSession } from '../api/session.api';
import './VideoSessionTest.css';

const VideoSessionTest = () => {
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // For testing, we can use hard-coded IDs or get from auth
  const [therapistId] = useState(1); // Change as needed
  const [patientId] = useState(1); // Change as needed

  const handleCreateSession = async () => {
    setLoading(true);
    setError('');
    try {
      const session = await createSession(therapistId, patientId);
      setSessionId(session.id);
    } catch (err) {
      setError(err.toString());
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="video-session-test-page">
      <div className="test-header">
        <button onClick={() => navigate(-1)} className="back-button">
          ← Back
        </button>
        <h1>Video Session Test</h1>
      </div>

      {!sessionId ? (
        <div className="session-setup">
          <div className="setup-card">
            <h2>🎥 Start Video Session</h2>
            <p>This will create a new therapy session and start recording.</p>
            
            <div className="setup-info">
              <div className="info-item">
                <strong>Therapist ID:</strong> {therapistId}
              </div>
              <div className="info-item">
                <strong>Patient ID:</strong> {patientId}
              </div>
            </div>

            {error && (
              <div className="error-box">
                <strong>Error:</strong> {error}
              </div>
            )}

            <button
              onClick={handleCreateSession}
              disabled={loading}
              className="create-session-button"
            >
              {loading ? '⏳ Creating Session...' : '🚀 Create Session & Start'}
            </button>

            <div className="setup-requirements">
              <h3>Requirements:</h3>
              <ul>
                <li>✅ Backend server running (port 8000)</li>
                <li>✅ Database tables created</li>
                <li>✅ Therapist and Patient exist in database</li>
                <li>✅ Camera and microphone permissions</li>
                <li>✅ OpenAI API key in .env file</li>
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <VideoSession
          sessionId={sessionId}
          therapistId={therapistId}
          patientId={patientId}
        />
      )}
    </div>
  );
};

export default VideoSessionTest;
