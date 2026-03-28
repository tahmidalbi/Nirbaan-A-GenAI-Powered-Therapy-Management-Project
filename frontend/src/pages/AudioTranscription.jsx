import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import AudioRecorder from '../components/AudioRecorder';
import TranscriptDisplay from '../components/TranscriptDisplay';
import { getSession } from '../api/therapy-session.api';
import './AudioTranscription.css';

/**
 * Example page for audio transcription during therapy sessions
 * 
 * Route: /audio-transcription/:sessionId/:speaker
 */
const AudioTranscription = () => {
  const { sessionId, speaker } = useParams();
  const [sessionData, setSessionData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const session = await getSession(parseInt(sessionId));
      setSessionData(session);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError(err.response?.data?.detail || 'Failed to load session');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const handleTranscription = (text, transcriptId) => {
    console.log('New transcription:', text, transcriptId);
    // Reload session to get updated transcripts
    loadSession();
  };

  const handleRefresh = () => {
    loadSession();
  };

  if (isLoading) {
    return (
      <div className="audio-transcription-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading session...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="audio-transcription-page">
        <div className="error-container">
          <h2>Error</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="audio-transcription-page">
      <div className="page-header">
        <h1>Audio Transcription</h1>
        {sessionData && (
          <div className="session-info">
            <span><strong>Session ID:</strong> {sessionData.id}</span>
            <span><strong>Started:</strong> {new Date(sessionData.started_at).toLocaleString()}</span>
            <span><strong>Speaker:</strong> {speaker}</span>
          </div>
        )}
      </div>

      <div className="main-content">
        <div className="content-grid">
          <div className="recorder-section">
            <AudioRecorder
              sessionId={parseInt(sessionId)}
              speaker={speaker}
              language="en"
              onTranscription={handleTranscription}
              autoSave={true}
              chunkDuration={10000} // 10 seconds
            />
          </div>

          <div className="transcript-section">
            <TranscriptDisplay
              transcripts={sessionData?.transcripts || []}
              autoScroll={true}
              maxHeight="600px"
              showClear={false}
            />
          </div>
        </div>

        <div className="session-actions">
          <button className="refresh-btn" onClick={handleRefresh}>
            🔄 Refresh Transcripts
          </button>
        </div>
      </div>

      <div className="usage-tips">
        <h3>💡 Tips</h3>
        <ul>
          <li>Click "Start Recording" to begin capturing audio</li>
          <li>Audio is automatically transcribed every 10 seconds</li>
          <li>Transcriptions are automatically saved to this session</li>
          <li>You can pause/resume recording at any time</li>
          <li>Click "Stop" when finished to process any remaining audio</li>
          <li>Use "Clear" to remove local transcriptions (saved ones remain)</li>
        </ul>
      </div>
    </div>
  );
};

export default AudioTranscription;
