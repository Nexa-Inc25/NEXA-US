import React, { useState, useEffect } from 'react';
import { FileText, Trash2, RefreshCw, Upload, CheckCircle, AlertCircle, Database } from 'lucide-react';
import './SpecLibrary.css';

function SpecLibrary() {
  const [library, setLibrary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);

  const ANALYZER_URL = process.env.REACT_APP_DOC_ANALYZER_URL || 'https://nexa-doc-analyzer-oct2025.onrender.com';

  useEffect(() => {
    fetchLibrary();
  }, []);

  const fetchLibrary = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${ANALYZER_URL}/spec-library`);
      if (response.ok) {
        const data = await response.json();
        setLibrary(data);
      } else {
        throw new Error('Failed to fetch library');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      const response = await fetch(`${ANALYZER_URL}/upload-spec-book`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        setUploadFile(null);
        fetchLibrary();
      } else {
        const data = await response.json();
        setError(data.detail || 'Upload failed');
      }
    } catch (err) {
      setError('Upload error: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const mb = bytes / (1024 * 1024);
    return mb.toFixed(2) + ' MB';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="spec-library">
        <div className="loading-state">
          <RefreshCw className="spinning" size={40} />
          <p>Loading spec library...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="spec-library">
      <div className="library-header">
        <div className="header-title">
          <Database size={32} />
          <div>
            <h1>Specification Library</h1>
            <p>Manage PG&E specs that the AI has learned</p>
          </div>
        </div>
        <button onClick={fetchLibrary} className="btn btn-secondary">
          <RefreshCw size={20} /> Refresh
        </button>
      </div>

      <div className="library-stats">
        <div className="stat-card">
          <FileText size={24} />
          <div>
            <h3>Total Specs</h3>
            <p className="stat-value">{library?.total_files || 0}</p>
          </div>
        </div>
        <div className="stat-card">
          <Database size={24} />
          <div>
            <h3>Total Chunks</h3>
            <p className="stat-value">{library?.total_chunks || 0}</p>
          </div>
        </div>
        <div className="stat-card">
          <CheckCircle size={24} className="success" />
          <div>
            <h3>Status</h3>
            <p className="stat-value">{library?.total_files > 0 ? 'Ready' : 'Empty'}</p>
          </div>
        </div>
      </div>

      <div className="upload-section">
        <h2><Upload size={24} /> Upload New Spec</h2>
        <div className="upload-controls">
          <input
            type="file"
            id="spec-upload"
            accept=".pdf"
            onChange={(e) => setUploadFile(e.target.files[0])}
            disabled={uploading}
          />
          <label htmlFor="spec-upload" className="file-label">
            {uploadFile ? uploadFile.name : 'Choose PDF'}
          </label>
          <button onClick={handleUpload} disabled={!uploadFile || uploading} className="btn btn-primary">
            {uploading ? 'Uploading...' : 'Upload Spec'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} /> {error}
        </div>
      )}

      <div className="specs-table-container">
        <h2>Uploaded Specifications</h2>
        {library?.files && library.files.length > 0 ? (
          <table className="specs-table">
            <thead>
              <tr>
                <th>File Name</th>
                <th>Chunks</th>
                <th>Upload Date</th>
              </tr>
            </thead>
            <tbody>
              {library.files.map((file, idx) => (
                <tr key={idx}>
                  <td>
                    <div className="file-name">
                      <FileText size={18} />
                      {file.filename || 'Unknown'}
                    </div>
                  </td>
                  <td>{file.chunk_count || 0}</td>
                  <td>{formatDate(file.upload_time)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-state">
            <FileText size={64} />
            <h3>No Specs Uploaded Yet</h3>
            <p>Upload PG&E specification PDFs to build the AI knowledge base</p>
          </div>
        )}
      </div>

      <div className="recommended-specs">
        <h2>Recommended PG&E Specs</h2>
        <div className="spec-checklist">
          <div className="spec-item">
            <CheckCircle size={20} className={library?.files?.some(f => f.filename?.includes('022178')) ? 'success' : 'pending'} />
            <div>
              <strong>022178</strong> - Pole Line Guys
              <span className="status">{library?.files?.some(f => f.filename?.includes('022178')) ? '✓ Uploaded' : 'Pending'}</span>
            </div>
          </div>
          <div className="spec-item">
            <CheckCircle size={20} className={library?.files?.some(f => f.filename?.includes('092813')) ? 'success' : 'pending'} />
            <div>
              <strong>092813</strong> - FuseSaver Requirements
              <span className="status">{library?.files?.some(f => f.filename?.includes('092813')) ? '✓ Uploaded' : 'Pending'}</span>
            </div>
          </div>
          <div className="spec-item">
            <CheckCircle size={20} className={library?.files?.some(f => f.filename?.includes('094672')) ? 'success' : 'pending'} />
            <div>
              <strong>094672</strong> - TripSaver II
              <span className="status">{library?.files?.some(f => f.filename?.includes('094672')) ? '✓ Uploaded' : 'Pending'}</span>
            </div>
          </div>
          <div className="spec-item">
            <CheckCircle size={20} className={library?.files?.some(f => f.filename?.includes('094669')) ? 'success' : 'pending'} />
            <div>
              <strong>094669</strong> - Line Reclosers
              <span className="status">{library?.files?.some(f => f.filename?.includes('094669')) ? '✓ Uploaded' : 'Pending'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SpecLibrary;
