// NEXA Field Crew Mobile App
// React Native app for field crews to complete jobs perfectly

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  TextInput,
  Alert,
  Platform,
  ActivityIndicator
} from 'react-native';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = 'https://nexa-us-pro.onrender.com';

const FieldCrewApp = () => {
  const [currentJob, setCurrentJob] = useState(null);
  const [jobStep, setJobStep] = useState('START');
  const [photos, setPhotos] = useState({
    before: [],
    during: [],
    after: []
  });
  const [jobData, setJobData] = useState({
    pm_number: '',
    notification_number: '',
    crew_lead: '',
    crew_members: [],
    materials: [],
    test_results: {}
  });
  const [loading, setLoading] = useState(false);
  const [checklist, setChecklist] = useState([]);

  // Start a new job
  const startJob = async () => {
    if (!jobData.pm_number) {
      Alert.alert('Error', 'Please enter PM Number');
      return;
    }

    setLoading(true);
    try {
      // Get GPS location
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Error', 'Location permission required');
        return;
      }
      const location = await Location.getCurrentPositionAsync({});

      // Initialize job
      const job = {
        id: `JOB_${jobData.pm_number}_${Date.now()}`,
        pm_number: jobData.pm_number,
        crew_lead: jobData.crew_lead,
        start_time: new Date().toISOString(),
        location: {
          lat: location.coords.latitude,
          lng: location.coords.longitude
        },
        status: 'IN_PROGRESS'
      };

      setCurrentJob(job);
      setJobStep('BEFORE_PHOTOS');
      
      // Generate checklist
      const checklistItems = [
        'Take BEFORE photos (3 minimum)',
        'Verify PM number matches work order',
        'Document existing conditions',
        'Install equipment per spec',
        'Verify clearances',
        'Clamp multiple guy wires if applicable',
        'Complete installation',
        'Perform required tests',
        'Take AFTER photos (3 minimum)',
        'Get crew signatures',
        'Clean up job site'
      ];
      setChecklist(checklistItems.map(item => ({ task: item, done: false })));
      
      await AsyncStorage.setItem('currentJob', JSON.stringify(job));
    } catch (error) {
      Alert.alert('Error', 'Failed to start job');
    }
    setLoading(false);
  };

  // Take a photo with validation
  const takePhoto = async (photoType) => {
    try {
      // Request camera permission
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Error', 'Camera permission required');
        return;
      }

      // Get current location for GPS tagging
      const location = await Location.getCurrentPositionAsync({});

      // Launch camera
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        exif: true
      });

      if (!result.canceled) {
        const photo = {
          uri: result.assets[0].uri,
          timestamp: new Date().toISOString(),
          gps: {
            lat: location.coords.latitude,
            lng: location.coords.longitude
          },
          type: photoType
        };

        // Add to photos array
        const updatedPhotos = { ...photos };
        updatedPhotos[photoType].push(photo);
        setPhotos(updatedPhotos);

        // Check if minimum photos met
        const minRequired = photoType === 'during' ? 0 : 3;
        if (updatedPhotos[photoType].length >= minRequired) {
          Alert.alert(
            'Photos Complete',
            `All required ${photoType} photos captured`,
            [{ text: 'Continue', onPress: () => moveToNextStep(photoType) }]
          );
        } else {
          Alert.alert(
            'Photo Saved',
            `${updatedPhotos[photoType].length}/${minRequired} ${photoType} photos taken`
          );
        }
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to take photo');
    }
  };

  // Move to next step in workflow
  const moveToNextStep = (currentPhotoType) => {
    switch (currentPhotoType) {
      case 'before':
        setJobStep('WORK_IN_PROGRESS');
        break;
      case 'during':
        setJobStep('WORK_IN_PROGRESS');
        break;
      case 'after':
        setJobStep('COMPLETE_JOB');
        break;
      default:
        break;
    }
  };

  // Complete the job and generate as-built
  const completeJob = async () => {
    setLoading(true);
    
    try {
      // Validate all required fields
      const missing = [];
      if (!jobData.notification_number) missing.push('Notification Number');
      if (photos.before.length < 3) missing.push('Before Photos (need 3)');
      if (photos.after.length < 3) missing.push('After Photos (need 3)');
      if (!jobData.ec_tag_signed) missing.push('EC Tag Signature');
      
      if (missing.length > 0) {
        Alert.alert('Cannot Complete', `Missing: ${missing.join(', ')}`);
        setLoading(false);
        return;
      }

      // Prepare completion data
      const completionData = {
        ...currentJob,
        ...jobData,
        photos,
        completion_time: new Date().toISOString(),
        total_hours: calculateHours(),
        test_results: {
          tension: 'Pass',
          grounding: 'Pass',
          clearance: 'Pass'
        },
        ec_tag_signed: true,
        materials_list: jobData.materials
      };

      // Send to backend for as-built generation
      const response = await fetch(`${API_URL}/api/field/complete-job`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(completionData)
      });

      if (response.ok) {
        const result = await response.json();
        
        Alert.alert(
          'Job Complete!',
          `As-built generated with ${result.compliance_score}% compliance\n\nPackage ID: ${result.package_id}\n\nReady for QA submission`,
          [
            {
              text: 'View Package',
              onPress: () => viewAsBuiltPackage(result.package_id)
            },
            {
              text: 'Start New Job',
              onPress: () => resetJob()
            }
          ]
        );
        
        // Clear current job
        await AsyncStorage.removeItem('currentJob');
      } else {
        Alert.alert('Error', 'Failed to complete job');
      }
    } catch (error) {
      Alert.alert('Error', 'Connection failed - saved locally');
      // Save locally for later sync
      await AsyncStorage.setItem('pendingJob', JSON.stringify(completionData));
    }
    
    setLoading(false);
  };

  // Calculate hours worked
  const calculateHours = () => {
    if (!currentJob) return 0;
    const start = new Date(currentJob.start_time);
    const end = new Date();
    return Math.round((end - start) / (1000 * 60 * 60) * 10) / 10; // Round to 0.1 hours
  };

  // View generated as-built package
  const viewAsBuiltPackage = (packageId) => {
    // Would open PDF viewer or preview
    Alert.alert('Package Ready', `As-built ${packageId} ready for QA review`);
  };

  // Reset for new job
  const resetJob = () => {
    setCurrentJob(null);
    setJobStep('START');
    setPhotos({ before: [], during: [], after: [] });
    setJobData({
      pm_number: '',
      notification_number: '',
      crew_lead: '',
      crew_members: [],
      materials: [],
      test_results: {}
    });
    setChecklist([]);
  };

  // Render different screens based on job step
  const renderContent = () => {
    switch (jobStep) {
      case 'START':
        return (
          <View style={styles.container}>
            <Text style={styles.title}>NEXA Field Crew</Text>
            <Text style={styles.subtitle}>Start New Job</Text>
            
            <TextInput
              style={styles.input}
              placeholder="PM Number (8 digits)"
              value={jobData.pm_number}
              onChangeText={(text) => setJobData({ ...jobData, pm_number: text })}
              keyboardType="numeric"
              maxLength={8}
            />
            
            <TextInput
              style={styles.input}
              placeholder="Crew Lead Name"
              value={jobData.crew_lead}
              onChangeText={(text) => setJobData({ ...jobData, crew_lead: text })}
            />
            
            <TouchableOpacity 
              style={styles.button}
              onPress={startJob}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Start Job</Text>
              )}
            </TouchableOpacity>
          </View>
        );

      case 'BEFORE_PHOTOS':
        return (
          <View style={styles.container}>
            <Text style={styles.title}>Before Photos</Text>
            <Text style={styles.subtitle}>
              Take {3 - photos.before.length} more photos
            </Text>
            
            <View style={styles.photoGrid}>
              {photos.before.map((photo, index) => (
                <Image 
                  key={index}
                  source={{ uri: photo.uri }}
                  style={styles.thumbnail}
                />
              ))}
            </View>
            
            <TouchableOpacity 
              style={styles.button}
              onPress={() => takePhoto('before')}
            >
              <Text style={styles.buttonText}>Take Photo</Text>
            </TouchableOpacity>
            
            {photos.before.length >= 3 && (
              <TouchableOpacity 
                style={[styles.button, styles.successButton]}
                onPress={() => setJobStep('WORK_IN_PROGRESS')}
              >
                <Text style={styles.buttonText}>Continue to Work</Text>
              </TouchableOpacity>
            )}
          </View>
        );

      case 'WORK_IN_PROGRESS':
        return (
          <View style={styles.container}>
            <Text style={styles.title}>Work In Progress</Text>
            <Text style={styles.subtitle}>PM {jobData.pm_number}</Text>
            
            <ScrollView style={styles.checklistContainer}>
              {checklist.map((item, index) => (
                <TouchableOpacity 
                  key={index}
                  style={styles.checklistItem}
                  onPress={() => {
                    const updated = [...checklist];
                    updated[index].done = !updated[index].done;
                    setChecklist(updated);
                  }}
                >
                  <Text style={[
                    styles.checklistText,
                    item.done && styles.checklistDone
                  ]}>
                    {item.done ? '✓' : '○'} {item.task}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            
            <TextInput
              style={styles.input}
              placeholder="Notification Number"
              value={jobData.notification_number}
              onChangeText={(text) => setJobData({ ...jobData, notification_number: text })}
              keyboardType="numeric"
            />
            
            <TouchableOpacity 
              style={styles.button}
              onPress={() => takePhoto('after')}
            >
              <Text style={styles.buttonText}>
                Take After Photos ({photos.after.length}/3)
              </Text>
            </TouchableOpacity>
            
            {photos.after.length >= 3 && (
              <TouchableOpacity 
                style={[styles.button, styles.successButton]}
                onPress={() => setJobStep('COMPLETE_JOB')}
              >
                <Text style={styles.buttonText}>Review & Complete</Text>
              </TouchableOpacity>
            )}
          </View>
        );

      case 'COMPLETE_JOB':
        return (
          <View style={styles.container}>
            <Text style={styles.title}>Complete Job</Text>
            <Text style={styles.subtitle}>Review and Submit</Text>
            
            <View style={styles.summary}>
              <Text style={styles.summaryText}>PM: {jobData.pm_number}</Text>
              <Text style={styles.summaryText}>
                Hours Worked: {calculateHours()}
              </Text>
              <Text style={styles.summaryText}>
                Before Photos: {photos.before.length} ✓
              </Text>
              <Text style={styles.summaryText}>
                After Photos: {photos.after.length} ✓
              </Text>
              <Text style={styles.summaryText}>
                Checklist: {checklist.filter(i => i.done).length}/{checklist.length}
              </Text>
            </View>
            
            <View style={styles.signatureBox}>
              <Text style={styles.signatureText}>EC Tag Digital Signature</Text>
              <TouchableOpacity
                style={styles.signButton}
                onPress={() => setJobData({ ...jobData, ec_tag_signed: true })}
              >
                <Text style={styles.buttonText}>
                  {jobData.ec_tag_signed ? '✓ Signed' : 'Sign EC Tag'}
                </Text>
              </TouchableOpacity>
            </View>
            
            <TouchableOpacity 
              style={[
                styles.button, 
                styles.successButton,
                !jobData.ec_tag_signed && styles.disabledButton
              ]}
              onPress={completeJob}
              disabled={!jobData.ec_tag_signed || loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>
                  Generate As-Built & Submit
                </Text>
              )}
            </TouchableOpacity>
          </View>
        );

      default:
        return null;
    }
  };

  return (
    <ScrollView style={styles.screen}>
      {renderContent()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  container: {
    padding: 20,
    paddingTop: 60
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10
  },
  subtitle: {
    fontSize: 18,
    color: '#666',
    marginBottom: 30
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    fontSize: 16,
    marginBottom: 15,
    borderWidth: 1,
    borderColor: '#ddd'
  },
  button: {
    backgroundColor: '#007AFF',
    borderRadius: 10,
    padding: 15,
    alignItems: 'center',
    marginTop: 10
  },
  successButton: {
    backgroundColor: '#34C759'
  },
  disabledButton: {
    opacity: 0.5
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600'
  },
  photoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 20
  },
  thumbnail: {
    width: 100,
    height: 100,
    margin: 5,
    borderRadius: 10
  },
  checklistContainer: {
    maxHeight: 300,
    marginBottom: 20
  },
  checklistItem: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 8,
    marginBottom: 8
  },
  checklistText: {
    fontSize: 16,
    color: '#333'
  },
  checklistDone: {
    color: '#34C759',
    textDecorationLine: 'line-through'
  },
  summary: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 10,
    marginBottom: 20
  },
  summaryText: {
    fontSize: 16,
    color: '#333',
    marginBottom: 10
  },
  signatureBox: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 10,
    marginBottom: 20,
    alignItems: 'center'
  },
  signatureText: {
    fontSize: 16,
    color: '#666',
    marginBottom: 10
  },
  signButton: {
    backgroundColor: '#FF9500',
    paddingHorizontal: 30,
    paddingVertical: 10,
    borderRadius: 8
  }
});

export default FieldCrewApp;
