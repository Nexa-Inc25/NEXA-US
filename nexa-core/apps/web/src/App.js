import React, { useState, useEffect } from 'react';
import './App.css';
import { Activity, Users, FileCheck, AlertTriangle, TrendingUp, Clock, DollarSign, CheckCircle } from 'lucide-react';

function App() {
  const [stats, setStats] = useState({
    activeProjects: 0,
    totalCrews: 0,
    pendingQA: 0,
    infractions: 0
  });

  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch data from your API
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // For now, using mock data
      setTimeout(() => {
        setStats({
          activeProjects: 12,
          totalCrews: 8,
          pendingQA: 23,
          infractions: 5
        });
        
        setRecentActivity([
          { id: 1, type: 'qa', message: 'QA submitted for Job #2341', time: '5 min ago', status: 'pending' },
          { id: 2, type: 'complete', message: 'Job #2339 completed', time: '1 hour ago', status: 'success' },
          { id: 3, type: 'infraction', message: 'Infraction detected in Job #2340', time: '2 hours ago', status: 'warning' },
          { id: 4, type: 'crew', message: 'Crew 3 started Job #2342', time: '3 hours ago', status: 'info' },
        ]);
        
        setLoading(false);
      }, 1000);

      // Real API call would be:
      // const apiUrl = process.env.REACT_APP_API_URL || 'https://nexa-core-api.onrender.com';
      // const response = await fetch(`${apiUrl}/api/dashboard/stats`);
      // const data = await response.json();
      // setStats(data.stats);
      // setRecentActivity(data.activity);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
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
    <div className="App">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <div>
            <h1>NEXA Dashboard</h1>
            <p className="subtitle">Field Operations Management</p>
          </div>
          <div className="header-actions">
            <button className="btn btn-primary">New Project</button>
            <button className="btn btn-secondary">Generate Report</button>
          </div>
        </div>
      </header>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">
            <Activity size={24} />
          </div>
          <div className="stat-content">
            <h3>Active Projects</h3>
            <p className="stat-value">{stats.activeProjects}</p>
            <span className="stat-change positive">+12% from last month</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">
            <Users size={24} />
          </div>
          <div className="stat-content">
            <h3>Total Crews</h3>
            <p className="stat-value">{stats.totalCrews}</p>
            <span className="stat-change">8 active today</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon orange">
            <FileCheck size={24} />
          </div>
          <div className="stat-content">
            <h3>Pending QA</h3>
            <p className="stat-value">{stats.pendingQA}</p>
            <span className="stat-change">5 urgent</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon red">
            <AlertTriangle size={24} />
          </div>
          <div className="stat-content">
            <h3>Infractions</h3>
            <p className="stat-value">{stats.infractions}</p>
            <span className="stat-change negative">-25% from last week</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Recent Activity */}
        <div className="activity-section">
          <h2>Recent Activity</h2>
          <div className="activity-list">
            {recentActivity.map(activity => (
              <div key={activity.id} className={`activity-item ${activity.status}`}>
                <div className="activity-icon">
                  {activity.type === 'qa' && <FileCheck size={20} />}
                  {activity.type === 'complete' && <CheckCircle size={20} />}
                  {activity.type === 'infraction' && <AlertTriangle size={20} />}
                  {activity.type === 'crew' && <Users size={20} />}
                </div>
                <div className="activity-content">
                  <p>{activity.message}</p>
                  <span className="activity-time">{activity.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Projects Table */}
        <div className="projects-section">
          <h2>Active Projects</h2>
          <table className="projects-table">
            <thead>
              <tr>
                <th>Project ID</th>
                <th>Location</th>
                <th>Crew</th>
                <th>Progress</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>#2341</td>
                <td>Sacramento, CA</td>
                <td>Crew 3</td>
                <td>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{width: '75%'}}></div>
                  </div>
                  <span>75%</span>
                </td>
                <td><span className="status-badge active">In Progress</span></td>
                <td>
                  <button className="btn-small">View Details</button>
                </td>
              </tr>
              <tr>
                <td>#2340</td>
                <td>San Francisco, CA</td>
                <td>Crew 1</td>
                <td>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{width: '90%'}}></div>
                  </div>
                  <span>90%</span>
                </td>
                <td><span className="status-badge review">Under Review</span></td>
                <td>
                  <button className="btn-small">View Details</button>
                </td>
              </tr>
              <tr>
                <td>#2339</td>
                <td>Oakland, CA</td>
                <td>Crew 5</td>
                <td>
                  <div className="progress-bar">
                    <div className="progress-fill complete" style={{width: '100%'}}></div>
                  </div>
                  <span>100%</span>
                </td>
                <td><span className="status-badge complete">Completed</span></td>
                <td>
                  <button className="btn-small">View Details</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <footer className="dashboard-footer">
        <p>© 2025 NEXA Inc. All rights reserved.</p>
        <div className="footer-links">
          <a href="/help">Help</a>
          <a href="/settings">Settings</a>
          <a href="/api">API Status</a>
        </div>
      </footer>
    </div>
  );
}

export default App;
