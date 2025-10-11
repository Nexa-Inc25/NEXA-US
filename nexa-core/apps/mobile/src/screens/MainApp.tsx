import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import LoginScreen from './LoginScreen';
import GeneralForemanDashboard from './GeneralForemanDashboard';
import ForemanFieldView from './ForemanFieldView';

export default function MainApp() {
  const [user, setUser] = useState<{ role: string } | null>(null);

  const handleLogin = (role: 'gf' | 'foreman' | 'crew') => {
    setUser({ role });
  };

  const handleLogout = () => {
    setUser(null);
  };

  if (!user) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  switch (user.role) {
    case 'gf':
      return <GeneralForemanDashboard />;
    case 'foreman':
    case 'crew':
      return <ForemanFieldView />;
    default:
      return <LoginScreen onLogin={handleLogin} />;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});
