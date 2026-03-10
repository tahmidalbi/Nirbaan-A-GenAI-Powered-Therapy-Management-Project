import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import './VideoCall.css';

const VideoCall = ({ 
  userId: userIdProp, 
  userType: userTypeProp, // "therapist" or "patient"
  targetUserId = null, // For therapist to call specific patient
  sessionId = null, // Therapy session ID
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

  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const wsRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const localStreamRef = useRef(null);
  const iceCandidateQueue = useRef([]);
  const callStateRef = useRef('idle');
  const pendingOfferRef = useRef(false);

  // Keep callStateRef in sync
  callStateRef.current = callState;

  // Log identity on mount
  useEffect(() => {
    console.log(`[VideoCall] Mounted — sessionId=${sessionId}, userId=${userId}, userType=${userType}`);
  }, [sessionId, userId, userType]);

  const cleanupMedia = useCallback(() => {
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
  }, []);

  const sendMessage = useCallback((msg) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
      console.log(`[VideoCall] Sent: ${msg.type}`);
    } else {
      console.warn(`[VideoCall] WS not open, cannot send: ${msg.type}`);
    }
  }, []);

  const setupPeerConnection = useCallback(async () => {
    console.log('[VideoCall] Setting up peer connection, requesting camera/mic...');
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    console.log('[VideoCall] Got local media stream');
    localStreamRef.current = stream;
    if (localVideoRef.current) localVideoRef.current.srcObject = stream;

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
    const wsUrl = `ws://localhost:8000/api/therapy-sessions/ws/signaling/${sessionId}`;
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

  const endCall = () => {
    sendMessage({ type: 'end_call' });
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

            <button className="end-call-btn" onClick={endCall}>
              End Call
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default VideoCall;
