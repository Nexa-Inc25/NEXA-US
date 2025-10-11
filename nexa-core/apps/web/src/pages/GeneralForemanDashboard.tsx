import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Briefcase, 
  TrendingUp, 
  AlertCircle,
  Clock,
  CheckCircle,
  Activity,
  DollarSign
} from 'lucide-react';
import axios from 'axios';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend,
  ResponsiveContainer 
} from 'recharts';
import '../styles/dashboard.css';

const API_URL = process.env.REACT_APP_API_URL || 'https://nexa-doc-analyzer-oct2025.onrender.com';

interface Crew {
  id: string;
  name: string;
  foreman: string;
  status: 'active' | 'idle' | 'break' | 'completed';
  currentJob: string | null;
  location: string;
  members: number;
  progress: number;
  lastUpdate: Date;
}

interface Job {
  id: string;
  name: string;
  priority: 'high' | 'medium' | 'low';
  crew: string | null;
  status: 'pending' | 'assigned' | 'in_progress' | 'completed';
  dueDate: Date;
  infractions: number;
  estimatedCost: number;
  pmNumber?: string;
  notificationNumber?: string;
}

const GeneralForemanDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'crews' | 'jobs' | 'analytics'>('overview');
  const [crews, setCrews] = useState<Crew[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCrew, setSelectedCrew] = useState<Crew | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // For now, use mock data. In production, this would call the API
      setCrews([
        {
          id: '1',
          name: 'Crew Alpha',
          foreman: 'John Smith',
          status: 'active',
          currentJob: 'TAG-2 Pole Replacement',
          location: 'Stockton North',
          members: 4,
          progress: 65,
          lastUpdate: new Date(),
        },
        {
          id: '2',
          name: 'Crew Bravo',
          foreman: 'Mike Johnson',
          status: 'active',
          currentJob: 'Transformer Installation',
          location: 'Stockton South',
          members: 5,
          progress: 30,
          lastUpdate: new Date(),
        },
        {
          id: '3',
          name: 'Crew Charlie',
          foreman: 'Sarah Davis',
          status: 'break',
          currentJob: null,
          location: 'Base',
          members: 3,
          progress: 0,
          lastUpdate: new Date(),
        },
        {
          id: '4',
          name: 'Crew Delta',
          foreman: 'Tom Wilson',
          status: 'idle',
          currentJob: null,
          location: 'Base',
          members: 4,
          progress: 0,
          lastUpdate: new Date(),
        },
      ]);

      setJobs([
        {
          id: 'JP001',
          name: '07D-1 Cable Replacement',
          priority: 'high',
          crew: null,
          status: 'pending',
          dueDate: new Date(Date.now() + 86400000),
          infractions: 0,
          estimatedCost: 12500,
          pmNumber: '46369836',
          notificationNumber: '126465328',
        },
        {
          id: 'JP002',
          name: 'Grounding System Upgrade',
          priority: 'medium',
          crew: 'Crew Alpha',
          status: 'in_progress',
          dueDate: new Date(Date.now() + 172800000),
          infractions: 1,
          estimatedCost: 8750,
          pmNumber: '35569872',
          notificationNumber: '129303200',
        },
        {
          id: 'JP003',
          name: 'Service Line Installation',
          priority: 'low',
          crew: null,
          status: 'pending',
          dueDate: new Date(Date.now() + 259200000),
          infractions: 0,
          estimatedCost: 5200,
        },
      ]);

      // Check analyzer health
      const healthCheck = await axios.get(`${API_URL}/health`);
      console.log('Analyzer Status:', healthCheck.data);
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const assignJobToCrew = (jobId: string, crewId: string) => {
    if (window.confirm(`Assign job ${jobId} to crew ${crewId}?`)) {
      setJobs(jobs.map(job => 
        job.id === jobId ? { ...job, crew: crewId, status: 'assigned' } : job
      ));
      alert('Job assigned successfully');
    }
  };

  const metrics = {
    activeCrews: crews.filter(c => c.status === 'active').length,
    totalCrews: crews.length,
    jobsToday: jobs.filter(j => j.status === 'in_progress').length,
    totalJobs: jobs.length,
    infractions: jobs.reduce((sum, j) => sum + j.infractions, 0),
    onTimeRate: 92,
    budgetUsed: 78,
    safetyScore: 98,
  };

  const chartData = {
    crewPerformance: crews.map(c => ({
      name: c.name,
      progress: c.progress,
      status: c.status,
    })),
    jobDistribution: [
      { name: 'Pending', value: jobs.filter(j => j.status === 'pending').length, color: '#FF9800' },
      { name: 'In Progress', value: jobs.filter(j => j.status === 'in_progress').length, color: '#2196F3' },
      { name: 'Completed', value: jobs.filter(j => j.status === 'completed').length, color: '#4CAF50' },
    ],
    weeklyTrend: [
      { day: 'Mon', completed: 4, infractions: 0 },
      { day: 'Tue', completed: 3, infractions: 1 },
      { day: 'Wed', completed: 5, infractions: 0 },
      { day: 'Thu', completed: 4, infractions: 2 },
      { day: 'Fri', completed: 6, infractions: 0 },
    ],
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>NEXA Field Management</h1>
          <p>General Foreman Dashboard - PG&E Stockton Division</p>
        </div>
        <div className="header-actions">
          <button onClick={() => loadDashboardData()} className="btn-refresh">
            Refresh
          </button>
          <span className="user-info">John Smith (GF)</span>
        </div>
      </header>

      <nav className="dashboard-nav">
        <button 
          className={`nav-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <TrendingUp size={20} />
          Overview
        </button>
        <button 
          className={`nav-tab ${activeTab === 'crews' ? 'active' : ''}`}
          onClick={() => setActiveTab('crews')}
        >
          <Users size={20} />
          Crews
        </button>
        <button 
          className={`nav-tab ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          <Briefcase size={20} />
          Jobs
        </button>
        <button 
          className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          <Activity size={20} />
          Analytics
        </button>
      </nav>

      <main className="dashboard-content">
        {activeTab === 'overview' && (
          <div className="overview-section">
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon" style={{ backgroundColor: '#4CAF50' }}>
                  <Users size={24} />
                </div>
                <div className="metric-details">
                  <span className="metric-value">{metrics.activeCrews}/{metrics.totalCrews}</span>
                  <span className="metric-label">Active Crews</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon" style={{ backgroundColor: '#2196F3' }}>
                  <Briefcase size={24} />
                </div>
                <div className="metric-details">
                  <span className="metric-value">{metrics.jobsToday}/{metrics.totalJobs}</span>
                  <span className="metric-label">Jobs Today</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon" style={{ backgroundColor: '#ff6b6b' }}>
                  <AlertCircle size={24} />
                </div>
                <div className="metric-details">
                  <span className="metric-value">{metrics.infractions}</span>
                  <span className="metric-label">Infractions</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon" style={{ backgroundColor: '#9C27B0' }}>
                  <Clock size={24} />
                </div>
                <div className="metric-details">
                  <span className="metric-value">{metrics.onTimeRate}%</span>
                  <span className="metric-label">On Time</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon" style={{ backgroundColor: '#FF9800' }}>
                  <DollarSign size={24} />
                </div>
                <div className="metric-details">
                  <span className="metric-value">{metrics.budgetUsed}%</span>
                  <span className="metric-label">Budget Used</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon" style={{ backgroundColor: '#00BCD4' }}>
                  <CheckCircle size={24} />
                </div>
                <div className="metric-details">
                  <span className="metric-value">{metrics.safetyScore}%</span>
                  <span className="metric-label">Safety Score</span>
                </div>
              </div>
            </div>

            <div className="charts-grid">
              <div className="chart-card">
                <h3>Crew Progress</h3>
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <BarChart data={chartData.crewPerformance}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="progress" fill="#1e3a8a" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="chart-card">
                <h3>Job Status Distribution</h3>
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={chartData.jobDistribution}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        fill="#8884d8"
                      >
                        {chartData.jobDistribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'crews' && (
          <div className="crews-section">
            <div className="section-header">
              <h2>Crew Management</h2>
              <div className="filter-controls">
                <select className="filter-select">
                  <option>All Status</option>
                  <option>Active</option>
                  <option>Idle</option>
                  <option>Break</option>
                </select>
              </div>
            </div>

            <div className="crews-grid">
              {crews.map(crew => (
                <div key={crew.id} className={`crew-card ${crew.status}`}>
                  <div className={`crew-status status-${crew.status}`}>
                    {crew.status.toUpperCase()}
                  </div>
                  <h3>{crew.name}</h3>
                  <p className="crew-foreman">Foreman: {crew.foreman}</p>
                  <p className="crew-location">Location: {crew.location}</p>
                  <p className="crew-members">{crew.members} members</p>
                  
                  {crew.currentJob && (
                    <>
                      <div className="current-job">
                        <p className="job-label">Current Job:</p>
                        <p className="job-name">{crew.currentJob}</p>
                      </div>
                      <div className="progress-bar">
                        <div 
                          className="progress-fill" 
                          style={{ width: `${crew.progress}%` }}
                        />
                      </div>
                      <p className="progress-text">{crew.progress}% Complete</p>
                    </>
                  )}
                  
                  <button 
                    className="btn-view-details"
                    onClick={() => setSelectedCrew(crew)}
                  >
                    View Details
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="jobs-section">
            <div className="section-header">
              <h2>Job Queue</h2>
              <div className="filter-controls">
                <select className="filter-select">
                  <option>All Priorities</option>
                  <option>High</option>
                  <option>Medium</option>
                  <option>Low</option>
                </select>
                <button className="btn-new-job">+ New Job</button>
              </div>
            </div>

            <div className="jobs-table">
              <table>
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>Name</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Crew</th>
                    <th>Due Date</th>
                    <th>PM #</th>
                    <th>Cost</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map(job => (
                    <tr key={job.id}>
                      <td>{job.id}</td>
                      <td>{job.name}</td>
                      <td>
                        <span className={`priority-badge priority-${job.priority}`}>
                          {job.priority.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge status-${job.status}`}>
                          {job.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td>{job.crew || '-'}</td>
                      <td>{job.dueDate.toLocaleDateString()}</td>
                      <td>{job.pmNumber || '-'}</td>
                      <td>${job.estimatedCost.toLocaleString()}</td>
                      <td>
                        {!job.crew ? (
                          <select 
                            onChange={(e) => e.target.value && assignJobToCrew(job.id, e.target.value)}
                            className="assign-select"
                          >
                            <option value="">Assign to...</option>
                            {crews.filter(c => c.status !== 'break').map(crew => (
                              <option key={crew.id} value={crew.id}>{crew.name}</option>
                            ))}
                          </select>
                        ) : (
                          <button className="btn-view" onClick={() => setSelectedJob(job)}>
                            View
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="analytics-section">
            <div className="section-header">
              <h2>Performance Analytics</h2>
              <div className="date-range">
                <input type="date" className="date-input" />
                <span>to</span>
                <input type="date" className="date-input" />
                <button className="btn-apply">Apply</button>
              </div>
            </div>

            <div className="analytics-grid">
              <div className="chart-card full-width">
                <h3>Weekly Completion Trend</h3>
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <LineChart data={chartData.weeklyTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="completed" stroke="#4CAF50" name="Jobs Completed" />
                      <Line type="monotone" dataKey="infractions" stroke="#ff6b6b" name="Infractions" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="stat-cards">
                <div className="stat-card">
                  <h4>Average Completion Time</h4>
                  <p className="stat-value">3.5 days</p>
                  <p className="stat-change positive">-12% from last week</p>
                </div>
                <div className="stat-card">
                  <h4>Contestable Go-Backs</h4>
                  <p className="stat-value">8 / 12</p>
                  <p className="stat-change">67% success rate</p>
                </div>
                <div className="stat-card">
                  <h4>Cost Efficiency</h4>
                  <p className="stat-value">$452K / $580K</p>
                  <p className="stat-change positive">22% under budget</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default GeneralForemanDashboard;
