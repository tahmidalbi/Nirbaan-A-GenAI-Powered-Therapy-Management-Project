import { useState, useEffect } from 'react';
import { listPatientResources, getPatientResourceDownloadUrl } from '../api/resource.api';
import './PatientResourceLibrary.css';

const FILE_ICON = (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const LINK_ICON = (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);

const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return '—';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Math.round((bytes / Math.pow(k, i)) * 10) / 10} ${sizes[i]}`;
};

const PatientResourceLibrary = () => {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(null); // resource id being downloaded

  useEffect(() => {
    listPatientResources()
      .then(setResources)
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load resources'))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async (resource) => {
    setDownloading(resource.id);
    try {
      const { download_url } = await getPatientResourceDownloadUrl(resource.id);
      // Open in new tab so browser handles download
      window.open(download_url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to get download link');
    } finally {
      setDownloading(null);
    }
  };

  const handleOpenLink = (url) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  if (loading) {
    return (
      <div className="prl-wrap">
        <div className="prl-loading">
          <div className="prl-spinner" />
          <p>Loading resources…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="prl-wrap">
      <div className="prl-header">
        <h2 className="prl-title">Resource Library</h2>
        <p className="prl-subtitle">
          Books, guides, and links shared by your therapist
        </p>
      </div>

      {error && <div className="prl-error">{error}</div>}

      {!error && resources.length === 0 && (
        <div className="prl-empty">
          <p>Your therapist hasn't shared any resources yet. Check back later.</p>
        </div>
      )}

      <div className="prl-grid">
        {resources.map((r) => {
          const isLink = !!r.source_url;
          const isDownloading = downloading === r.id;

          return (
            <div key={r.id} className={`prl-card ${isLink ? 'prl-card--link' : 'prl-card--file'}`}>
              <div className="prl-card-icon">
                {isLink ? LINK_ICON : FILE_ICON}
              </div>

              <div className="prl-card-body">
                <h3 className="prl-card-title">{r.title}</h3>
                <div className="prl-card-meta">
                  {isLink ? (
                    <span className="prl-meta-tag prl-meta-tag--link">Web Link</span>
                  ) : (
                    <>
                      <span className="prl-meta-tag prl-meta-tag--file">
                        {r.file_type.toUpperCase()}
                      </span>
                      <span className="prl-meta-size">{formatBytes(r.size_bytes)}</span>
                    </>
                  )}
                  <span className="prl-meta-date">
                    {new Date(r.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </span>
                </div>
              </div>

              <div className="prl-card-action">
                {isLink ? (
                  <button
                    className="prl-btn prl-btn--visit"
                    onClick={() => handleOpenLink(r.source_url)}
                  >
                    Visit Link ↗
                  </button>
                ) : (
                  <button
                    className="prl-btn prl-btn--download"
                    onClick={() => handleDownload(r)}
                    disabled={isDownloading}
                  >
                    {isDownloading ? 'Getting link…' : 'Download ↓'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PatientResourceLibrary;
