import { useState, useEffect, useCallback } from 'react';
import VideoCall from '../components/VideoCall';
import AudioRecorder from '../components/AudioRecorder';
import TranscriptDisplay from '../components/TranscriptDisplay';
import { startSession } from '../api/therapy-session.api';
import './VideoSessionWithTranscript.css';

/**
 * Video call with live audio transcription.
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

  // Append each new chunk returned by AudioRecorder immediately — no polling needed.
  const handleTranscription = useCallback((transcriptEntry) => {
    setTranscripts(prev => [...prev, transcriptEntry]);
  }, []);

  if (isLoading) {
    return <div className="loading">Loading session...</div>;
  }

  return (
    <div className="video-session-transcript-page">
      <div className="session-header">
        <h1>Video Therapy Session</h1>
        {sessionId && (
          <div className="session-meta">
            <span>Session ID: {sessionId}</span>
          </div>
        )}
      </div>

      <div className="session-content">
        <div className="video-section">
          <VideoCall
            userId={userType === 'therapist' ? therapistId : patientId}
            userType={userType}
            targetUserId={userType === 'therapist' ? patientId : null}
            sessionId={sessionId}
            onCallEnd={() => console.log('Call ended')}
          />

          {/* AudioRecorder sits beneath the video controls */}
          {sessionId && (
            <AudioRecorder
              sessionId={sessionId}
              speaker={userType}
              language="en"
              chunkDuration={5000}
              autoSave={true}
              onTranscription={handleTranscription}
            />
          )}
        </div>

        <div className="transcript-sidebar">
          <TranscriptDisplay
            transcripts={transcripts}
            autoScroll={true}
            maxHeight="calc(100vh - 200px)"
            showClear={true}
            onClear={() => setTranscripts([])}
          />
        </div>
      </div>
    </div>
  );
};

export default VideoSessionWithTranscript;
