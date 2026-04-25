import { useState, useEffect, useCallback, useRef } from 'react';
import VideoCall from '../components/VideoCall';
import TranscriptDisplay from '../components/TranscriptDisplay';
import { startSession, endSession, getSessionAnalysis } from '../api/therapy-session.api';
import './VideoSessionWithTranscript.css';

const WS_BASE = `${(import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/^http/, 'ws')}/api/therapy-sessions`;

/**
 * Video call with WebSocket-streamed live transcription and post-session analysis.
 *
 * Route: /video-session-transcript/:therapistId/:patientId
 */
const VideoSessionWithTranscript = ({ therapistId, patientId, userType }) => {
  const [sessionId, setSessionId] = useState(null);
  const [transcripts, setTranscripts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [callActive, setCallActive] = useState(false);

  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);

  // ── Create session on mount ──────────────────────────────
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

  // ── Streaming transcription helpers ──────────────────────
  const userId = userType === 'therapist' ? therapistId : patientId;

  const startStreaming = useCallback(async () => {
    if (!sessionId || wsRef.current) return;

    // 1. Open transcription WebSocket
    const wsUrl = `${WS_BASE}/ws/transcription/${sessionId}?userId=${userId}&userType=${userType}&language=en`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = async () => {
      console.log('[StreamTranscript] WS connected');
      setIsLive(true);

      // 2. Capture mic via Web Audio API → MediaRecorder
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
        streamRef.current = stream;

        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4';

        const recorder = new MediaRecorder(stream, { mimeType });
        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);            // binary frame
          }
        };

        // Produce a chunk every 2 seconds
        recorder.start(2000);
        console.log('[StreamTranscript] MediaRecorder started, mimeType:', mimeType);
      } catch (err) {
        console.error('[StreamTranscript] Mic access failed:', err);
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'transcript') {
          setTranscripts((prev) => [...prev, msg]);
        } else if (msg.type === 'error') {
          console.warn('[StreamTranscript] Server error:', msg.message);
        }
      } catch {
        // ignore non-JSON frames
      }
    };

    ws.onclose = () => {
      console.log('[StreamTranscript] WS closed');
      setIsLive(false);
      wsRef.current = null;
    };

    ws.onerror = (err) => {
      console.error('[StreamTranscript] WS error:', err);
    };
  }, [sessionId, userId, userType]);

  const stopStreaming = useCallback(() => {
    // Stop recorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    // Release mic
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    // Close WS gracefully
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'stop' }));
      ws.close();
    }
    wsRef.current = null;
    setIsLive(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopStreaming();
  }, [stopStreaming]);

  // ── Call lifecycle ───────────────────────────────────────
  const handleCallStart = useCallback(() => {
    setCallActive(true);
    startStreaming();
  }, [startStreaming]);

  const handleCallEnd = useCallback(async () => {
    setCallActive(false);
    stopStreaming();

    if (!sessionId) return;

    // End session on backend → triggers AI analysis
    setAnalysisLoading(true);
    try {
      const session = await endSession(sessionId);
      // Try to load analysis (may already be attached)
      if (session.analysis) {
        setAnalysis(session.analysis);
      } else {
        // Fetch separately in case the sync generation takes a moment
        const a = await getSessionAnalysis(sessionId);
        setAnalysis(a);
      }
    } catch (err) {
      console.warn('Post-session analysis not available:', err);
    } finally {
      setAnalysisLoading(false);
    }
  }, [sessionId, stopStreaming]);

  // ── Render ───────────────────────────────────────────────
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
            {isLive && <span className="header-live-dot">● Live Transcription</span>}
          </div>
        )}
      </div>

      <div className="session-content">
        <div className="video-section">
          <VideoCall
            userId={userId}
            userType={userType}
            targetUserId={userType === 'therapist' ? patientId : null}
            sessionId={sessionId}
            onCallStart={handleCallStart}
            onCallEnd={handleCallEnd}
          />
        </div>

        <div className="transcript-sidebar">
          <TranscriptDisplay
            transcripts={transcripts}
            autoScroll={true}
            maxHeight="calc(100vh - 200px)"
            showClear={true}
            onClear={() => setTranscripts([])}
            isLive={isLive}
          />

          {/* Post-session analysis panel */}
          {analysisLoading && (
            <div className="analysis-panel loading-analysis">
              <div className="analysis-spinner" />
              <span>Generating session analysis...</span>
            </div>
          )}

          {analysis && !analysisLoading && (
            <div className="analysis-panel">
              <h3>Session Analysis</h3>

              <div className="analysis-section">
                <h4>Summary</h4>
                <p>{analysis.summary}</p>
              </div>

              {analysis.detected_topics?.length > 0 && (
                <div className="analysis-section">
                  <h4>Detected Topics</h4>
                  <div className="topic-tags">
                    {analysis.detected_topics.map((topic, i) => (
                      <span key={i} className="topic-tag">{topic}</span>
                    ))}
                  </div>
                </div>
              )}

              {analysis.therapist_interventions?.length > 0 && (
                <div className="analysis-section">
                  <h4>Therapist Interventions</h4>
                  <ul className="intervention-list">
                    {analysis.therapist_interventions.map((item, i) => (
                      <li key={i}>
                        <strong>{typeof item === 'string' ? item : item.type}:</strong>{' '}
                        {typeof item === 'string' ? '' : item.description}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoSessionWithTranscript;
