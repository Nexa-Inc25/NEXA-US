/**
 * Photos & QA Screen
 * Upload audits/photos, view analysis results, manage offline queue
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { Camera } from 'expo-camera';
import NetInfo from '@react-native-community/netinfo';
import { theme } from '../theme';
import { RootState } from '../store';
import { addToQueue } from '../store/slices/queueSlice';
import { setLoading, setCurrentResult, setError } from '../store/slices/auditSlice';
import { apiService } from '../services/api';
import { offlineQueue } from '../services/offlineQueue';

interface PhotosQAScreenProps {
  navigation: any;
}

export const PhotosQAScreen: React.FC<PhotosQAScreenProps> = ({ navigation }) => {
  const dispatch = useDispatch();
  const { loading, error } = useSelector((state: RootState) => state.audits);
  const { items: queueItems } = useSelector((state: RootState) => state.queue);
  
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [isOnline, setIsOnline] = useState(true);
  const [capturedPhotos, setCapturedPhotos] = useState<any[]>([]);
  const [currentJob, setCurrentJob] = useState<any>(null);

  // Request camera permissions on mount
  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  // Monitor network status
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOnline(state.isConnected ?? false);
    });
    return () => unsubscribe();
  }, []);

  // Handle PDF upload
  const handlePickPDF = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        copyToCacheDirectory: true,
      });

      if (result.canceled) return;

      const file = result.assets[0];
      
      if (isOnline) {
        // Upload immediately
        dispatch(setLoading(true));
        try {
          const response = await apiService.analyzeAudit(file.uri, file.name);
          dispatch(setCurrentResult(response));
          navigation.navigate('Results');
        } catch (err: any) {
          dispatch(setError(err.message || 'Upload failed'));
          Alert.alert('Error', 'Failed to analyze audit. Added to offline queue.');
          await queueUpload(file.uri, file.name, 'pdf', file.size || 0);
        }
      } else {
        // Queue for later
        await queueUpload(file.uri, file.name, 'pdf', file.size || 0);
        Alert.alert('Offline', 'Audit queued for upload when online');
      }
    } catch (err) {
      console.error('PDF picker error:', err);
      Alert.alert('Error', 'Failed to pick PDF');
    }
  };

  // Handle photo from camera
  const handleTakePhoto = async () => {
    if (hasPermission === false) {
      Alert.alert('Permission Denied', 'Camera access is required');
      return;
    }

    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        allowsEditing: false,
      });

      if (result.canceled) return;

      const photo = result.assets[0];
      const fileName = `photo_${Date.now()}.jpg`;

      if (isOnline) {
        // Upload immediately
        dispatch(setLoading(true));
        try {
          const response = await apiService.analyzePhoto(photo.uri, fileName);
          dispatch(setCurrentResult(response));
          navigation.navigate('Results');
        } catch (err: any) {
          dispatch(setError(err.message || 'Upload failed'));
          Alert.alert('Error', 'Failed to analyze photo. Added to offline queue.');
          await queueUpload(photo.uri, fileName, 'photo', photo.fileSize || 0);
        }
      } else {
        // Queue for later
        await queueUpload(photo.uri, fileName, 'photo', photo.fileSize || 0);
        Alert.alert('Offline', 'Photo queued for upload when online');
      }
    } catch (err) {
      console.error('Camera error:', err);
      Alert.alert('Error', 'Failed to take photo');
    }
  };

  // Handle photo from gallery
  const handlePickPhoto = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        allowsEditing: false,
      });

      if (result.canceled) return;

      const photo = result.assets[0];
      const fileName = `photo_${Date.now()}.jpg`;

      if (isOnline) {
        // Upload immediately
        dispatch(setLoading(true));
        try {
          const response = await apiService.analyzePhoto(photo.uri, fileName);
          dispatch(setCurrentResult(response));
          navigation.navigate('Results');
        } catch (err: any) {
          dispatch(setError(err.message || 'Upload failed'));
          Alert.alert('Error', 'Failed to analyze photo. Added to offline queue.');
          await queueUpload(photo.uri, fileName, 'photo', photo.fileSize || 0);
        }
      } else {
        // Queue for later
        await queueUpload(photo.uri, fileName, 'photo', photo.fileSize || 0);
        Alert.alert('Offline', 'Photo queued for upload when online');
      }
    } catch (err) {
      console.error('Photo picker error:', err);
      Alert.alert('Error', 'Failed to pick photo');
    }
  };

  // Queue upload for offline sync
  const queueUpload = async (
    fileUri: string,
    fileName: string,
    fileType: 'pdf' | 'photo',
    fileSize: number
  ) => {
    const queueItem = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      fileUri,
      fileName,
      fileType,
      fileSize,
    };
    
    dispatch(addToQueue(queueItem));
    await offlineQueue.saveQueue([...queueItems, queueItem]);
  };

  // Submit as-built with all captured photos
  const handleSubmitAsBuilt = async () => {
    if (capturedPhotos.length === 0) {
      Alert.alert('No Photos', 'Please take photos before submitting as-built');
      return;
    }

    if (!currentJob) {
      Alert.alert('No Job', 'Please scan a job QR code first');
      return;
    }

    dispatch(setLoading(true));
    try {
      const formData = new FormData();
      formData.append('job_id', currentJob.id);
      formData.append('pm_number', currentJob.pm_number || '');
      formData.append('location', currentJob.location || '');
      formData.append('foreman_name', currentJob.foreman_name || 'John Smith');
      formData.append('crew_number', currentJob.crew_number || 'CREW-001');
      
      capturedPhotos.forEach((photo, index) => {
        formData.append('photos', {
          uri: photo.uri,
          name: `photo_${index}.jpg`,
          type: 'image/jpeg'
        } as any);
      });

      const response = await apiService.fillAsBuilt(formData);
      
      Alert.alert(
        'As-Built Filled!', 
        `PDF: ${response.pdf_url}\nGo-backs: ${response.go_backs.length}\nReady for QA: ${response.ready_for_qa ? 'Yes' : 'No'}`,
        [
          { text: 'View Results', onPress: () => {
            dispatch(setCurrentResult(response));
            navigation.navigate('Results');
            setCapturedPhotos([]); // Clear photos after submission
          }},
          { text: 'OK', style: 'cancel' }
        ]
      );
    } catch (err: any) {
      dispatch(setError(err.message || 'Failed to fill as-built'));
      Alert.alert('Error', 'Failed to fill as-built. Please try again.');
    } finally {
      dispatch(setLoading(false));
    }
  };

  const pendingCount = queueItems.filter(i => i.status === 'pending').length;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Network Status Banner */}
      {!isOnline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>📡 Offline Mode - Uploads will queue</Text>
        </View>
      )}

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Upload Audit or Photo</Text>
        <Text style={styles.subtitle}>
          Field crews: Capture infractions for instant analysis
        </Text>
      </View>

      {/* Upload Options */}
      <View style={styles.uploadSection}>
        <TouchableOpacity
          style={[styles.uploadButton, styles.primaryButton]}
          onPress={handlePickPDF}
          disabled={loading}
        >
          <Text style={styles.uploadIcon}>📄</Text>
          <Text style={styles.uploadButtonText}>Upload PDF Audit</Text>
          <Text style={styles.uploadButtonSubtext}>Select from files</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.uploadButton, styles.secondaryButton]}
          onPress={handleTakePhoto}
          disabled={loading || hasPermission === false}
        >
          <Text style={styles.uploadIcon}>📷</Text>
          <Text style={styles.uploadButtonText}>Take Photo</Text>
          <Text style={styles.uploadButtonSubtext}>Camera capture</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.uploadButton, styles.secondaryButton]}
          onPress={handlePickPhoto}
          disabled={loading}
        >
          <Text style={styles.uploadIcon}>🖼️</Text>
          <Text style={styles.uploadButtonText}>Choose Photo</Text>
          <Text style={styles.uploadButtonSubtext}>From gallery</Text>
        </TouchableOpacity>
      </View>

      {/* Loading State */}
      {loading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
          <Text style={styles.loadingText}>Analyzing document...</Text>
        </View>
      )}

      {/* Error State */}
      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
        </View>
      )}

      {/* Offline Queue Summary */}
      {pendingCount > 0 && (
        <TouchableOpacity
          style={styles.queueSummary}
          onPress={() => navigation.navigate('SyncQueue')}
        >
          <View style={styles.queueHeader}>
            <Text style={styles.queueTitle}>📦 Offline Queue</Text>
            <Text style={styles.queueBadge}>{pendingCount}</Text>
          </View>
          <Text style={styles.queueSubtext}>
            {pendingCount} item{pendingCount !== 1 ? 's' : ''} waiting to sync
          </Text>
          <Text style={styles.queueLink}>View Queue →</Text>
        </TouchableOpacity>
      )}

      {/* Info Section */}
      <View style={styles.infoSection}>
        <Text style={styles.infoTitle}>💡 How it works</Text>
        <Text style={styles.infoText}>
          1. Upload a PDF audit or take a photo of infractions{'\n'}
          2. AI analyzes against PG&E specs and pricing{'\n'}
          3. Get instant cost impact with labor & equipment{'\n'}
          4. Review repealable vs. true infractions
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    padding: theme.spacing.md,
  },
  offlineBanner: {
    backgroundColor: theme.colors.warning,
    padding: theme.spacing.sm,
    borderRadius: theme.borderRadius.medium,
    marginBottom: theme.spacing.md,
  },
  offlineText: {
    color: '#fff',
    fontWeight: '600',
    textAlign: 'center',
  },
  header: {
    marginBottom: theme.spacing.lg,
  },
  title: {
    fontSize: theme.fontSizes.xlarge,
    fontWeight: '700',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  subtitle: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.textSecondary,
  },
  uploadSection: {
    marginBottom: theme.spacing.lg,
  },
  uploadButton: {
    padding: theme.spacing.lg,
    borderRadius: theme.borderRadius.medium,
    marginBottom: theme.spacing.md,
    alignItems: 'center',
    ...theme.shadows.medium,
  },
  primaryButton: {
    backgroundColor: theme.colors.primary,
  },
  secondaryButton: {
    backgroundColor: theme.colors.surface,
    borderWidth: 2,
    borderColor: theme.colors.primary,
  },
  uploadIcon: {
    fontSize: 48,
    marginBottom: theme.spacing.sm,
  },
  uploadButtonText: {
    fontSize: theme.fontSizes.large,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  uploadButtonSubtext: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
  },
  loadingContainer: {
    padding: theme.spacing.xl,
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.medium,
    marginBottom: theme.spacing.md,
  },
  loadingText: {
    marginTop: theme.spacing.md,
    fontSize: theme.fontSizes.medium,
    color: theme.colors.textSecondary,
  },
  errorContainer: {
    padding: theme.spacing.md,
    backgroundColor: '#ffe6e6',
    borderRadius: theme.borderRadius.medium,
    marginBottom: theme.spacing.md,
  },
  errorText: {
    color: theme.colors.danger,
    fontSize: theme.fontSizes.medium,
  },
  queueSummary: {
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.medium,
    borderLeftWidth: 4,
    borderLeftColor: theme.colors.warning,
    marginBottom: theme.spacing.lg,
    ...theme.shadows.small,
  },
  queueHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  queueTitle: {
    fontSize: theme.fontSizes.large,
    fontWeight: '600',
    color: theme.colors.text,
  },
  queueBadge: {
    backgroundColor: theme.colors.warning,
    color: '#fff',
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.large,
    fontSize: theme.fontSizes.small,
    fontWeight: '700',
  },
  queueSubtext: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
  },
  queueLink: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.primary,
    fontWeight: '600',
  },
  infoSection: {
    padding: theme.spacing.md,
    backgroundColor: theme.colors.primaryLight + '20',
    borderRadius: theme.borderRadius.medium,
  },
  infoTitle: {
    fontSize: theme.fontSizes.large,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  infoText: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    lineHeight: 24,
  },
});
