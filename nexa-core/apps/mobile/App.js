/**
 * Nexa Core Mobile - Crew Foreman As-Built Submission
 * Offline-first with queue and sync
 */

import React, { useState, useEffect } from 'react';
import { View, Button, Text, TextInput, ScrollView, StyleSheet, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import * as ImagePicker from 'expo-image-picker';
import * as SecureStore from 'expo-secure-store';

// IMPORTANT: Update this after deploying your API
const API_URL = 'https://nexa-core-api.onrender.com/api';

const App = () => {
  const [jobId, setJobId] = useState('');
  const [asBuiltNotes, setAsBuiltNotes] = useState('');
  const [measurements, setMeasurements] = useState('');
  const [equipment, setEquipment] = useState('');
  const [weather, setWeather] = useState('');
  const [photos, setPhotos] = useState([]);
  const [status, setStatus] = useState('Ready');
  const [isOnline, setIsOnline] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    // Monitor network status
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOnline(state.isConnected);
      if (state.isConnected) {
        syncPending();
      }
    });

    // Load pending count
    loadPendingCount();
    
    return () => unsubscribe();
  }, []);

  const loadPendingCount = async () => {
    try {
      const pending = await AsyncStorage.getItem('pending_submissions') || '[]';
      const pendingArray = JSON.parse(pending);
      setPendingCount(pendingArray.length);
    } catch (error) {
      console.error('Error loading pending count:', error);
    }
  };

  const pickPhoto = async () => {
    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Required', 'Camera access is needed to capture photos');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.7,
      base64: true  // For offline storage
    });

    if (!result.canceled && result.assets[0]) {
      const photo = {
        uri: result.assets[0].uri,
        base64: result.assets[0].base64,
        timestamp: new Date().toISOString()
      };
      setPhotos([...photos, photo]);
      setStatus(`Photo captured (${photos.length + 1} total)`);
    }
  };

  const getCurrentPosition = () => {
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: new Date().toISOString()
          });
        },
        () => resolve(null)
      );
    });
  };

  const submitAsBuilt = async () => {
    if (!jobId || !asBuiltNotes) {
      Alert.alert('Missing Information', 'Job ID and notes are required');
      return;
    }

    setStatus('Preparing submission...');

    // Get API key
    const apiKey = await SecureStore.getItemAsync('foreman_api_key');
    if (!apiKey) {
      Alert.alert('Authentication Required', 'Please login first');
      setStatus('Login required');
      return;
    }

    // Get GPS coordinates
    const gps = await getCurrentPosition();

    // Build submission data matching API schema
    const submission = {
      job_id: parseInt(jobId),
      as_built_data: {
        notes: asBuiltNotes,
        timestamp: new Date().toISOString()
      },
      equipment_installed: equipment ? JSON.parse(`{"description": "${equipment}"}`) : null,
      measurements: measurements ? JSON.parse(`{"values": "${measurements}"}`) : null,
      weather_conditions: weather,
      crew_notes: asBuiltNotes,
      gps_coordinates: gps,
      submitted_offline: !isOnline,
      photos: photos.map(p => ({
        base64: p.base64,
        timestamp: p.timestamp
      }))
    };

    // Try to submit if online
    if (isOnline) {
      try {
        setStatus('Submitting to server...');
        
        const response = await fetch(`${API_URL}/submissions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
          },
          body: JSON.stringify(submission),
          timeout: 30000
        });

        if (response.ok) {
          const result = await response.json();
          setStatus(`✅ Submitted! ID: ${result.id}`);
          clearForm();
          Alert.alert('Success', 'As-built submitted successfully');
          return;
        } else {
          const error = await response.json();
          throw new Error(error.error || 'Submission failed');
        }
      } catch (error) {
        console.error('Submission error:', error);
        setStatus('Failed - queuing offline...');
        await queueSubmission(submission);
      }
    } else {
      // Queue for later if offline
      await queueSubmission(submission);
    }
  };

  const queueSubmission = async (submission) => {
    try {
      let pending = await AsyncStorage.getItem('pending_submissions') || '[]';
      pending = JSON.parse(pending);
      pending.push({
        ...submission,
        queued_at: new Date().toISOString()
      });
      await AsyncStorage.setItem('pending_submissions', JSON.stringify(pending));
      setPendingCount(pending.length);
      setStatus(`📦 Queued offline (${pending.length} pending)`);
      clearForm();
      Alert.alert('Queued', 'Submission saved for sync when online');
    } catch (error) {
      console.error('Queue error:', error);
      Alert.alert('Error', 'Failed to save submission');
    }
  };

  const syncPending = async () => {
    const apiKey = await SecureStore.getItemAsync('foreman_api_key');
    if (!apiKey) return;

    try {
      let pending = await AsyncStorage.getItem('pending_submissions') || '[]';
      pending = JSON.parse(pending);
      
      if (pending.length === 0) return;

      setStatus(`Syncing ${pending.length} submissions...`);
      
      let successCount = 0;
      const remaining = [];

      for (let submission of pending) {
        try {
          const response = await fetch(`${API_URL}/submissions`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': apiKey
            },
            body: JSON.stringify(submission)
          });

          if (response.ok) {
            successCount++;
          } else {
            remaining.push(submission);
          }
        } catch (error) {
          remaining.push(submission);
        }
      }

      await AsyncStorage.setItem('pending_submissions', JSON.stringify(remaining));
      setPendingCount(remaining.length);
      
      if (successCount > 0) {
        setStatus(`✅ Synced ${successCount} submissions`);
        Alert.alert('Sync Complete', `${successCount} submissions uploaded`);
      }
    } catch (error) {
      console.error('Sync error:', error);
    }
  };

  const clearForm = () => {
    setJobId('');
    setAsBuiltNotes('');
    setMeasurements('');
    setEquipment('');
    setWeather('');
    setPhotos([]);
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Nexa Core - As-Built Submission</Text>
        <Text style={styles.networkStatus}>
          {isOnline ? '🟢 Online' : '🔴 Offline'}
        </Text>
        {pendingCount > 0 && (
          <Text style={styles.pendingBadge}>
            📦 {pendingCount} pending sync
          </Text>
        )}
      </View>

      <View style={styles.form}>
        <Text style={styles.label}>Job ID (from QR):</Text>
        <TextInput
          style={styles.input}
          value={jobId}
          onChangeText={setJobId}
          placeholder="Enter job ID"
          keyboardType="numeric"
        />

        <Text style={styles.label}>As-Built Notes: *</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          value={asBuiltNotes}
          onChangeText={setAsBuiltNotes}
          placeholder="Describe work completed"
          multiline
          numberOfLines={4}
        />

        <Text style={styles.label}>Measurements:</Text>
        <TextInput
          style={styles.input}
          value={measurements}
          onChangeText={setMeasurements}
          placeholder="Spacing, clearance, etc."
        />

        <Text style={styles.label}>Equipment Installed:</Text>
        <TextInput
          style={styles.input}
          value={equipment}
          onChangeText={setEquipment}
          placeholder="Type, model, serial number"
        />

        <Text style={styles.label}>Weather Conditions:</Text>
        <TextInput
          style={styles.input}
          value={weather}
          onChangeText={setWeather}
          placeholder="Clear, rainy, etc."
        />

        <View style={styles.photoSection}>
          <Button title="📷 Capture Photo" onPress={pickPhoto} />
          <Text style={styles.photoCount}>
            Photos captured: {photos.length}
          </Text>
        </View>

        <View style={styles.submitSection}>
          <Button
            title={isOnline ? "Submit As-Built" : "Queue for Sync"}
            onPress={submitAsBuilt}
            color={isOnline ? "#007AFF" : "#FF9500"}
          />
        </View>

        {pendingCount > 0 && isOnline && (
          <View style={styles.syncSection}>
            <Button title="🔄 Sync Now" onPress={syncPending} color="#34C759" />
          </View>
        )}

        <Text style={styles.status}>{status}</Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    backgroundColor: '#007AFF',
    padding: 20,
    paddingTop: 50,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: 'white',
  },
  networkStatus: {
    color: 'white',
    marginTop: 5,
    fontSize: 14,
  },
  pendingBadge: {
    color: '#FFD700',
    marginTop: 5,
    fontSize: 14,
    fontWeight: 'bold',
  },
  form: {
    padding: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 15,
    marginBottom: 5,
  },
  input: {
    backgroundColor: 'white',
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  photoSection: {
    marginTop: 20,
    marginBottom: 10,
  },
  photoCount: {
    marginTop: 10,
    fontSize: 14,
    color: '#666',
  },
  submitSection: {
    marginTop: 20,
  },
  syncSection: {
    marginTop: 10,
  },
  status: {
    marginTop: 20,
    padding: 15,
    backgroundColor: '#E8E8E8',
    borderRadius: 8,
    textAlign: 'center',
    fontSize: 14,
  },
});

export default App;
