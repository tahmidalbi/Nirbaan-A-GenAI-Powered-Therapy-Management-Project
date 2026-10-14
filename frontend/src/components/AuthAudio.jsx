import { useEffect, useState } from 'react';
import { fetchAudioBlob } from '../api/imaginal-generator.api';

// <audio src> cannot send the login token, so the file is fetched with it and played from a blob URL.
const AuthAudio = ({ scriptId, className }) => {
  const [src, setSrc] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;
    setSrc(null);
    setFailed(false);

    fetchAudioBlob(scriptId)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [scriptId]);

  if (failed) return <p className={className}>Audio is not available.</p>;
  if (!src) return <p className={className}>Loading audio…</p>;
  // eslint-disable-next-line jsx-a11y/media-has-caption
  return <audio controls src={src} className={className} />;
};

export default AuthAudio;
