import { useState, useRef, useEffect } from 'react';
import { appendTranscript } from '../api/session.api';
import { classifyEmotion } from '../utils/emotionClassifier';
import './VideoSession.css';

const VideoSession = ({ sessionId, therapistId, patientId }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [stream, setStream] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Initialize webcam and microphone
  useEffect(() => {
    const initializeMedia = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 1280, height: 720 },
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            sampleRate: 44100,
          },
        });

        setStream(mediaStream);
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      } catch (err) {
        console.error('Error accessing media devices:', err);
        setError('Failed to access camera/microphone. Please grant permissions.');
      }
    };

    initializeMedia();

    // Cleanup on unmount
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Start recording
  const startRecording = () => {
    if (!stream) {
      setError('No media stream available');
      return;
    }

    try {
      // Create MediaRecorder with audio only
      const audioStream = new MediaStream(
        stream.getAudioTracks()
      );

      const mediaRecorder = new MediaRecorder(audioStream, {
        mimeType: 'audio/webm',
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Collect audio chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Process audio when recording stops
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: 'audio/webm',
        });
        await processAudioChunk(audioBlob);
        audioChunksRef.current = [];
      };

      // Start recording with 5-second chunks
      mediaRecorder.start(5000);
      setIsRecording(true);
      setError('');
    } catch (err) {
      console.error('Error starting recording:', err);
      setError('Failed to start recording');
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Process audio chunk and send to backend
  const processAudioChunk = async (audioBlob) => {
    setIsProcessing(true);
    try {
      // In a real implementation, you would:
      // 1. Send audio to speech-to-text service (e.g., Whisper API, Google Speech-to-Text)
      // 2. Get transcription back
      // 3. Detect emotion using OpenAI
      // 4. Send to backend

      // Mock transcription for demonstration
      // Replace this with actual speech-to-text API call
      const transcribedText = 'This is a sample transcription of the audio chunk.';
      
      // Classify emotion using OpenAI
      const detectedEmotion = await classifyEmotion(transcribedText);

      const transcriptEntry = {
        speaker: 'patient', // or 'therapist' based on speaker identification
        text: transcribedText,
        emotion: detectedEmotion,
        timestamp: new Date().toISOString(),
      };

      // Send to backend
      if (sessionId) {
        const updatedSession = await appendTranscript(sessionId, transcriptEntry);
        setTranscript(updatedSession.transcript);
      } else {
        // If no session ID, just add to local state
        setTranscript((prev) => [...prev, transcriptEntry]);
      }
    } catch (err) {
      console.error('Error processing audio:', err);
      setError('Failed to process audio chunk');
    } finally {
      setIsProcessing(false);
    }
  };

  // Toggle recording
  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="video-session">
      <div className="video-container">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="video-stream"
        />
        
        <div className="video-controls">
          <button
            onClick={toggleRecording}
            className={`record-button ${isRecording ? 'recording' : ''}`}
            disabled={!stream}
          >
            {isRecording ? '⏹️ Stop Recording' : '🎙️ Start Recording'}
          </button>
          
          {isProcessing && (
            <span className="processing-indicator">Processing audio...</span>
          )}
        </div>

        {error && <div className="error-message">{error}</div>}
      </div>

      <div className="transcript-container">
        <div className="transcript-header">
          <h3>📝 Live Transcript</h3>
          <span className="transcript-count">
            {transcript.length} {transcript.length === 1 ? 'entry' : 'entries'}
          </span>
        </div>

        <div className="transcript-list">
          {transcript.length === 0 ? (
            <div className="empty-transcript">
              <p>Start recording to see the live transcript</p>
            </div>
          ) : (
            transcript.map((entry, index) => (
              <div key={index} className={`transcript-entry ${entry.speaker}`}>
                <div className="entry-header">
                  <span className="speaker">
                    {entry.speaker === 'therapist' ? '🩺' : '👤'}{' '}
                    {entry.speaker.charAt(0).toUpperCase() + entry.speaker.slice(1)}
                  </span>
                  {entry.emotion && (
                    <span className={`emotion emotion-${entry.emotion}`}>
                      {entry.emotion}
                    </span>
                  )}
                  <span className="timestamp">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="entry-text">{entry.text}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoSession;
