import { useState, useRef, useEffect } from 'react';
import './MindfulnessPlayer.css';

const TRACKS = [
  {
    id: 1,
    title: 'Guided Meditation',
    subtitle: 'Relaxation & breath awareness',
    src: '/mindfulness/track-1.m4a',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="28" height="28">
        <circle cx="12" cy="12" r="10" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8 12c0-2.2 1.8-4 4-4s4 1.8 4 4-1.8 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="12" cy="12" r="1.5" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 2,
    title: 'Deep Relaxation',
    subtitle: 'Body scan & calming exercise',
    src: '/mindfulness/track-2.m4a',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="28" height="28">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 6v6l4 2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

function formatTime(secs) {
  if (!secs || isNaN(secs)) return '0:00';
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function MindfulnessPlayer() {
  const [activeId, setActiveId] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef(null);

  const activeTrack = TRACKS.find((t) => t.id === activeId);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onDurationChange = () => setDuration(audio.duration);
    const onEnded = () => { setPlaying(false); setCurrentTime(0); };
    const onCanPlay = () => setLoading(false);
    const onWaiting = () => setLoading(true);

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('durationchange', onDurationChange);
    audio.addEventListener('loadedmetadata', onDurationChange);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('canplay', onCanPlay);
    audio.addEventListener('waiting', onWaiting);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('durationchange', onDurationChange);
      audio.removeEventListener('loadedmetadata', onDurationChange);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('canplay', onCanPlay);
      audio.removeEventListener('waiting', onWaiting);
    };
  }, [activeId]);

  const selectTrack = (track) => {
    if (activeId === track.id) {
      togglePlay();
      return;
    }
    const audio = audioRef.current;
    audio.pause();
    setCurrentTime(0);
    setDuration(0);
    setLoading(true);
    setActiveId(track.id);
    audio.src = track.src;
    audio.load();
    audio.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
  };

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!activeId) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
    }
  };

  const handleSeek = (e) => {
    const audio = audioRef.current;
    if (!duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    audio.currentTime = ratio * duration;
  };

  const progress = duration ? (currentTime / duration) * 100 : 0;

  return (
    <div className="mfp-root">
      <audio ref={audioRef} preload="none" />

      <div className="mfp-header">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="22" height="22">
          <path d="M9 18V5l12-2v13" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="6" cy="18" r="3" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="18" cy="16" r="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>Mindfulness Audio</span>
      </div>

      <ul className="mfp-list">
        {TRACKS.map((track) => {
          const isActive = activeId === track.id;
          return (
            <li
              key={track.id}
              className={`mfp-item ${isActive ? 'mfp-item--active' : ''}`}
              onClick={() => selectTrack(track)}
            >
              <div className="mfp-item-icon">
                {track.icon}
              </div>

              <div className="mfp-item-info">
                <span className="mfp-item-title">{track.title}</span>
                <span className="mfp-item-sub">{track.subtitle}</span>
              </div>

              <div className="mfp-item-right">
                {isActive ? (
                  <button
                    className="mfp-play-btn mfp-play-btn--active"
                    onClick={(e) => { e.stopPropagation(); togglePlay(); }}
                    aria-label={playing ? 'Pause' : 'Play'}
                  >
                    {loading ? (
                      <span className="mfp-spinner" />
                    ) : playing ? (
                      <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                        <rect x="6" y="4" width="4" height="16" rx="1" />
                        <rect x="14" y="4" width="4" height="16" rx="1" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                        <path d="M5 3l14 9-14 9V3z" />
                      </svg>
                    )}
                  </button>
                ) : (
                  <button className="mfp-play-btn" aria-label="Play">
                    <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                      <path d="M5 3l14 9-14 9V3z" />
                    </svg>
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {activeTrack && (
        <div className="mfp-player">
          <div className="mfp-player-track">
            <span className="mfp-player-title">{activeTrack.title}</span>
            <div className="mfp-player-times">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          <div
            className="mfp-progress-bar"
            onClick={handleSeek}
            role="progressbar"
            aria-valuenow={Math.round(progress)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="mfp-progress-track">
              <div className="mfp-progress-fill" style={{ width: `${progress}%` }} />
              <div className="mfp-progress-thumb" style={{ left: `${progress}%` }} />
            </div>
          </div>

          <div className="mfp-player-controls">
            <button
              className="mfp-ctrl-btn mfp-ctrl-btn--skip"
              onClick={() => { if (audioRef.current) audioRef.current.currentTime = Math.max(0, currentTime - 15); }}
              title="Back 15s"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                <path d="M1 4v6h6" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M3.51 15a9 9 0 1 0 .49-3.5" strokeLinecap="round" strokeLinejoin="round" />
                <text x="9" y="14" fontSize="6" fill="currentColor" stroke="none" fontFamily="serif">15</text>
              </svg>
            </button>

            <button
              className="mfp-ctrl-btn mfp-ctrl-btn--main"
              onClick={togglePlay}
              aria-label={playing ? 'Pause' : 'Play'}
            >
              {loading ? (
                <span className="mfp-spinner mfp-spinner--lg" />
              ) : playing ? (
                <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
                  <rect x="6" y="4" width="4" height="16" rx="1" />
                  <rect x="14" y="4" width="4" height="16" rx="1" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
                  <path d="M5 3l14 9-14 9V3z" />
                </svg>
              )}
            </button>

            <button
              className="mfp-ctrl-btn mfp-ctrl-btn--skip"
              onClick={() => { if (audioRef.current) audioRef.current.currentTime = Math.min(duration, currentTime + 15); }}
              title="Forward 15s"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                <path d="M23 4v6h-6" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M20.49 15a9 9 0 1 1-.49-3.5" strokeLinecap="round" strokeLinejoin="round" />
                <text x="9" y="14" fontSize="6" fill="currentColor" stroke="none" fontFamily="serif">15</text>
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
