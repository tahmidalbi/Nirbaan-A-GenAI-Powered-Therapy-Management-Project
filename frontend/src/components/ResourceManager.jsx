import { useState, useEffect } from 'react';
import { uploadResource, listResources, deleteResource, uploadFromUrl } from '../api/resource.api';
import './ResourceManager.css';

const ResourceManager = () => {
  const [resources, setResources] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [title, setTitle] = useState('');
  const [uploadMode, setUploadMode] = useState('file'); // 'file' or 'url'
  const [url, setUrl] = useState('');
  const [resourceType, setResourceType] = useState('webpage');

  useEffect(() => {
    fetchResources();
  }, []);

  const fetchResources = async () => {
    try {
      setLoading(true);
      const data = await listResources();
      setResources(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      if (!title) {
        // Auto-fill title from filename
        setTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile || !title) return;

    try {
      setUploading(true);
      setError('');
      await uploadResource(selectedFile, title);
      
      // Clear form
      setSelectedFile(null);
      setTitle('');
      document.getElementById('file-input').value = '';
      
      // Refresh list
      await fetchResources();
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  };

  const handleUrlUpload = async (e) => {
    e.preventDefault();
    if (!url || !title) return;

    try {
      setUploading(true);
      setError('');
      await uploadFromUrl(url, title, resourceType);
      
      // Clear form
      setUrl('');
      setTitle('');
      setResourceType('webpage');
      
      // Refresh list
      await fetchResources();
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (resourceId) => {
    if (!confirm('Are you sure you want to delete this resource?')) return;

    try {
      await deleteResource(resourceId);
      await fetchResources();
    } catch (err) {
      setError(err);
    }
  };

  const getStatusBadgeClass = (status) => {
    const classes = {
      ready: 'status-ready',
      processing: 'status-processing',
      failed: 'status-failed',
      uploaded: 'status-uploaded',
    };
    return classes[status] || 'status-default';
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="resource-manager">
      <div className="upload-section">
        <h3>Add Knowledge Base Resource</h3>
        {error && <div className="error-banner">{error}</div>}
        
        <div className="upload-tabs">
          <button 
            className={`tab-btn ${uploadMode === 'file' ? 'active' : ''}`}
            onClick={() => setUploadMode('file')}
          >
            Upload File
          </button>
          <button 
            className={`tab-btn ${uploadMode === 'url' ? 'active' : ''}`}
            onClick={() => setUploadMode('url')}
          >
            Add Web Link
          </button>
        </div>

        {uploadMode === 'file' ? (
          <form onSubmit={handleUpload} className="upload-form">
            <div className="form-group">
              <label htmlFor="title">Document Title</label>
              <input
                type="text"
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., ERP Treatment Protocol"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="file-input">Select File (PDF or TXT)</label>
              <input
                type="file"
                id="file-input"
                accept=".pdf,.txt"
                onChange={handleFileSelect}
                required
              />
              {selectedFile && (
                <div className="file-info">
                  Selected: {selectedFile.name} ({formatBytes(selectedFile.size)})
                </div>
              )}
            </div>

            <button type="submit" disabled={uploading || !selectedFile || !title} className="upload-btn">
              {uploading ? 'Processing...' : 'Upload & Process'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleUrlUpload} className="upload-form">
            <div className="form-group">
              <label htmlFor="url-title">Resource Title</label>
              <input
                type="text"
                id="url-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., OCD Treatment Guidelines Article"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="url-input">Web URL</label>
              <input
                type="url"
                id="url-input"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/article"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="resource-type">Resource Type</label>
              <select
                id="resource-type"
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value)}
              >
                <option value="webpage">Webpage</option>
                <option value="blog">Blog Post</option>
                <option value="article">Article</option>
              </select>
            </div>

            <button type="submit" disabled={uploading || !url || !title} className="upload-btn">
              {uploading ? 'Fetching & Processing...' : 'Add & Process'}
            </button>
          </form>
        )}
      </div>

      <div className="resources-list">
        <h3>Your Knowledge Base ({resources.length})</h3>
        
        {loading ? (
          <div className="loading">Loading resources...</div>
        ) : resources.length === 0 ? (
          <div className="empty-state">
            <p>No documents uploaded yet. Upload your first knowledge base document above.</p>
          </div>
        ) : (
          <div className="resources-grid">
            {resources.map((resource) => (
              <div key={resource.id} className="resource-card">
                <div className="resource-header">
                  <h4>{resource.title}</h4>
                  <span className={`status-badge ${getStatusBadgeClass(resource.status)}`}>
                    {resource.status}
                  </span>
                </div>
                
                <div className="resource-meta">
                  <p><strong>File:</strong> {resource.original_filename}</p>
                  <p><strong>Type:</strong> {resource.file_type.toUpperCase()}</p>
                  <p><strong>Size:</strong> {formatBytes(resource.size_bytes)}</p>
                  {resource.total_pages && (
                    <p><strong>Pages:</strong> {resource.total_pages}</p>
                  )}
                  {resource.total_chunks && (
                    <p><strong>Chunks:</strong> {resource.total_chunks}</p>
                  )}
                  <p><strong>Uploaded:</strong> {new Date(resource.created_at).toLocaleDateString()}</p>
                </div>

                {resource.error_message && (
                  <div className="error-message">
                    <strong>Error:</strong> {resource.error_message}
                  </div>
                )}

                <div className="resource-actions">
                  <button onClick={() => handleDelete(resource.id)} className="delete-btn">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ResourceManager;