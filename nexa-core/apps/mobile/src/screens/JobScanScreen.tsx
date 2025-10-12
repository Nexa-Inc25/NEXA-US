import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ScrollView,
  ActivityIndicator,
  Image
} from 'react-native';
import * as BarCodeScanner from 'expo-barcode-scanner';
import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system';
import { Camera } from 'expo-camera';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = 'https://nexa-doc-analyzer-oct2025.onrender.com';

interface JobData {
  job_id: string;
  pm_number: string;
  notification_number?: string;
  location: string;
  scheduled_date: string;
  crew: string;
  foreman: string;
  initial_analysis?: {
    infractions: number;
    repealable: number;
    total_savings: number;
  };
}

interface PhotoCapture {
  uri: string;
  timestamp: string;
  type: 'pole' | 'crossarm' | 'grounding' | 'general';
  yolo_check?: {
    passed: boolean;
    issues: string[];
    confidence: number;
  };
}

export default function JobScanScreen({ navigation }: any) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [scanned, setScanned] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [jobData, setJobData] = useState<JobData | null>(null);
  const [photos, setPhotos] = useState<PhotoCapture[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const { status } = await BarCodeScanner.requestPermissionsAsync();
      setHasPermission(status === 'granted');
      
      const cameraStatus = await Camera.requestCameraPermissionsAsync();
      if (cameraStatus.status !== 'granted') {
        Alert.alert('Permission needed', 'Camera permission is required to take photos');
      }
    })();
  }, []);

  const handleBarCodeScanned = async ({ type, data }: { type: string; data: string }) => {
    setScanned(true);
    setScanning(false);
    
    // Parse QR code - expects format: JOB-YYYYMMDD-XXXXXXXX
    if (data.startsWith('JOB-')) {
      setLoading(true);
      try {
        // Fetch job details from backend
        const response = await axios.get(`${API_URL}/api/workflow/job/${data}`);
        setJobData(response.data);
        
        Alert.alert(
          'Job Found',
          `PM: ${response.data.pm_number}\nLocation: ${response.data.location}`,
          [{ text: 'Start Work', onPress: () => {} }]
        );
      } catch (error) {
        Alert.alert('Error', 'Could not load job details');
        console.error(error);
      } finally {
        setLoading(false);
      }
    } else {
      Alert.alert('Invalid QR Code', 'Please scan a valid job QR code');
      setScanned(false);
    }
  };

  const takePhoto = async (type: PhotoCapture['type']) => {
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false,
      quality: 0.8,
      base64: true,
    });

    if (!result.canceled && result.assets[0]) {
      const photo: PhotoCapture = {
        uri: result.assets[0].uri,
        timestamp: new Date().toISOString(),
        type: type,
      };

      // Run YOLO check (offline initially)
      const yoloResult = await runYOLOCheck(result.assets[0]);
      photo.yolo_check = yoloResult;

      setPhotos([...photos, photo]);

      if (!yoloResult.passed) {
        Alert.alert(
          '⚠️ Potential Issue Detected',
          `YOLO detected: ${yoloResult.issues.join(', ')}\n\nConfidence: ${(yoloResult.confidence * 100).toFixed(1)}%`,
          [
            { text: 'Retake', onPress: () => takePhoto(type) },
            { text: 'Keep Anyway', style: 'cancel' }
          ]
        );
      }
    }
  };

  const runYOLOCheck = async (image: any): Promise<PhotoCapture['yolo_check']> => {
    // For offline demo - in production, use TensorFlow Lite
    // Simulate YOLO detection
    const random = Math.random();
    
    if (random > 0.8) {
      return {
        passed: false,
        issues: ['Crossarm spacing non-compliant', 'Missing grounding wire'],
        confidence: 0.92
      };
    }
    
    return {
      passed: true,
      issues: [],
      confidence: 0.95
    };
  };

  const submitJob = async () => {
    if (!jobData || photos.length === 0) {
      Alert.alert('Incomplete', 'Please scan a job and take photos before submitting');
      return;
    }

    setSubmitting(true);

    try {
      // Check for go-backs
      const hasIssues = photos.some(p => p.yolo_check && !p.yolo_check.passed);
      
      if (hasIssues) {
        Alert.alert(
          'Go-Backs Detected',
          'YOLO detected potential issues. Submit anyway?',
          [
            { text: 'Fix Issues', style: 'cancel', onPress: () => setSubmitting(false) },
            { text: 'Submit', style: 'destructive', onPress: () => doSubmit() }
          ]
        );
      } else {
        await doSubmit();
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to submit job');
      console.error(error);
      setSubmitting(false);
    }
  };

  const doSubmit = async () => {
    try {
      // Convert photos to base64 for upload
      const photoData = await Promise.all(photos.map(async (photo) => {
        const base64 = await FileSystem.readAsStringAsync(photo.uri, {
          encoding: 'base64' as const,
        });
        return base64;
      }));

      // Submit to backend
      const response = await axios.post(`${API_URL}/api/workflow/submit-field-work`, {
        job_id: jobData!.job_id,
        photos: photoData,
        notes: `Field work completed. ${photos.length} photos taken.`
      });

      // Save to local queue if offline
      if (!response.data) {
        await saveToQueue({
          job_id: jobData!.job_id,
          photos: photoData,
          timestamp: new Date().toISOString()
        });
      }

      Alert.alert(
        '✅ Job Submitted',
        `Job ${jobData!.pm_number} has been submitted for QA review.\n\nExpected processing: 5 minutes`,
        [{ text: 'OK', onPress: () => navigation.navigate('Jobs') }]
      );
    } catch (error) {
      console.error('Submit error:', error);
      // Save to offline queue
      await saveToQueue({
        job_id: jobData!.job_id,
        photos: photos.map(p => p.uri),
        timestamp: new Date().toISOString()
      });
      
      Alert.alert(
        'Saved Offline',
        'Job saved locally and will sync when connection is restored',
        [{ text: 'OK', onPress: () => navigation.navigate('Jobs') }]
      );
    } finally {
      setSubmitting(false);
    }
  };

  const saveToQueue = async (data: any) => {
    try {
      const queue = await AsyncStorage.getItem('offline_queue');
      const items = queue ? JSON.parse(queue) : [];
      items.push(data);
      await AsyncStorage.setItem('offline_queue', JSON.stringify(items));
    } catch (error) {
      console.error('Queue save error:', error);
    }
  };

  if (hasPermission === null) {
    return <View style={styles.container}><ActivityIndicator size="large" /></View>;
  }
  
  if (hasPermission === false) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>No access to camera</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* QR Scanner Section */}
      {!jobData && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Scan Job QR Code</Text>
          {scanning ? (
            <View style={styles.scannerContainer}>
              <BarCodeScanner.BarCodeScanner
                onBarCodeScanned={scanned ? undefined : handleBarCodeScanned}
                style={StyleSheet.absoluteFillObject}
              />
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setScanning(false)}
              >
                <Text style={styles.cancelText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.scanButton}
              onPress={() => {
                setScanning(true);
                setScanned(false);
              }}
            >
              <Text style={styles.scanButtonText}>📷 Scan QR Code</Text>
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* Job Details */}
      {jobData && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Job Details</Text>
          <View style={styles.jobCard}>
            <Text style={styles.jobField}>PM: {jobData.pm_number}</Text>
            <Text style={styles.jobField}>Location: {jobData.location}</Text>
            <Text style={styles.jobField}>Crew: {jobData.crew}</Text>
            <Text style={styles.jobField}>Scheduled: {new Date(jobData.scheduled_date).toLocaleDateString()}</Text>
            {jobData.initial_analysis && (
              <View style={styles.warningBox}>
                <Text style={styles.warningText}>
                  ⚠️ {jobData.initial_analysis.infractions} potential issues identified
                </Text>
                <Text style={styles.warningSubtext}>
                  {jobData.initial_analysis.repealable} may be repealable (${jobData.initial_analysis.total_savings} savings)
                </Text>
              </View>
            )}
          </View>
        </View>
      )}

      {/* Photo Capture */}
      {jobData && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Field Photos ({photos.length})</Text>
          
          <View style={styles.photoButtons}>
            <TouchableOpacity
              style={styles.photoButton}
              onPress={() => takePhoto('pole')}
            >
              <Text style={styles.photoButtonText}>📸 Pole</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.photoButton}
              onPress={() => takePhoto('crossarm')}
            >
              <Text style={styles.photoButtonText}>📸 Crossarm</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.photoButton}
              onPress={() => takePhoto('grounding')}
            >
              <Text style={styles.photoButtonText}>📸 Grounding</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.photoButton}
              onPress={() => takePhoto('general')}
            >
              <Text style={styles.photoButtonText}>📸 General</Text>
            </TouchableOpacity>
          </View>

          {/* Photo Gallery */}
          <ScrollView horizontal style={styles.photoGallery}>
            {photos.map((photo, index) => (
              <View key={index} style={styles.photoItem}>
                <Image source={{ uri: photo.uri }} style={styles.photoThumb} />
                <Text style={styles.photoType}>{photo.type}</Text>
                {photo.yolo_check && !photo.yolo_check.passed && (
                  <View style={styles.issueIndicator}>
                    <Text style={styles.issueText}>!</Text>
                  </View>
                )}
              </View>
            ))}
          </ScrollView>

          {/* YOLO Results Summary */}
          {photos.some(p => p.yolo_check && !p.yolo_check.passed) && (
            <View style={styles.yoloSummary}>
              <Text style={styles.yoloTitle}>⚠️ Issues Detected by AI</Text>
              {photos
                .filter(p => p.yolo_check && !p.yolo_check.passed)
                .map((photo, i) => (
                  <Text key={i} style={styles.yoloIssue}>
                    • {photo.yolo_check!.issues.join(', ')}
                  </Text>
                ))}
            </View>
          )}
        </View>
      )}

      {/* Submit Button */}
      {jobData && photos.length > 0 && (
        <TouchableOpacity
          style={[styles.submitButton, submitting && styles.submitButtonDisabled]}
          onPress={submitJob}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.submitButtonText}>Submit Job for QA Review</Text>
          )}
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  section: {
    backgroundColor: 'white',
    margin: 10,
    padding: 15,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
    color: '#1e3a8a',
  },
  scannerContainer: {
    height: 300,
    borderRadius: 10,
    overflow: 'hidden',
    position: 'relative',
  },
  cancelButton: {
    position: 'absolute',
    bottom: 20,
    alignSelf: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  cancelText: {
    color: 'white',
    fontSize: 16,
  },
  scanButton: {
    backgroundColor: '#1e3a8a',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  scanButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  jobCard: {
    backgroundColor: '#f9fafb',
    padding: 15,
    borderRadius: 8,
  },
  jobField: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 8,
  },
  warningBox: {
    backgroundColor: '#fef3c7',
    padding: 10,
    borderRadius: 6,
    marginTop: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#f59e0b',
  },
  warningText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#92400e',
  },
  warningSubtext: {
    fontSize: 12,
    color: '#92400e',
    marginTop: 4,
  },
  photoButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 15,
  },
  photoButton: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 8,
    marginRight: 10,
    marginBottom: 10,
  },
  photoButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
  },
  photoGallery: {
    flexDirection: 'row',
    marginTop: 10,
  },
  photoItem: {
    marginRight: 10,
    position: 'relative',
  },
  photoThumb: {
    width: 80,
    height: 80,
    borderRadius: 8,
  },
  photoType: {
    fontSize: 10,
    textAlign: 'center',
    marginTop: 4,
    color: '#6b7280',
  },
  issueIndicator: {
    position: 'absolute',
    top: 5,
    right: 5,
    backgroundColor: '#ef4444',
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  issueText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  yoloSummary: {
    backgroundColor: '#fee2e2',
    padding: 12,
    borderRadius: 8,
    marginTop: 15,
  },
  yoloTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#991b1b',
    marginBottom: 8,
  },
  yoloIssue: {
    fontSize: 12,
    color: '#991b1b',
    marginLeft: 10,
    marginBottom: 4,
  },
  submitButton: {
    backgroundColor: '#059669',
    margin: 20,
    padding: 18,
    borderRadius: 10,
    alignItems: 'center',
  },
  submitButtonDisabled: {
    backgroundColor: '#9ca3af',
  },
  submitButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  errorText: {
    fontSize: 16,
    color: '#ef4444',
    textAlign: 'center',
    marginTop: 50,
  },
});
