import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { transcribeAudio } from '../api/therapy-session.api';
import { endLiveSession } from '../api/sessions.api';
import './VideoCall.css';

const VideoCall = ({ 
  userId: userIdProp, 
  userType: userTypeProp, // "therapist" or "patient"
  targetUserId = null, // For therapist to call specific patient
  sessionId = null, // Therapy session ID
  onCallStart = () => {},
  onCallEnd = () => {} 
}) => {
  // Fall back to auth store if props are not valid numbers
  const authUser = useAuthStore((state) => state.user);
  const userId = (userIdProp && !isNaN(userIdProp)) ? userIdProp : authUser?.id;
  const userType = userTypeProp || authUser?.role;
  const [callState, setCallState] = useState('idle');
  const [wsConnected, setWsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);

  // Device selection
  const [audioInputs, setAudioInputs] = useState([]);   // microphones
  const [videoInputs, setVideoInputs] = useState([]);   // cameras
  const [audioOutputs, setAudioOutputs] = useState([]); // speakers
  const [selectedMic, setSelectedMic] = useState('');
  const [selectedCamera, setSelectedCamera] = useState('');
  const [selectedSpeaker, setSelectedSpeaker] = useState('');
  const [showDevices, setShowDevices] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0); // 0-100

  // Transcript state
  const [transcript, setTranscript] = useState([]);   // [{speaker, text, timestamp}]
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [showTranscript, setShowTranscript] = useState(true);

  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const audioLevelTimerRef = useRef(null);
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const wsRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const localStreamRef = useRef(null);
  const iceCandidateQueue = useRef([]);
  const callStateRef = useRef('idle');
  const pendingOfferRef = useRef(false);
  const mediaRecorderRef = useRef(null);
  const chunkTimerRef = useRef(null);
  const isTranscribingRef = useRef(false);

  // Keep callStateRef in sync
  callStateRef.current = callState;

  // Start/stop transcription when call connects or ends
  useEffect(() => {
    if (callState === 'connected') {
      startTranscription();
      onCallStart();
    } else if (callState === 'idle' || callState === 'ended') {
      stopTranscription();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callState]);

  // Log identity on mount
  useEffect(() => {
    console.log(`[VideoCall] Mounted — sessionId=${sessionId}, userId=${userId}, userType=${userType}`);
  }, [sessionId, userId, userType]);

  // Enumerate devices on mount (and after any device change)
  const refreshDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const mics = devices.filter(d => d.kind === 'audioinput');
      const cams = devices.filter(d => d.kind === 'videoinput');
      const speakers = devices.filter(d => d.kind === 'audiooutput');
      setAudioInputs(mics);
      setVideoInputs(cams);
      setAudioOutputs(speakers);
      // Set defaults only if nothing selected yet
      setSelectedMic(prev => prev || mics[0]?.deviceId || '');
      setSelectedCamera(prev => prev || cams[0]?.deviceId || '');
      setSelectedSpeaker(prev => prev || speakers[0]?.deviceId || '');
    } catch (err) {
      console.warn('[VideoCall] Could not enumerate devices:', err);
    }
  }, []);

  useEffect(() => {
    // Devices may have no labels until media permission granted; re-enumerate after that
    refreshDevices();
    navigator.mediaDevices.addEventListener('devicechange', refreshDevices);
    return () => navigator.mediaDevices.removeEventListener('devicechange', refreshDevices);
  }, [refreshDevices]);

  // Audio level meter — runs while local stream is active
  const startAudioMeter = useCallback((stream) => {
    try {
      const ctx = new AudioContext();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioContextRef.current = ctx;
      analyserRef.current = analyser;
      const buf = new Uint8Array(analyser.frequencyBinCount);
      audioLevelTimerRef.current = setInterval(() => {
        analyser.getByteFrequencyData(buf);
        const avg = buf.reduce((s, v) => s + v, 0) / buf.length;
        setAudioLevel(Math.min(100, Math.round(avg * 2)));
      }, 100);
    } catch (err) {
      console.warn('[VideoCall] Audio meter error:', err);
    }
  }, []);

  const stopAudioMeter = useCallback(() => {
    if (audioLevelTimerRef.current) clearInterval(audioLevelTimerRef.current);
    if (audioContextRef.current) { audioContextRef.current.close(); audioContextRef.current = null; }
    setAudioLevel(0);
  }, []);

  const stopTranscription = useCallback(() => {
    isTranscribingRef.current = false;
    if (chunkTimerRef.current) clearTimeout(chunkTimerRef.current);
    const rec = mediaRecorderRef.current;
    if (rec && rec.state === 'recording') {
      rec.stop(); // fires onstop to flush last chunk
    }
    mediaRecorderRef.current = null;
    setIsTranscribing(false);
  }, []);

  const startTranscription = useCallback(() => {
    if (!sessionId || !userType) return;
    const stream = localStreamRef.current;
    if (!stream) return;
    if (isTranscribingRef.current) return;

    const audioTracks = stream.getAudioTracks();
    if (audioTracks.length === 0) return;

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : 'audio/mp4';
    const format = mimeType.includes('webm') ? 'webm' : 'mp4';

    const recordChunk = () => {
      if (!isTranscribingRef.current) return;
      const audioStream = new MediaStream(localStreamRef.current?.getAudioTracks() ?? []);
      if (audioStream.getAudioTracks().length === 0) return;

      let chunks = [];
      let rec;
      try { rec = new MediaRecorder(audioStream, { mimeType }); }
      catch { rec = new MediaRecorder(audioStream); }

      rec.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      rec.onstop = async () => {
        // Skip if mic was muted — avoid sending silence to Whisper (causes hallucinations)
        const audioTrack = localStreamRef.current?.getAudioTracks()[0];
        const micIsActive = audioTrack ? audioTrack.enabled : true;

        if (chunks.length > 0 && micIsActive) {
          const blob = new Blob(chunks, { type: mimeType });
          try {
            const result = await transcribeAudio(blob, {
              sessionId, speaker: userType, language: 'en', format
            });
            if (result?.text?.trim()) {
              setTranscript(prev => [...prev, {
                speaker: userType, text: result.text.trim(), timestamp: new Date()
              }]);
            }
          } catch (err) {
            console.warn('[Transcript] Chunk failed:', err);
          }
        }
        // Schedule next chunk if still going
        if (isTranscribingRef.current) {
          chunkTimerRef.current = setTimeout(recordChunk, 0);
        }
      };

      rec.start();
      mediaRecorderRef.current = rec;
      // Stop after 10 seconds to flush
      chunkTimerRef.current = setTimeout(() => {
        if (rec.state === 'recording') rec.stop();
      }, 10000);
    };

    isTranscribingRef.current = true;
    setIsTranscribing(true);
    console.log('[Transcript] Starting chunked recording…');
    recordChunk();
  }, [sessionId, userType]);

  const cleanupMedia = useCallback(() => {
    stopTranscription();
    stopAudioMeter();
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }
    if (localVideoRef.current) localVideoRef.current.srcObject = null;
    if (remoteVideoRef.current) remoteVideoRef.current.srcObject = null;
    iceCandidateQueue.current = [];
  }, [stopAudioMeter, stopTranscription]);

  const sendMessage = useCallback((msg) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
      console.log(`[VideoCall] Sent: ${msg.type}`);
    } else {
      console.warn(`[VideoCall] WS not open, cannot send: ${msg.type}`);
    }
  }, []);

  // Switch microphone mid-call
  const switchMic = useCallback(async (deviceId) => {
    setSelectedMic(deviceId);
    const stream = localStreamRef.current;
    const pc = peerConnectionRef.current;
    if (!stream || !pc) return;
    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: { exact: deviceId } },
        video: false,
      });
      const newAudioTrack = newStream.getAudioTracks()[0];
      const sender = pc.getSenders().find(s => s.track?.kind === 'audio');
      if (sender) await sender.replaceTrack(newAudioTrack);
      // Stop old audio track
      stream.getAudioTracks().forEach(t => t.stop());
      // Replace in local stream
      stream.removeTrack(stream.getAudioTracks()[0]);
      stream.addTrack(newAudioTrack);
      stopAudioMeter();
      startAudioMeter(stream);
      console.log('[VideoCall] Switched mic to:', newAudioTrack.label);
    } catch (err) {
      console.error('[VideoCall] Failed to switch mic:', err);
    }
  }, [startAudioMeter, stopAudioMeter]);

  // Switch camera mid-call
  const switchCamera = useCallback(async (deviceId) => {
    setSelectedCamera(deviceId);
    const stream = localStreamRef.current;
    const pc = peerConnectionRef.current;
    if (!stream || !pc) return;
    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: deviceId } },
        audio: false,
      });
      const newVideoTrack = newStream.getVideoTracks()[0];
      const sender = pc.getSenders().find(s => s.track?.kind === 'video');
      if (sender) await sender.replaceTrack(newVideoTrack);
      stream.getVideoTracks().forEach(t => t.stop());
      if (localVideoRef.current) {
        const newStream2 = new MediaStream([newVideoTrack, ...stream.getAudioTracks()]);
        localVideoRef.current.srcObject = newStream2;
        localStreamRef.current = newStream2;
      }
      console.log('[VideoCall] Switched camera to:', newVideoTrack.label);
    } catch (err) {
      console.error('[VideoCall] Failed to switch camera:', err);
    }
  }, []);

  // Switch speaker (output device)
  const switchSpeaker = useCallback(async (deviceId) => {
    setSelectedSpeaker(deviceId);
    if (remoteVideoRef.current && remoteVideoRef.current.setSinkId) {
      try {
        await remoteVideoRef.current.setSinkId(deviceId);
        console.log('[VideoCall] Switched speaker to:', deviceId);
      } catch (err) {
        console.error('[VideoCall] Failed to switch speaker:', err);
      }
    }
  }, []);

  const setupPeerConnection = useCallback(async () => {
    console.log('[VideoCall] Setting up peer connection, requesting camera/mic...');
    const constraints = {
      audio: selectedMic ? { deviceId: { exact: selectedMic } } : true,
      video: selectedCamera ? { deviceId: { exact: selectedCamera } } : true,
    };
    console.log('[VideoCall] getUserMedia constraints:', constraints);
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    // Re-enumerate now that we have permission — labels will become available
    refreshDevices();
    const audioTrack = stream.getAudioTracks()[0];
    const videoTrack = stream.getVideoTracks()[0];
    console.log('[VideoCall] Audio track:', audioTrack?.label, '| enabled:', audioTrack?.enabled);
    console.log('[VideoCall] Video track:', videoTrack?.label, '| enabled:', videoTrack?.enabled);
    localStreamRef.current = stream;
    if (localVideoRef.current) localVideoRef.current.srcObject = stream;
    startAudioMeter(stream);

    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
      ]
    });
    peerConnectionRef.current = pc;

    stream.getTracks().forEach(track => {
      pc.addTrack(track, stream);
    });

    pc.ontrack = (event) => {
      console.log('[VideoCall] Received remote track:', event.track.kind);
      if (remoteVideoRef.current) remoteVideoRef.current.srcObject = event.streams[0];
      setCallState('connected');
    };

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        sendMessage({ type: 'ice-candidate', candidate: event.candidate });
      }
    };

    pc.onconnectionstatechange = () => {
      console.log('[VideoCall] PC connection state:', pc.connectionState);
      if (pc.connectionState === 'connected') setCallState('connected');
      if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
        setError('Connection lost');
        cleanupMedia();
      }
    };

    pc.oniceconnectionstatechange = () => {
      console.log('[VideoCall] ICE state:', pc.iceConnectionState);
    };

    return pc;
  }, [sendMessage, cleanupMedia]);

  // --- WebSocket effect ---
  useEffect(() => {
    if (!sessionId || !userId || !userType) {
      console.log(`[VideoCall] Skipping WS — missing: sessionId=${sessionId}, userId=${userId}, userType=${userType}`);
      return;
    }

    let cancelled = false;
    const wsUrl = `${(import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/^http/, 'ws')}/api/therapy-sessions/ws/signaling/${sessionId}`;
    console.log(`[VideoCall] Opening WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      if (cancelled) { ws.close(); return; }
      console.log(`[VideoCall] WebSocket OPEN — identifying as ${userType} #${userId}`);
      wsRef.current = ws;
      setWsConnected(true);
      setError(null);
      ws.send(JSON.stringify({ type: 'identify', userId: Number(userId), userType }));
    };

    ws.onmessage = async (event) => {
      if (cancelled) return;
      try {
        const msg = JSON.parse(event.data);
        console.log(`[VideoCall] Received: ${msg.type}`, msg.type === 'session_info' ? msg : '');

        switch (msg.type) {
          case 'connected':
            console.log(`[VideoCall] Identified in session ${sessionId}`);
            break;

          case 'user-joined':
            console.log(`[VideoCall] Peer joined: userId=${msg.userId}, userType=${msg.userType}`);
            console.log(`[VideoCall] pendingOffer=${pendingOfferRef.current}, hasPC=${!!peerConnectionRef.current}`);
            if (pendingOfferRef.current && peerConnectionRef.current) {
              try {
                const offer = await peerConnectionRef.current.createOffer();
                await peerConnectionRef.current.setLocalDescription(offer);
                ws.send(JSON.stringify({ type: 'offer', offer }));
                console.log('[VideoCall] Sent deferred offer to newly joined peer');
                pendingOfferRef.current = false;
              } catch (err) {
                console.error('[VideoCall] Error sending deferred offer:', err);
              }
            }
            break;

          case 'offer':
            console.log('[VideoCall] Processing incoming offer...');
            try {
              if (!peerConnectionRef.current) {
                await setupPeerConnection();
              }
              const pc = peerConnectionRef.current;
              await pc.setRemoteDescription(new RTCSessionDescription(msg.offer));
              console.log('[VideoCall] Remote description set');
              // drain queued ICE candidates
              while (iceCandidateQueue.current.length > 0) {
                await pc.addIceCandidate(iceCandidateQueue.current.shift());
              }
              const answer = await pc.createAnswer();
              await pc.setLocalDescription(answer);
              sendMessage({ type: 'answer', answer });
              console.log('[VideoCall] Sent answer');
              setCallState('calling');
            } catch (err) {
              console.error('[VideoCall] Error handling offer:', err);
              setError(`Failed to handle incoming call: ${err.message}`);
            }
            break;

          case 'answer':
            console.log('[VideoCall] Processing answer...');
            try {
              const pc = peerConnectionRef.current;
              if (!pc) { console.warn('[VideoCall] No PC for answer'); break; }
              await pc.setRemoteDescription(new RTCSessionDescription(msg.answer));
              while (iceCandidateQueue.current.length > 0) {
                await pc.addIceCandidate(iceCandidateQueue.current.shift());
              }
              console.log('[VideoCall] Remote description set from answer');
            } catch (err) {
              console.error('[VideoCall] Error handling answer:', err);
            }
            break;

          case 'ice-candidate':
            try {
              const pc = peerConnectionRef.current;
              if (pc && pc.remoteDescription) {
                await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
              } else {
                iceCandidateQueue.current.push(new RTCIceCandidate(msg.candidate));
              }
            } catch (err) {
              console.error('[VideoCall] Error handling ICE candidate:', err);
            }
            break;

          case 'call_ended':
            setCallState('ended');
            cleanupMedia();
            setTimeout(() => { setCallState('idle'); setError(null); }, 3000);
            break;

          case 'session_info':
            // handled by startCall promise — do nothing here
            break;

          case 'error':
            console.error('[VideoCall] Server error:', msg.message);
            setError(msg.message);
            break;

          default:
            console.log('[VideoCall] Unknown message:', msg.type);
        }
      } catch (err) {
        console.error('[VideoCall] Error processing WS message:', err);
      }
    };

    ws.onerror = () => {
      if (!cancelled) setError('WebSocket connection error');
    };

    ws.onclose = () => {
      console.log('[VideoCall] WebSocket closed');
      if (!cancelled) {
        setWsConnected(false);
        if (callStateRef.current === 'connected') {
          setError('Connection lost');
          cleanupMedia();
        }
      }
    };

    return () => {
      cancelled = true;
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, userId, userType]);

  const startCall = async () => {
    if (!sessionId) { setError('No session ID available'); return; }

    try {
      await setupPeerConnection();
      setCallState('calling');

      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        setError('Not connected to signaling server');
        setCallState('idle');
        return;
      }

      // Set pendingOffer BEFORE asking for session info, so if user-joined
      // arrives during the wait, the handler can send the offer immediately
      pendingOfferRef.current = true;

      // Ask server how many users are in the session
      const sessionInfo = await new Promise((resolve) => {
        const origHandler = ws.onmessage;
        ws.onmessage = async (event) => {
          const msg = JSON.parse(event.data);
          if (msg.type === 'session_info') {
            ws.onmessage = origHandler;
            resolve(msg);
          } else if (origHandler) {
            origHandler(event);
          }
        };
        ws.send(JSON.stringify({ type: 'get_session_info' }));
        setTimeout(() => { ws.onmessage = origHandler; resolve(null); }, 2000);
      });

      console.log('[VideoCall] Session info:', sessionInfo);
      const peerCount = sessionInfo?.user_count ?? 0;
      if (peerCount > 1) {
        // Patient already connected — send offer now
        console.log('[VideoCall] Peer already in session, sending offer');
        const offer = await peerConnectionRef.current.createOffer();
        await peerConnectionRef.current.setLocalDescription(offer);
        sendMessage({ type: 'offer', offer });
        pendingOfferRef.current = false;
      } else {
        console.log('[VideoCall] No peer yet, waiting for patient to join (pendingOffer=true)');
        // pendingOfferRef already set above
      }
    } catch (err) {
      console.error('[VideoCall] Error starting call:', err);
      setError(`Failed to start call: ${err.message}`);
      setCallState('idle');
    }
  };

  const endCall = async () => {
    sendMessage({ type: 'end_call' });
    if (sessionId) {
      try { await endLiveSession(sessionId); } catch (_) { /* already ended or error — continue cleanup */ }
    }
    cleanupMedia();
    setCallState('idle');
    onCallEnd();
  };

  const toggleMute = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMuted(!audioTrack.enabled);
      }
    }
  };

  // For debugging: print full device/track info to console
  const debugAudio = () => {
    const stream = localStreamRef.current;
    if (!stream) { console.log('[AudioDebug] No local stream yet'); return; }
    stream.getTracks().forEach(t => {
      const settings = t.getSettings();
      console.log(`[AudioDebug] Track: kind=${t.kind}, label=${t.label}, enabled=${t.enabled}`);
      console.log(`[AudioDebug]   deviceId=${settings.deviceId}, sampleRate=${settings.sampleRate}, channelCount=${settings.channelCount}`);
    });
    if (remoteVideoRef.current?.srcObject) {
      remoteVideoRef.current.srcObject.getTracks().forEach(t => {
        console.log(`[AudioDebug] Remote track: kind=${t.kind}, label=${t.label}, readyState=${t.readyState}`);
      });
    } else {
      console.log('[AudioDebug] No remote stream yet');
    }
  };

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoOff(!videoTrack.enabled);
      }
    }
  };

  return (
    <div className="video-call-container">
      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      {/* Video Display */}
      <div className="video-display">
        <div className="video-wrapper remote-video-wrapper">
          <video
            ref={remoteVideoRef}
            autoPlay
            playsInline
            className="remote-video"
          />
          {callState !== 'connected' && (
            <div className="video-placeholder">
              <span>Remote Video</span>
            </div>
          )}
        </div>

        <div className="video-wrapper local-video-wrapper">
          <video
            ref={localVideoRef}
            autoPlay
            playsInline
            muted
            className="local-video"
          />
          {callState === 'idle' && (
            <div className="video-placeholder">
              <span>Your Video</span>
            </div>
          )}
        </div>
      </div>

      {/* Call Controls */}
      <div className="call-controls">
        <div className="call-status">
          Status: <span className={`status-${callState}`}>{callState}</span>
          {wsConnected && callState === 'idle' && (
            <span style={{ marginLeft: 12, color: '#4caf50', fontSize: '0.9em' }}>
              ● Connected to session {sessionId}
              {userType === 'patient' && ' — waiting for therapist to start call'}
            </span>
          )}
          {!wsConnected && callState === 'idle' && (
            <span style={{ marginLeft: 12, color: '#ff9800', fontSize: '0.9em' }}>
              ○ Connecting...
            </span>
          )}
        </div>

        {callState === 'idle' && userType === 'therapist' && (
          <button className="start-call-btn" onClick={startCall}>
            Start Call
          </button>
        )}

        {(callState === 'connected' || callState === 'calling') && (
          <>
            {/* Audio level meter */}
            <div className="audio-meter" title="Your microphone level">
              <span style={{ fontSize: '0.75em', marginRight: 4 }}>🎤</span>
              <div className="audio-meter-bar">
                <div
                  className="audio-meter-fill"
                  style={{
                    width: `${audioLevel}%`,
                    backgroundColor: audioLevel > 70 ? '#4caf50' : audioLevel > 30 ? '#8bc34a' : '#ccc'
                  }}
                />
              </div>
            </div>

            <button 
              className={`control-btn ${isMuted ? 'active' : ''}`}
              onClick={toggleMute}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? '🔇' : '🎤'}
            </button>

            <button 
              className={`control-btn ${isVideoOff ? 'active' : ''}`}
              onClick={toggleVideo}
              title={isVideoOff ? 'Turn on camera' : 'Turn off camera'}
            >
              {isVideoOff ? '📹' : '📷'}
            </button>

            <button
              className="control-btn"
              onClick={() => setShowDevices(v => !v)}
              title="Device settings"
            >
              ⚙️
            </button>

            <button className="end-call-btn" onClick={endCall}>
              End Call
            </button>
          </>
        )}

        {/* Device selector panel — visible in idle OR during call */}
        {showDevices && (
          <div className="device-panel">
            <div className="device-row">
              <label>🎤 Microphone</label>
              <select
                value={selectedMic}
                onChange={e => callState === 'idle' ? setSelectedMic(e.target.value) : switchMic(e.target.value)}
              >
                {audioInputs.map(d => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label || `Microphone ${d.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="device-row">
              <label>📷 Camera</label>
              <select
                value={selectedCamera}
                onChange={e => callState === 'idle' ? setSelectedCamera(e.target.value) : switchCamera(e.target.value)}
              >
                {videoInputs.map(d => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label || `Camera ${d.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="device-row">
              <label>🔊 Speaker</label>
              <select
                value={selectedSpeaker}
                onChange={e => switchSpeaker(e.target.value)}
              >
                {audioOutputs.length > 0
                  ? audioOutputs.map(d => (
                      <option key={d.deviceId} value={d.deviceId}>
                        {d.label || `Speaker ${d.deviceId.slice(0, 8)}`}
                      </option>
                    ))
                  : <option value="">Default (browser-controlled)</option>
                }
              </select>
            </div>
            <button
              className="control-btn"
              style={{ marginTop: 8, width: '100%', fontSize: '0.8em' }}
              onClick={debugAudio}
            >
              Print track info to console
            </button>
          </div>
        )}

        {/* Show gear icon in idle too so user can pre-select devices */}
        {callState === 'idle' && (
          <button
            className="control-btn"
            onClick={() => setShowDevices(v => !v)}
            title="Select camera / microphone"
            style={{ marginLeft: 8 }}
          >
            ⚙️ Devices
          </button>
        )}
      </div>

      {/* Transcript panel — visible once session has entries */}
      {(transcript.length > 0 || isTranscribing) && (
        <div className="transcript-panel">
          <div className="transcript-header">
            <span className="transcript-title">
              📝 Session Transcript
              {isTranscribing && (
                <span className="recording-indicator"> ● Recording</span>
              )}
            </span>
            <div className="transcript-controls">
              <button
                className="control-btn transcript-toggle-btn"
                onClick={() => setShowTranscript(v => !v)}
                title={showTranscript ? 'Collapse transcript' : 'Expand transcript'}
              >
                {showTranscript ? '▲' : '▼'}
              </button>
              {transcript.length > 0 && (
                <button
                  className="control-btn transcript-clear-btn"
                  onClick={() => setTranscript([])}
                  title="Clear transcript"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {showTranscript && (
            <div className="transcript-entries">
              {transcript.length === 0 ? (
                <div className="transcript-empty">Waiting for speech…</div>
              ) : (
                transcript.map((entry, i) => (
                  <div key={i} className={`transcript-entry ${entry.speaker}`}>
                    <span className="transcript-speaker">{entry.speaker}</span>
                    <span className="transcript-text">{entry.text}</span>
                    <span className="transcript-time">
                      {entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VideoCall;
