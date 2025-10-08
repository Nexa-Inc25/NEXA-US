import React, { useState, useEffect } from 'react';
import { FileText, Trash2, RefreshCw, Upload, CheckCircle, AlertCircle, Database } from 'lucide-react';
import './SpecLibrary.css';

function SpecLibrary() {
  const [library, setLibrary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadFiles, setUploadFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });

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
        console.log('Library data received:', data); // Debug log
        setLibrary(data);
      } else {
        const errorText = await response.text();
        throw new Error(`Failed to fetch library: ${response.status} - ${errorText}`);
      }
    } catch (err) {
      setError(err.message);
      console.error('Library fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!uploadFiles || uploadFiles.length === 0) return;
    
    setUploading(true);
    setError(null);
    setUploadProgress({ current: 0, total: uploadFiles.length });
    
    const results = [];
    
    for (let i = 0; i < uploadFiles.length; i++) {
      const file = uploadFiles[i];
      setUploadProgress({ current: i + 1, total: uploadFiles.length });
      
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch(`${ANALYZER_URL}/learn-spec/`, {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const data = await response.json();
          results.push({ file: file.name, success: true, chunks: data.chunks_learned });
        } else {
          let errorMsg = `Status: ${response.status}`;
          try {
            const data = await response.json();
            errorMsg = data.detail || data.message || errorMsg;
          } catch (e) {
            const text = await response.text();
            errorMsg = text || errorMsg;
          }
          console.error(`Upload failed for ${file.name}:`, errorMsg);
          results.push({ file: file.name, success: false, error: errorMsg });
        }
      } catch (err) {
        results.push({ file: file.name, success: false, error: err.message });
      }
    }
    
    // Show summary
    const successful = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success).length;
    
    if (failed > 0) {
      setError(`Uploaded ${successful} files successfully, ${failed} failed`);
    }
    
    setUploadFiles([]);
    setUploadProgress({ current: 0, total: 0 });
    setUploading(false);
    
    // Wait a moment for the server to finish processing, then refresh
    setTimeout(() => {
      fetchLibrary();
    }, 1000);
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
        <div className="header-actions">
          <button onClick={fetchLibrary} className="btn btn-secondary">
            <RefreshCw size={20} /> Refresh
          </button>
          <button onClick={async () => {
            if (window.confirm('This will delete all uploaded specs. Are you sure?')) {
              try {
                const response = await fetch(`${ANALYZER_URL}/manage-specs`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ operation: 'clear' })
                });
                if (response.ok) {
                  alert('Library cleared successfully');
                  fetchLibrary();
                } else {
                  alert('Failed to clear library');
                }
              } catch (err) {
                alert('Error: ' + err.message);
              }
            }
          }} className="btn btn-danger">
            <Trash2 size={20} /> Clear All
          </button>
        </div>
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
        <h2><Upload size={24} /> Upload Specs (Multiple Files)</h2>
        <div className="upload-controls">
          <input
            type="file"
            id="spec-upload"
            accept=".pdf"
            multiple
            onChange={(e) => setUploadFiles(Array.from(e.target.files))}
            disabled={uploading}
          />
          <label htmlFor="spec-upload" className="file-label">
            {uploadFiles.length > 0 ? `${uploadFiles.length} file(s) selected` : 'Choose PDF Files'}
          </label>
          <button onClick={handleUpload} disabled={uploadFiles.length === 0 || uploading} className="btn btn-primary">
            {uploading ? `Uploading ${uploadProgress.current}/${uploadProgress.total}...` : `Upload ${uploadFiles.length || ''} Spec${uploadFiles.length !== 1 ? 's' : ''}`}
          </button>
        </div>
        {uploadFiles.length > 0 && !uploading && (
          <div className="selected-files">
            <p><strong>Selected files:</strong></p>
            <ul>
              {uploadFiles.map((file, idx) => (
                <li key={idx}>{file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</li>
              ))}
            </ul>
          </div>
        )}
        {uploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
              />
            </div>
            <p>Uploading {uploadProgress.current} of {uploadProgress.total} files...</p>
          </div>
        )}
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
