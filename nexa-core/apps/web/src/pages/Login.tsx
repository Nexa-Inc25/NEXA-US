import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import '../styles/login.css';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleRoleLogin = (role: string) => {
    setLoading(true);
    // Store role in session
    sessionStorage.setItem('userRole', role);
    sessionStorage.setItem('userName', role === 'general_foreman' ? 'John Smith' : 'Mike Johnson');
    
    setTimeout(() => {
      if (role === 'general_foreman') {
        navigate('/gf-dashboard');
      } else if (role === 'foreman') {
        navigate('/foreman');
      }
      setLoading(false);
    }, 500);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <Shield size={48} color="#1e3a8a" />
          <h1>NEXA Field Management</h1>
          <p>PG&E Stockton Division</p>
        </div>

        <div className="login-content">
          <h2>Select Your Role</h2>
          
          <div className="role-buttons">
            <button
              className="role-button gf"
              onClick={() => handleRoleLogin('general_foreman')}
              disabled={loading}
            >
              <h3>General Foreman</h3>
              <p>Manage crews, assign jobs, view analytics</p>
            </button>

            <button
              className="role-button foreman"
              onClick={() => handleRoleLogin('foreman')}
              disabled={loading}
            >
              <h3>Foreman</h3>
              <p>Field operations, time tracking, safety</p>
            </button>

            <button
              className="role-button crew"
              onClick={() => handleRoleLogin('crew')}
              disabled={loading}
            >
              <h3>Crew Member</h3>
              <p>View assignments, submit reports</p>
            </button>
          </div>

          {loading && (
            <div className="loading-indicator">
              <div className="spinner"></div>
              <p>Logging in...</p>
            </div>
          )}
        </div>

        <div className="login-footer">
          <p>Production Environment • Render Cloud</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
