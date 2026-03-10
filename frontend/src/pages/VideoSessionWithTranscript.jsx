import { useState, useEffect, useCallback } from 'react';
import VideoCall from '../components/VideoCall';
import TranscriptDisplay from '../components/TranscriptDisplay';
import { startSession, getSession } from '../api/therapy-session.api';
import './VideoSessionWithTranscript.css';

/**
 * Example: Video call with live transcript display
 * 
 * Route: /video-session-transcript/:therapistId/:patientId
 */
const VideoSessionWithTranscript = ({ therapistId, patientId, userType }) => {
  const [sessionId, setSessionId] = useState(null);
  const [transcripts, setTranscripts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const initializeSession = useCallback(async () => {
    setIsLoading(true);
    try {
      const session = await startSession(therapistId, patientId);
      setSessionId(session.id);
      setTranscripts(session.transcripts || []);
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsLoading(false);
    }
  }, [therapistId, patientId]);

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  const refreshTranscripts = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      const session = await getSession(sessionId);
      setTranscripts(session.transcripts || []);
    } catch (error) {
      console.error('Failed to refresh transcripts:', error);
    }
  }, [sessionId]);

  useEffect(() => {
    // Auto-refresh transcripts every 5 seconds during session
    const interval = setInterval(() => {
      if (sessionId) {
        refreshTranscripts();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [sessionId, refreshTranscripts]);

  if (isLoading) {
    return <div className="loading">Loading session...</div>;
  }

  return (
    <div className="video-session-transcript-page">
      <div className="session-header">
        <h1>Video Therapy Session</h1>
        <div className="session-meta">
          <span>Session ID: {sessionId}</span>
          <button onClick={refreshTranscripts} className="refresh-btn">
            Refresh Transcripts
          </button>
        </div>
      </div>

      <div className="session-content">
        <div className="video-section">
          <VideoCall
            userId={userType === 'therapist' ? therapistId : patientId}
            userType={userType}
            targetUserId={userType === 'therapist' ? patientId : null}
            onCallEnd={() => console.log('Call ended')}
          />
        </div>

        <div className="transcript-sidebar">
          <TranscriptDisplay
            transcripts={transcripts}
            autoScroll={true}
            maxHeight="calc(100vh - 200px)"
            showClear={false}
          />
        </div>
      </div>
    </div>
  );
};

export default VideoSessionWithTranscript;
