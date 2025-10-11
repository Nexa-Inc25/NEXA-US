import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';

interface LoginScreenProps {
  onLogin: (role: 'gf' | 'foreman' | 'crew') => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [loading, setLoading] = useState(false);

  const handleLogin = (role: 'gf' | 'foreman' | 'crew') => {
    setLoading(true);
    setTimeout(() => {
      onLogin(role);
      setLoading(false);
    }, 500);
  };


  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>NEXA Field Management</Text>
          <Text style={styles.subtitle}>Select Role</Text>
        </View>

        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={styles.roleButton}
            onPress={() => handleLogin('gf')}
            disabled={loading}
          >
            <Text style={styles.roleButtonText}>General Foreman</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.roleButton}
            onPress={() => handleLogin('foreman')}
            disabled={loading}
          >
            <Text style={styles.roleButtonText}>Foreman</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.roleButton}
            onPress={() => handleLogin('crew')}
            disabled={loading}
          >
            <Text style={styles.roleButtonText}>Crew Member</Text>
          </TouchableOpacity>

          {loading && <ActivityIndicator size="large" color="#1e3a8a" style={styles.loader} />}
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>PG&E Stockton Division</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e3a8a',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#64748b',
  },
  buttonContainer: {
    marginBottom: 40,
  },
  roleButton: {
    backgroundColor: '#1e3a8a',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  roleButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  loader: {
    marginTop: 20,
  },
  footer: {
    alignItems: 'center',
  },
  footerText: {
    color: '#64748b',
    fontSize: 14,
  },
});
