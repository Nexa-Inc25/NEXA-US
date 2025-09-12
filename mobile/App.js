import React from 'react';
import { SafeAreaView, View, Text, Button } from 'react-native';
import Constants from 'expo-constants';
import { AuthProvider, useAuth } from './src/auth/AuthProvider';
import TodayScreen from './src/screens/TodayScreen';

function Welcome() {
  const { isAuthenticated, login, devLogin, logout, user } = useAuth();

  return (
    <SafeAreaView style={{ flex: 1, padding: 16 }}>
      {!isAuthenticated ? (
        <View>
          <Text style={{ fontSize: 20, marginBottom: 12 }}>NEXA Foreman (MVP)</Text>
          <View style={{ gap: 8 }}>
            <Button title="Login with Auth0" onPress={login} />
            <Button title="Dev Login (Bypass)" onPress={devLogin} />
          </View>
        </View>
      ) : (
        <View style={{ flex: 1 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
            <Text style={{ fontSize: 16 }}>Welcome {user?.sub || 'foreman'}</Text>
            <Button title="Logout" onPress={logout} />
          </View>
          <TodayScreen />
        </View>
      )}
      <Text style={{ marginTop: 16, color: '#888' }}>API: {Constants?.expoConfig?.extra?.API_BASE_URL}</Text>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Welcome />
    </AuthProvider>
  );
}
