import React, { useState, useEffect } from 'react';
import { 
  Briefcase, 
  Clock, 
  Shield, 
  Camera,
  CheckCircle,
  AlertTriangle,
  MapPin,
  Users,
  FileText
} from 'lucide-react';
import axios from 'axios';
import '../styles/foreman.css';

const API_URL = process.env.REACT_APP_API_URL || 'https://nexa-doc-analyzer-oct2025.onrender.com';

interface Job {
  id: string;
  name: string;
  location: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed';
  assignedBy: string;
  dueDate: Date;
  description: string;
  crew: string[];
  pmNumber?: string;
  notificationNumber?: string;
}

interface TimeEntry {
  id: string;
  date: Date;
  hours: number;
  jobId: string;
  notes: string;
}

interface SafetyCheck {
  ppe: boolean;
  hazards: boolean;
  permits: boolean;
  briefing: boolean;
}

const ForemanFieldView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'jobs' | 'time' | 'safety' | 'photos'>('jobs');
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTimeModal, setShowTimeModal] = useState(false);
  const [showSafetyModal, setShowSafetyModal] = useState(false);
  const [timeFormData, setTimeFormData] = useState({ hours: '', notes: '' });
  const [safetyChecks, setSafetyChecks] = useState<SafetyCheck>({
    ppe: false,
    hazards: false,
    permits: false,
    briefing: false,
  });
  const [photos, setPhotos] = useState<any[]>([]);

  useEffect(() => {
    loadForemanData();
  }, []);

  const loadForemanData = async () => {
    setLoading(true);
    try {
      // Mock data - in production this would call the API
      const mockJobs: Job[] = [
        {
          id: 'J001',
          name: 'TAG-2 Pole Replacement',
          location: 'Stockton North - Grid 42B',
          priority: 'high',
          status: 'in_progress',
          assignedBy: 'John Smith (GF)',
          dueDate: new Date(Date.now() + 86400000),
          description: 'Replace deteriorated pole with new TAG-2 rated pole. Check guy wires and ground connections.',
          crew: ['Mike Johnson', 'Tom Wilson', 'Steve Brown'],
          pmNumber: '46369836',
          notificationNumber: '126465328',
        },
        {
          id: 'J002',
          name: 'Transformer Installation',
          location: 'Stockton South - Grid 18A',
          priority: 'medium',
          status: 'pending',
          assignedBy: 'John Smith (GF)',
          dueDate: new Date(Date.now() + 172800000),
          description: 'Install new 50kVA transformer. Coordinate with switching center for outage.',
          crew: ['Mike Johnson', 'Tom Wilson'],
          pmNumber: '35569872',
        },
      ];

      setJobs(mockJobs);
      setCurrentJob(mockJobs[0]);

      setTimeEntries([
        { id: 'T001', date: new Date(), hours: 3.5, jobId: 'J001', notes: 'Site preparation and safety setup' },
        { id: 'T002', date: new Date(Date.now() - 86400000), hours: 8, jobId: 'J001', notes: 'Old pole removal' },
      ]);

      setPhotos([
        { id: 'P001', name: 'Before - Pole condition', timestamp: new Date(Date.now() - 86400000) },
        { id: 'P002', name: 'During - Excavation', timestamp: new Date(Date.now() - 43200000) },
      ]);

    } catch (error) {
      console.error('Error loading foreman data:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateJobStatus = (jobId: string, newStatus: 'pending' | 'in_progress' | 'completed') => {
    if (window.confirm(`Update job status to ${newStatus}?`)) {
      setJobs(jobs.map(job => 
        job.id === jobId ? { ...job, status: newStatus } : job
      ));
      if (currentJob?.id === jobId) {
        setCurrentJob({ ...currentJob, status: newStatus });
      }
      alert('Job status updated successfully');
    }
  };

  const submitTimeEntry = () => {
    if (!timeFormData.hours || !currentJob) return;
    
    const newEntry: TimeEntry = {
      id: `T${Date.now()}`,
      date: new Date(),
      hours: parseFloat(timeFormData.hours),
      jobId: currentJob.id,
      notes: timeFormData.notes,
    };
    
    setTimeEntries([newEntry, ...timeEntries]);
    setShowTimeModal(false);
    setTimeFormData({ hours: '', notes: '' });
    alert('Time entry submitted');
  };

  const submitSafetyReport = () => {
    const allChecked = Object.values(safetyChecks).every(v => v);
    if (!allChecked) {
      alert('Please complete all safety checks');
      return;
    }
    
    setShowSafetyModal(false);
    setSafetyChecks({ ppe: false, hazards: false, permits: false, briefing: false });
    alert('Safety report submitted successfully');
  };

  const uploadPhoto = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e: any) => {
      const file = e.target.files[0];
      if (file) {
        const newPhoto = {
          id: `P${Date.now()}`,
          name: file.name,
          timestamp: new Date(),
        };
        setPhotos([newPhoto, ...photos]);
        alert('Photo uploaded successfully');
      }
    };
    input.click();
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading field data...</p>
      </div>
    );
  }

  return (
    <div className="foreman-container">
      <header className="foreman-header">
        <div className="header-content">
          <h1>Foreman Field View</h1>
          <p>Mike Johnson - Crew Alpha</p>
        </div>
        <div className="header-actions">
          <button onClick={() => loadForemanData()} className="btn-sync">
            Sync Data
          </button>
          <span className="connection-status online">Online</span>
        </div>
      </header>

      <nav className="foreman-nav">
        <button 
          className={`nav-tab ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          <Briefcase size={20} />
          Jobs
        </button>
        <button 
          className={`nav-tab ${activeTab === 'time' ? 'active' : ''}`}
          onClick={() => setActiveTab('time')}
        >
          <Clock size={20} />
          Time
        </button>
        <button 
          className={`nav-tab ${activeTab === 'safety' ? 'active' : ''}`}
          onClick={() => setActiveTab('safety')}
        >
          <Shield size={20} />
          Safety
        </button>
        <button 
          className={`nav-tab ${activeTab === 'photos' ? 'active' : ''}`}
          onClick={() => setActiveTab('photos')}
        >
          <Camera size={20} />
          Photos
        </button>
      </nav>

      <main className="foreman-content">
        {activeTab === 'jobs' && (
          <div className="jobs-section">
            {currentJob && (
              <div className="current-job-card">
                <div className="job-header">
                  <h2>Current Job</h2>
                  <span className={`priority-indicator priority-${currentJob.priority}`}>
                    {currentJob.priority.toUpperCase()}
                  </span>
                </div>
                
                <h3>{currentJob.name}</h3>
                
                <div className="job-details">
                  <div className="detail-item">
                    <MapPin size={16} />
                    <span>{currentJob.location}</span>
                  </div>
                  <div className="detail-item">
                    <Users size={16} />
                    <span>Assigned by: {currentJob.assignedBy}</span>
                  </div>
                  <div className="detail-item">
                    <Clock size={16} />
                    <span>Due: {currentJob.dueDate.toLocaleDateString()}</span>
                  </div>
                  {currentJob.pmNumber && (
                    <div className="detail-item">
                      <FileText size={16} />
                      <span>PM #{currentJob.pmNumber}</span>
                    </div>
                  )}
                </div>

                <p className="job-description">{currentJob.description}</p>

                <div className="crew-list">
                  <h4>Crew Members ({currentJob.crew.length})</h4>
                  {currentJob.crew.map((member, index) => (
                    <div key={index} className="crew-member">
                      <CheckCircle size={16} color="#4CAF50" />
                      <span>{member}</span>
                    </div>
                  ))}
                </div>

                <div className="job-actions">
                  <select 
                    value={currentJob.status}
                    onChange={(e) => updateJobStatus(currentJob.id, e.target.value as any)}
                    className={`status-select status-${currentJob.status}`}
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              </div>
            )}

            <div className="upcoming-jobs">
              <h3>Upcoming Jobs</h3>
              <div className="jobs-list">
                {jobs.filter(j => j.id !== currentJob?.id).map(job => (
                  <div key={job.id} className="job-item" onClick={() => setCurrentJob(job)}>
                    <div className="job-item-header">
                      <h4>{job.name}</h4>
                      <span className={`priority-badge priority-${job.priority}`}>
                        {job.priority}
                      </span>
                    </div>
                    <p>{job.location}</p>
                    <p className="job-due">Due: {job.dueDate.toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'time' && (
          <div className="time-section">
            <div className="time-header">
              <h2>Time Tracking</h2>
              <button onClick={() => setShowTimeModal(true)} className="btn-primary">
                Log Time Entry
              </button>
            </div>

            <div className="time-summary">
              <div className="summary-card">
                <h3>Today's Hours</h3>
                <p className="summary-value">
                  {timeEntries
                    .filter(t => t.date.toDateString() === new Date().toDateString())
                    .reduce((sum, t) => sum + t.hours, 0)
                    .toFixed(1)} hrs
                </p>
              </div>
              <div className="summary-card">
                <h3>Week Total</h3>
                <p className="summary-value">
                  {timeEntries.reduce((sum, t) => sum + t.hours, 0).toFixed(1)} hrs
                </p>
              </div>
            </div>

            <div className="time-entries">
              <h3>Recent Entries</h3>
              {timeEntries.map(entry => (
                <div key={entry.id} className="time-entry">
                  <div className="entry-header">
                    <span className="entry-date">{entry.date.toLocaleDateString()}</span>
                    <span className="entry-hours">{entry.hours} hours</span>
                  </div>
                  <p className="entry-notes">{entry.notes}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'safety' && (
          <div className="safety-section">
            <div className="safety-header">
              <h2>Safety Management</h2>
              <button onClick={() => setShowSafetyModal(true)} className="btn-primary">
                Complete Safety Check
              </button>
            </div>

            <div className="safety-status">
              <div className="status-card safe">
                <CheckCircle size={32} />
                <h3>All Clear</h3>
                <p>No safety incidents today</p>
              </div>
            </div>

            <div className="safety-requirements">
              <h3>Today's Requirements</h3>
              <div className="requirement-list">
                <div className="requirement-item">
                  <Shield size={20} color="#1e3a8a" />
                  <span>Hard hats required at all times</span>
                </div>
                <div className="requirement-item">
                  <Shield size={20} color="#1e3a8a" />
                  <span>Safety glasses required</span>
                </div>
                <div className="requirement-item">
                  <Shield size={20} color="#1e3a8a" />
                  <span>Steel-toed boots required</span>
                </div>
                <div className="requirement-item">
                  <Shield size={20} color="#1e3a8a" />
                  <span>High-visibility vests required</span>
                </div>
              </div>
            </div>

            <div className="hazards">
              <h3>Active Hazards</h3>
              <div className="hazard-list">
                <div className="hazard-item">
                  <AlertTriangle size={20} color="#FF9800" />
                  <span>Overhead power lines - maintain 10ft clearance</span>
                </div>
                <div className="hazard-item">
                  <AlertTriangle size={20} color="#FF9800" />
                  <span>Underground utilities marked - dig with caution</span>
                </div>
                <div className="hazard-item">
                  <AlertTriangle size={20} color="#FF9800" />
                  <span>Traffic control zone - use spotters</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'photos' && (
          <div className="photos-section">
            <div className="photos-header">
              <h2>Documentation</h2>
              <div className="photo-actions">
                <button onClick={uploadPhoto} className="btn-primary">
                  <Camera size={20} />
                  Take Photo
                </button>
                <button className="btn-secondary">
                  <FileText size={20} />
                  Upload Document
                </button>
              </div>
            </div>

            <div className="photos-grid">
              {photos.map(photo => (
                <div key={photo.id} className="photo-card">
                  <div className="photo-placeholder">
                    <Camera size={32} color="#999" />
                  </div>
                  <p className="photo-name">{photo.name}</p>
                  <p className="photo-time">{photo.timestamp.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Time Entry Modal */}
      {showTimeModal && (
        <div className="modal-overlay" onClick={() => setShowTimeModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>Log Time Entry</h2>
            
            <div className="form-group">
              <label>Hours Worked</label>
              <input
                type="number"
                step="0.5"
                value={timeFormData.hours}
                onChange={e => setTimeFormData({ ...timeFormData, hours: e.target.value })}
                placeholder="8.0"
              />
            </div>
            
            <div className="form-group">
              <label>Notes</label>
              <textarea
                value={timeFormData.notes}
                onChange={e => setTimeFormData({ ...timeFormData, notes: e.target.value })}
                placeholder="Describe work performed..."
                rows={4}
              />
            </div>
            
            <div className="modal-actions">
              <button onClick={() => setShowTimeModal(false)} className="btn-cancel">
                Cancel
              </button>
              <button onClick={submitTimeEntry} className="btn-submit">
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Safety Check Modal */}
      {showSafetyModal && (
        <div className="modal-overlay" onClick={() => setShowSafetyModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>Daily Safety Checklist</h2>
            
            <div className="checklist">
              {Object.entries({
                ppe: 'All crew members wearing proper PPE',
                hazards: 'Hazards identified and mitigated',
                permits: 'Required permits in place',
                briefing: 'Safety briefing completed',
              }).map(([key, label]) => (
                <label key={key} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={safetyChecks[key as keyof SafetyCheck]}
                    onChange={e => setSafetyChecks({
                      ...safetyChecks,
                      [key]: e.target.checked
                    })}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
            
            <div className="modal-actions">
              <button onClick={() => setShowSafetyModal(false)} className="btn-cancel">
                Cancel
              </button>
              <button onClick={submitSafetyReport} className="btn-submit">
                Submit Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ForemanFieldView;
