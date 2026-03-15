import { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './TranscriptDisplay.css';

const TranscriptDisplay = ({ 
  transcripts = [],
  autoScroll = true,
  maxHeight = '500px',
  showClear = false,
  onClear = null,
  isLive = false,
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
    return speaker?.toLowerCase() === 'therapist' ? 'therapist' : 'patient';
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence == null) return null;
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
  };

  const handleClear = () => {
    if (onClear) {
      onClear();
    }
  };

  if (transcripts.length === 0) {
    return (
      <div className="transcript-display-container" style={{ maxHeight }}>
        <div className="transcript-display-header">
          <h3>Live Transcript</h3>
          {isLive && <span className="live-badge">● LIVE</span>}
        </div>
        <div className="transcript-empty">
          <span className="empty-icon">📝</span>
          <p>No transcripts yet. Transcripts will appear here in real-time once the call starts.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="transcript-display-container" style={{ maxHeight }}>
      <div className="transcript-display-header">
        <h3>Live Transcript</h3>
        <div className="transcript-header-actions">
          {isLive && <span className="live-badge">● LIVE</span>}
          {showClear && onClear && (
            <button className="clear-transcript-btn" onClick={handleClear}>
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="transcript-content" ref={containerRef}>
        {transcripts.map((transcript, index) => {
          const conf = getConfidenceLabel(transcript.confidence);
          return (
            <div 
              key={transcript.id || index} 
              className={`transcript-entry ${getSpeakerClass(transcript.speaker)}${transcript.is_partial ? ' partial' : ''}`}
            >
              <div className="transcript-meta-row">
                <span className="transcript-time">
                  [{formatTime(transcript.timestamp)}]
                </span>
                <span className="transcript-speaker">
                  {transcript.speaker}:
                </span>
                {conf && (
                  <span className={`confidence-badge confidence-${conf}`}>
                    {conf}
                  </span>
                )}
              </div>
              <div className="transcript-text">
                {transcript.text}
              </div>
            </div>
          );
        })}
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
      timestamp: PropTypes.string,
      confidence: PropTypes.number,
      is_partial: PropTypes.bool,
    })
  ),
  autoScroll: PropTypes.bool,
  maxHeight: PropTypes.string,
  showClear: PropTypes.bool,
  onClear: PropTypes.func,
  isLive: PropTypes.bool,
};

export default TranscriptDisplay;
