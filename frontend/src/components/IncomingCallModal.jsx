import { useEffect, useRef, useState } from 'react';
import './IncomingCallModal.css';

const RING_TIMEOUT_S = 45;

const IncomingCallModal = ({ callerName, onAccept, onDecline }) => {
  const [timeLeft, setTimeLeft] = useState(RING_TIMEOUT_S);
  const intervalRef = useRef(null);
  const timeoutRef = useRef(null);

  // ── Ringtone via Web Audio API (no audio file needed) ──────────────────────
  useEffect(() => {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;

    const ctx = new AudioCtx();

    const scheduleRing = (startTime) => {
      // Classic dual-tone phone ring: 480 Hz + 620 Hz
      [480, 620].forEach((freq) => {
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = freq;
        // Fade in / sustain / fade out to avoid clicks
        gain.gain.setValueAtTime(0, startTime);
        gain.gain.linearRampToValueAtTime(0.22, startTime + 0.05);
        gain.gain.setValueAtTime(0.22, startTime + 0.9);
        gain.gain.linearRampToValueAtTime(0, startTime + 1.0);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + 1.0);
      });
    };

    // Pre-schedule a ring every 3 s for the full timeout duration
    const now = ctx.currentTime;
    for (let t = 0; t < RING_TIMEOUT_S; t += 3) {
      scheduleRing(now + t);
    }

    return () => {
      ctx.close();
    };
  }, []);
  // ───────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) { clearInterval(intervalRef.current); return 0; }
        return prev - 1;
      });
    }, 1000);

    timeoutRef.current = setTimeout(() => {
      onDecline();
    }, RING_TIMEOUT_S * 1000);

    return () => {
      clearInterval(intervalRef.current);
      clearTimeout(timeoutRef.current);
    };
  }, [onDecline]);

  return (
    <div className="icm-overlay">
      <div className="icm-modal">
        <div className="icm-pulse-ring" />
        <div className="icm-avatar">
          {(callerName || 'T').slice(0, 1).toUpperCase()}
        </div>
        <p className="icm-caller-name">{callerName || 'Your Therapist'}</p>
        <p className="icm-subtitle">Incoming video call</p>
        <p className="icm-timeout">Auto-decline in {timeLeft}s</p>
        <div className="icm-actions">
          <button className="icm-decline" onClick={onDecline}>
            <span className="icm-icon">✕</span> Decline
          </button>
          <button className="icm-accept" onClick={onAccept}>
            <span className="icm-icon">📹</span> Accept
          </button>
        </div>
      </div>
    </div>
  );
};

export default IncomingCallModal;
