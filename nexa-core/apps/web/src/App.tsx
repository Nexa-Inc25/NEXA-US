import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import GeneralForemanDashboard from './pages/GeneralForemanDashboard';
import ForemanFieldView from './pages/ForemanFieldView';
import Login from './pages/Login';
import { AuthProvider } from './contexts/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import './styles/global.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route 
            path="/gf-dashboard" 
            element={
              <PrivateRoute role="general_foreman">
                <GeneralForemanDashboard />
              </PrivateRoute>
            } 
          />
          <Route 
            path="/foreman" 
            element={
              <PrivateRoute role="foreman">
                <ForemanFieldView />
              </PrivateRoute>
            } 
          />
          <Route path="/" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
