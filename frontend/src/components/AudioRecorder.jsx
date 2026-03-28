import { useState, useRef, useEffect } from 'react';
import { transcribeAudio } from '../api/therapy-session.api';
import './AudioRecorder.css';

const AudioRecorder = ({ 
  sessionId = null,
  speaker = 'therapist',
  language = 'en',
  onTranscription = null,
  autoSave = false,
  chunkDuration = 5000 // Record in 5-second chunks
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const chunkTimerRef = useRef(null);
  const recordingTimerRef = useRef(null);

  useEffect(() => {
    return () => {
      stopRecording();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      setError(null);
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      streamRef.current = stream;

      // Create MediaRecorder with supported format
      let mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/ogg';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4';
        }
      }

      const mediaRecorder = new MediaRecorder(stream, { 
        mimeType,
        audioBitsPerSecond: 128000
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (audioChunksRef.current.length > 0) {
          await processAudioChunks();
        }
      };

      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
      setIsPaused(false);
      setRecordingTime(0);

      // Start recording timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      // Set up automatic chunk processing if enabled
      if (chunkDuration > 0) {
        startChunkTimer();
      }

    } catch (err) {
      console.error('Error starting recording:', err);
      setError(`Failed to access microphone: ${err.message}`);
    }
  };

  const startChunkTimer = () => {
    chunkTimerRef.current = setInterval(() => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        // Stop and restart to trigger ondataavailable
        mediaRecorderRef.current.stop();
        
        // Small delay before restarting
        setTimeout(() => {
          if (mediaRecorderRef.current && streamRef.current) {
            audioChunksRef.current = [];
            mediaRecorderRef.current.start();
          }
        }, 100);
      }
    }, chunkDuration);
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      
      // Restart recording timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    }
  };

  const stopRecording = () => {
    if (chunkTimerRef.current) {
      clearInterval(chunkTimerRef.current);
      chunkTimerRef.current = null;
    }

    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    setIsRecording(false);
    setIsPaused(false);
  };

  const processAudioChunks = async () => {
    if (audioChunksRef.current.length === 0) return;

    setIsProcessing(true);
    setError(null);

    try {
      const mimeType = mediaRecorderRef.current.mimeType;
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
      const format = mimeType.split('/')[1].split(';')[0];

      const result = await transcribeAudio(audioBlob, {
        language: language || undefined,
        sessionId: sessionId || undefined,
        speaker: speaker || undefined,
        format,
      });

      if (result.success && result.text) {
        const newTranscript = {
          id: result.transcript_id,
          speaker,
          text: result.text,
          timestamp: new Date().toISOString(),
        };

        setTranscripts(prev => [...prev, newTranscript]);
        setCurrentTranscript(result.text);

        if (onTranscription) {
          onTranscription(newTranscript);
        }
      }

    } catch (err) {
      console.error('Error processing audio:', err);
      setError(`Transcription error: ${err.message}`);
    } finally {
      setIsProcessing(false);
      audioChunksRef.current = [];
    }
  };

  const clearTranscripts = () => {
    setTranscripts([]);
    setCurrentTranscript('');
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-recorder-container">
      <div className="recorder-header">
        <h3>Audio Transcription</h3>
        {isRecording && (
          <div className="recording-indicator">
            <span className="recording-dot"></span>
            <span className="recording-time">{formatTime(recordingTime)}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="recorder-controls">
        {!isRecording ? (
          <button 
            className="record-btn start-btn" 
            onClick={startRecording}
            disabled={isProcessing}
          >
            🎤 Start Recording
          </button>
        ) : (
          <>
            {!isPaused ? (
              <button 
                className="record-btn pause-btn" 
                onClick={pauseRecording}
              >
                ⏸ Pause
              </button>
            ) : (
              <button 
                className="record-btn resume-btn" 
                onClick={resumeRecording}
              >
                ▶ Resume
              </button>
            )}
            <button 
              className="record-btn stop-btn" 
              onClick={stopRecording}
            >
              ⏹ Stop
            </button>
          </>
        )}

        {transcripts.length > 0 && (
          <button 
            className="record-btn clear-btn" 
            onClick={clearTranscripts}
            disabled={isRecording}
          >
            🗑 Clear
          </button>
        )}
      </div>

      {isProcessing && (
        <div className="processing-indicator">
          <div className="spinner"></div>
          <span>Transcribing audio...</span>
        </div>
      )}

      {currentTranscript && (
        <div className="current-transcript">
          <h4>Latest Transcription:</h4>
          <p>{currentTranscript}</p>
        </div>
      )}

      {transcripts.length > 0 && (
        <div className="transcript-history">
          <h4>Transcription History:</h4>
          <div className="transcript-list">
            {transcripts.map((transcript, index) => (
              <div key={index} className="transcript-item">
                <div className="transcript-meta">
                  <span className="transcript-number">#{index + 1}</span>
                  <span className="transcript-time">
                    {new Date(transcript.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="transcript-text">
                  {transcript.text}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="recorder-info">
        <p>
          <strong>Settings:</strong> 
          {chunkDuration > 0 && ` Auto-transcribe every ${chunkDuration / 1000}s`}
          {autoSave && sessionId && ` | Auto-save to session #${sessionId}`}
        </p>
      </div>
    </div>
  );
};

export default AudioRecorder;
