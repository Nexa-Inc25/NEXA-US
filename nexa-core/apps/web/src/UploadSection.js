import React, { useState } from 'react';
import { FileCheck, Upload, AlertCircle, CheckCircle } from 'lucide-react';

function UploadSection() {
  const [specFile, setSpecFile] = useState(null);
  const [auditFile, setAuditFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const ANALYZER_URL = process.env.REACT_APP_DOC_ANALYZER_URL || 'https://nexa-doc-analyzer-oct2025.onrender.com';

  const handleSpecUpload = async () => {
    if (!specFile) return;
    
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', specFile);

    try {
      const response = await fetch(`${ANALYZER_URL}/learn-spec/`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      if (response.ok) {
        setResults({ type: 'spec', data });
        setSpecFile(null);
      } else {
        setError(data.detail || 'Upload failed');
      }
    } catch (err) {
      setError('Failed to upload spec: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleAuditAnalysis = async () => {
    if (!auditFile) return;
    
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', auditFile);

    try {
      const response = await fetch(`${ANALYZER_URL}/analyze-audit/`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      if (response.ok) {
        setResults({ type: 'audit', data });
        setAuditFile(null);
      } else {
        setError(data.detail || 'Analysis failed');
      }
    } catch (err) {
      setError('Failed to analyze audit: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container">
      <h2>Document Upload & Analysis</h2>
      
      {/* Spec Upload */}
      <div className="upload-card">
        <div className="upload-header">
          <FileCheck size={24} />
          <h3>Upload Specification</h3>
        </div>
        <p>Upload PG&E spec PDFs for the AI to learn compliance standards</p>
        <div className="upload-controls">
          <input
            type="file"
            id="spec-upload"
            accept=".pdf"
            onChange={(e) => setSpecFile(e.target.files[0])}
            disabled={uploading}
          />
          <label htmlFor="spec-upload" className="file-label">
            <Upload size={20} />
            {specFile ? specFile.name : 'Choose Spec PDF'}
          </label>
          <button 
            onClick={handleSpecUpload}
            disabled={!specFile || uploading}
            className="btn btn-primary"
          >
            {uploading ? 'Uploading...' : 'Upload Spec'}
          </button>
        </div>
      </div>

      {/* Audit Analysis */}
      <div className="upload-card">
        <div className="upload-header">
          <AlertCircle size={24} />
          <h3>Analyze Audit</h3>
        </div>
        <p>Upload QA audit documents to check for repealable infractions</p>
        <div className="upload-controls">
          <input
            type="file"
            id="audit-upload"
            accept=".pdf"
            onChange={(e) => setAuditFile(e.target.files[0])}
            disabled={uploading}
          />
          <label htmlFor="audit-upload" className="file-label">
            <Upload size={20} />
            {auditFile ? auditFile.name : 'Choose Audit PDF'}
          </label>
          <button 
            onClick={handleAuditAnalysis}
            disabled={!auditFile || uploading}
            className="btn btn-primary"
          >
            {uploading ? 'Analyzing...' : 'Analyze Audit'}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {/* Results Display */}
      {results && (
        <div className="results-container">
          {results.type === 'spec' ? (
            <div className="alert alert-success">
              <CheckCircle size={20} />
              <div>
                <strong>Spec Uploaded Successfully!</strong>
                <p>Created {results.data.chunks_created || 'N/A'} chunks</p>
                <p>Processing time: {results.data.processing_time?.toFixed(2) || 'N/A'}s</p>
              </div>
            </div>
          ) : (
            <div className="audit-results">
              <h3>Analysis Results</h3>
              {results.data.infractions?.length > 0 ? (
                <div className="infractions-list">
                  {results.data.infractions.map((inf, idx) => (
                    <div key={idx} className="infraction-card">
                      <div className="infraction-header">
                        <strong>{inf.code || `Infraction ${idx + 1}`}</strong>
                        <span className={`badge ${inf.is_repealable ? 'badge-success' : 'badge-danger'}`}>
                          {inf.is_repealable ? 'Repealable' : 'Not Repealable'}
                        </span>
                      </div>
                      <div className="infraction-details">
                        <p>Confidence: {(inf.confidence * 100).toFixed(0)}%</p>
                        <p>Reason: {inf.reason || 'No reason provided'}</p>
                        {inf.spec_references?.length > 0 && (
                          <p>References: {inf.spec_references.join(', ')}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p>No infractions found</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default UploadSection;
