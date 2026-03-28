import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import VideoCall from '../components/VideoCall';
import { startSession } from '../api/therapy-session.api';
import { useAuthStore } from '../store/authStore';
import './VideoSession.css';

const VideoSession = () => {
  const { userType, userId, patientId, sessionId } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const [sessionData, setSessionData] = useState(null);
  const [isLoading, setIsLoading]     = useState(false);
  const [error, setError]             = useState(null);
  const sessionCreatedRef = useRef(false);

  const actualUserType = userType || user?.role || 'patient';
  const actualUserId   = userId   || user?.id;

  const initializeSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // POST /sessions/start — backend instantly notifies the patient via WS
      const session = await startSession(parseInt(actualUserId), parseInt(patientId));
      setSessionData(session);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create session');
    } finally {
      setIsLoading(false);
    }
  }, [actualUserId, patientId]);

  useEffect(() => {
    if (sessionId) {
      // Incoming call route (/video-call/:sessionId) — session already exists
      setSessionData({ id: parseInt(sessionId) });
    } else if (actualUserType === 'therapist' && actualUserId && patientId && !sessionCreatedRef.current) {
      sessionCreatedRef.current = true;
      initializeSession();
    } else {
      setIsLoading(false);
    }
  }, [sessionId, actualUserType, actualUserId, patientId, initializeSession]);

  const handleCallEnd = () => navigate(-1);

  return (
    <div className="video-session-page">
      <div className="video-session-header">
        <h1>Video Session</h1>
        {sessionData && (
          <div className="session-info">
            <span>Session ID: {sessionData.id}</span>
            {sessionData.started_at && (
              <span>Started: {new Date(sessionData.started_at).toLocaleString()}</span>
            )}
          </div>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {isLoading ? (
        <div className="loading-container">
          <div className="spinner" />
          <p>Initializing session…</p>
        </div>
      ) : !sessionData ? null : (
        <div className="video-container">
          <VideoCall
            userId={actualUserId ? parseInt(actualUserId) : undefined}
            userType={actualUserType}
            targetUserId={actualUserType === 'therapist' ? parseInt(patientId) : null}
            sessionId={sessionData.id}
            onCallEnd={handleCallEnd}
          />
        </div>
      )}

      <div className="session-instructions">
        <h3>Instructions</h3>
        <ul>
          {actualUserType === 'therapist' ? (
            <>
              <li>The patient has been notified of this call</li>
              <li>Click "Start Call" once the patient accepts to begin</li>
            </>
          ) : (
            <>
              <li>Click "Start Call" to connect your camera and microphone</li>
              <li>Click "End Call" when the session is complete</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
};

export default VideoSession;
