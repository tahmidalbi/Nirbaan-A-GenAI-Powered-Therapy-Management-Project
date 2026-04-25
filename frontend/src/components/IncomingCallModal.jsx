import { useEffect, useRef, useState } from 'react';
import './IncomingCallModal.css';

const RING_TIMEOUT_S = 45;

/** Play a two-tone phone-style ringtone using Web Audio API */
function startRingtone() {
  let audioCtx;
  let stopped = false;
  let stopFn = null;

  // Delay creation to satisfy browsers that require a user gesture
  // (modal appearance counts as a user-triggered event in most cases)
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  } catch {
    return () => {};
  }

  const gainNode = audioCtx.createGain();
  gainNode.gain.setValueAtTime(0.18, audioCtx.currentTime);
  gainNode.connect(audioCtx.destination);

  // Schedule repeating ring: two quick beeps then a pause
  const beepDuration = 0.18;   // seconds per beep
  const beepGap = 0.10;        // gap between the two beeps
  const pauseDuration = 1.60;  // silent pause after each pair
  const freq1 = 480;
  const freq2 = 620;

  function scheduleRing(startAt) {
    if (stopped) return;

    [freq1, freq2].forEach((freq, i) => {
      const t = startAt + i * (beepDuration + beepGap);
      const osc = audioCtx.createOscillator();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, t);
      osc.connect(gainNode);
      osc.start(t);
      osc.stop(t + beepDuration);
    });

    const nextRing = startAt + 2 * (beepDuration + beepGap) + pauseDuration;
    const delay = (nextRing - audioCtx.currentTime) * 1000;
    const tid = setTimeout(() => scheduleRing(nextRing), Math.max(0, delay - 50));
    stopFn = () => clearTimeout(tid);
  }

  scheduleRing(audioCtx.currentTime + 0.05);

  return () => {
    stopped = true;
    if (stopFn) stopFn();
    gainNode.disconnect();
    audioCtx.close();
  };
}

const IncomingCallModal = ({ callerName, onAccept, onDecline }) => {
  const [timeLeft, setTimeLeft] = useState(RING_TIMEOUT_S);
  const intervalRef = useRef(null);
  const timeoutRef = useRef(null);
  const stopRingtoneRef = useRef(null);

  // Start ringtone on mount, stop on unmount
  useEffect(() => {
    stopRingtoneRef.current = startRingtone();
    return () => {
      if (stopRingtoneRef.current) stopRingtoneRef.current();
    };
  }, []);

  const handleAccept = () => {
    if (stopRingtoneRef.current) stopRingtoneRef.current();
    onAccept();
  };

  const handleDecline = () => {
    if (stopRingtoneRef.current) stopRingtoneRef.current();
    onDecline();
  };

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) { clearInterval(intervalRef.current); return 0; }
        return prev - 1;
      });
    }, 1000);

    timeoutRef.current = setTimeout(() => {
      handleDecline();
    }, RING_TIMEOUT_S * 1000);

    return () => {
      clearInterval(intervalRef.current);
      clearTimeout(timeoutRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
          <button className="icm-decline" onClick={handleDecline}>
            <span className="icm-icon">✕</span> Decline
          </button>
          <button className="icm-accept" onClick={handleAccept}>
            <span className="icm-icon">📹</span> Accept
          </button>
        </div>
      </div>
    </div>
  );
};

export default IncomingCallModal;
