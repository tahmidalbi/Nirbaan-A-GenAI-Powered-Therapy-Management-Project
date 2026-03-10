import { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './TranscriptDisplay.css';

const TranscriptDisplay = ({ 
  transcripts = [],
  autoScroll = true,
  maxHeight = '500px',
  showClear = false,
  onClear = null
}) => {
  const transcriptEndRef = useRef(null);
  const containerRef = useRef(null);

  // Auto-scroll to bottom when new transcript arrives
  useEffect(() => {
    if (autoScroll && transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'nearest'
      });
    }
  }, [transcripts, autoScroll]);

  const formatTime = (timestamp) => {
    if (!timestamp) return '00:00:00';
    
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    
    return `${hours}:${minutes}:${seconds}`;
  };

  const getSpeakerClass = (speaker) => {
    return speaker.toLowerCase() === 'therapist' ? 'therapist' : 'patient';
  };

  const handleClear = () => {
    if (onClear) {
      onClear();
    }
  };

  if (transcripts.length === 0) {
    return (
      <div className="transcript-display-container" style={{ maxHeight }}>
        <div className="transcript-empty">
          <span className="empty-icon">📝</span>
          <p>No transcripts yet. Start recording to see transcripts appear here in real-time.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="transcript-display-container" style={{ maxHeight }}>
      <div className="transcript-header">
        <h3>Live Transcript</h3>
        {showClear && onClear && (
          <button className="clear-transcript-btn" onClick={handleClear}>
            Clear
          </button>
        )}
      </div>

      <div className="transcript-content" ref={containerRef}>
        {transcripts.map((transcript, index) => (
          <div 
            key={transcript.id || index} 
            className={`transcript-entry ${getSpeakerClass(transcript.speaker)}`}
          >
            <div className="transcript-time">
              [{formatTime(transcript.timestamp)}]
            </div>
            <div className="transcript-speaker">
              {transcript.speaker}:
            </div>
            <div className="transcript-text">
              {transcript.text}
            </div>
          </div>
        ))}
        <div ref={transcriptEndRef} />
      </div>
    </div>
  );
};

TranscriptDisplay.propTypes = {
  transcripts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      speaker: PropTypes.string.isRequired,
      text: PropTypes.string.isRequired,
      timestamp: PropTypes.string.isRequired,
    })
  ),
  autoScroll: PropTypes.bool,
  maxHeight: PropTypes.string,
  showClear: PropTypes.bool,
  onClear: PropTypes.func,
};

export default TranscriptDisplay;
