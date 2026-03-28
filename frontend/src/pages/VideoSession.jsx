import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import VideoCall from '../components/VideoCall';
import { startSession } from '../api/therapy-session.api';
import { useAuthStore } from '../store/authStore';
import './VideoSession.css';

/**
 * Example page demonstrating VideoCall component integration
 * 
 * Routes:
 * - /video-session/:userType/:userId/:patientId - Full parameter route
 * - /video-call/:sessionId - Incoming call route for patients
 */
const VideoSession = () => {
  const { userType, userId, patientId, sessionId } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  
  const [sessionData, setSessionData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const sessionCreatedRef = useRef(false); // prevent StrictMode double-creation

  // Determine actual userType and userId based on route and auth
  const actualUserType = userType || user?.role || 'patient';
  const actualUserId = userId || user?.id;

  const initializeSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const session = await startSession(parseInt(actualUserId), parseInt(patientId));
      setSessionData(session);
      console.log('Session created:', session);
    } catch (err) {
      console.error('Failed to create session:', err);
      setError(err.response?.data?.detail || 'Failed to create session');
    } finally {
      setIsLoading(false);
    }
  }, [actualUserId, patientId]);

  // For therapist, automatically create session on mount
  // For incoming call route (/video-call/:sessionId), session already exists
  useEffect(() => {
    if (sessionId) {
      // Incoming call scenario - sessionId provided in URL
      setSessionData({ id: sessionId });
      setIsLoading(false);
      // If auth user has no id yet (e.g. getCurrentPatient failed), log a warning
      if (!user?.id) {
        console.warn('VideoSession: user.id not available yet from auth store');
      }
    } else if (actualUserType === 'therapist' && actualUserId && patientId && !sessionCreatedRef.current) {
      // Therapist initiating call - create new session (guard against StrictMode double-mount)
      sessionCreatedRef.current = true;
      initializeSession();
    } else {
      setIsLoading(false);
    }
  }, [sessionId, actualUserType, actualUserId, patientId, initializeSession]);

  const handleCallEnd = () => {
    console.log('Call ended');
    // Navigate back or show session summary
    navigate(-1);
  };

  const getTargetUserId = () => {
    if (actualUserType === 'therapist') {
      return parseInt(patientId);
    }
    return null; // Patients don't initiate calls
  };

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

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Initializing session...</p>
        </div>
      ) : !sessionData ? null : (
        <div className="video-container">
          <VideoCall
            userId={actualUserId ? parseInt(actualUserId) : undefined}
            userType={actualUserType}
            targetUserId={getTargetUserId()}
            sessionId={sessionData?.id}
            onCallEnd={handleCallEnd}
          />
        </div>
      )}

      <div className="session-instructions">
        <h3>Instructions</h3>
        <ul>
          {actualUserType === 'therapist' ? (
            <>
              <li>Click "Start Call" to initiate the video session with your patient</li>
              <li>The patient will receive an incoming call notification</li>
              <li>Once they accept, the video call will begin</li>
            </>
          ) : (
            <>
              <li>Wait for your therapist to initiate the call</li>
              <li>You'll see an incoming call notification when they call</li>
              <li>Click "Accept" to join the video session</li>
            </>
          )}
          <li>Use the microphone button to mute/unmute</li>
          <li>Use the camera button to turn video on/off</li>
          <li>Click "End Call" when the session is complete</li>
        </ul>
      </div>
    </div>
  );
};

export default VideoSession;
