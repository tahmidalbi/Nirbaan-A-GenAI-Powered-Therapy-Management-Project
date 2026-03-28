import { useEffect, useRef, useState } from 'react';
import './IncomingCallModal.css';

const RING_TIMEOUT_S = 45;

const IncomingCallModal = ({ callerName, onAccept, onDecline }) => {
  const [timeLeft, setTimeLeft] = useState(RING_TIMEOUT_S);
  const intervalRef = useRef(null);
  const timeoutRef = useRef(null);

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
