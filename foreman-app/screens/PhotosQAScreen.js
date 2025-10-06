import React, { useState } from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  Image, 
  StyleSheet, 
  Alert, 
  ScrollView, 
  ActivityIndicator,
  SafeAreaView,
  StatusBar 
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';
import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';

const PhotosQAScreen = ({ route, navigation }) => {
  const [image, setImage] = useState(null);
  const [qaResult, setQaResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Get API URL from app.json config
  const API_URL = Constants.expoConfig?.extra?.API_URL || 'http://localhost:8000';

  const pickImage = async () => {
    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Denied', 'Camera access is required to take photos.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });
    
    if (!result.canceled) {
      setImage(result.assets[0].uri);
      setQaResult(null); // Clear previous results
    }
  };

  const pickFromGallery = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });
    
    if (!result.canceled) {
      setImage(result.assets[0].uri);
      setQaResult(null);
    }
  };

  const analyzePhoto = async () => {
    if (!image) {
      Alert.alert('No Image', 'Please select a photo first');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    
    // Create file object for upload
    formData.append('audit_file', {
      uri: image,
      type: 'image/jpeg',
      name: 'audit_photo.jpg',
    });

    try {
      const token = await SecureStore.getItemAsync('authToken');
      const response = await axios.post(
        `${API_URL}/analyze-audit/`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': token ? `Bearer ${token}` : undefined,
          },
          timeout: 30000, // 30 second timeout
        }
      );

      if (response.data.success) {
        setQaResult(response.data);
      }
    } catch (error) {
      console.error('Analysis error:', error);
      Alert.alert(
        'Analysis Failed',
        'Unable to analyze photo. The service may be offline or the image format is unsupported.',
        [
          { text: 'Retry', onPress: analyzePhoto },
          { text: 'Cancel', style: 'cancel' }
        ]
      );
    } finally {
      setLoading(false);
    }
  };

  const getRepealabilityColor = (repealable) => {
    return repealable === 'YES' ? '#4CAF50' : '#F44336';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#4CAF50';
    if (confidence >= 0.6) return '#FFC107';
    return '#F44336';
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.headerText}>Quality Assurance Analysis</Text>
          <Text style={styles.subHeader}>
            Analyze photos against PG&E specification standards
          </Text>
        </View>

        <View style={styles.imageSection}>
          {image ? (
            <View style={styles.imageContainer}>
              <Image source={{ uri: image }} style={styles.image} />
              <TouchableOpacity 
                style={styles.removeImageButton}
                onPress={() => { setImage(null); setQaResult(null); }}
              >
                <Text style={styles.removeImageText}>✕</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.imagePlaceholder}>
              <Text style={styles.placeholderIcon}>📷</Text>
              <Text style={styles.placeholderText}>No image selected</Text>
              <Text style={styles.placeholderSubtext}>Take a photo or select from gallery</Text>
            </View>
          )}
        </View>

        <View style={styles.actionButtons}>
          <TouchableOpacity 
            style={[styles.actionButton, styles.primaryButton]}
            onPress={pickImage}
            activeOpacity={0.8}
          >
            <Text style={styles.actionButtonText}>Take Photo</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={[styles.actionButton, styles.secondaryButton]}
            onPress={pickFromGallery}
            activeOpacity={0.8}
          >
            <Text style={styles.secondaryButtonText}>Choose from Gallery</Text>
          </TouchableOpacity>
        </View>

        {image && (
          <TouchableOpacity 
            style={[styles.analyzeButton, loading && styles.analyzeButtonDisabled]}
            onPress={analyzePhoto}
            disabled={loading}
            activeOpacity={0.8}
          >
            {loading ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <Text style={styles.analyzeButtonText}>Analyze with NEXA AI</Text>
            )}
          </TouchableOpacity>
        )}

        {qaResult && (
          <View style={styles.resultContainer}>
            <Text style={styles.resultHeader}>Analysis Results</Text>
            
            {qaResult.summary && (
              <View style={styles.summaryCard}>
                <View style={styles.summaryRow}>
                  <Text style={styles.summaryLabel}>Total Infractions</Text>
                  <Text style={styles.summaryValue}>{qaResult.summary.total_infractions}</Text>
                </View>
                <View style={styles.summaryRow}>
                  <Text style={styles.summaryLabel}>Repealable</Text>
                  <Text style={styles.summaryValue}>{qaResult.summary.repealable_count}</Text>
                </View>
                <View style={styles.summaryRow}>
                  <Text style={styles.summaryLabel}>Average Confidence</Text>
                  <Text style={styles.summaryValue}>{(qaResult.summary.average_confidence * 100).toFixed(1)}%</Text>
                </View>
              </View>
            )}

            {qaResult.analysis && qaResult.analysis.map((item, index) => (
              <View key={index} style={styles.infractionCard}>
                <View style={styles.infractionHeader}>
                  <Text style={styles.infractionNumber}>Infraction #{index + 1}</Text>
                  <View style={[styles.statusBadge, { backgroundColor: getRepealabilityColor(item.repealable) + '20' }]}>
                    <Text style={[styles.statusText, { color: getRepealabilityColor(item.repealable) }]}>
                      {item.repealable === 'YES' ? 'Repealable' : 'Valid'}
                    </Text>
                  </View>
                </View>
                
                <Text style={styles.infractionText}>{item.infraction}</Text>
                
                <View style={styles.metricsContainer}>
                  <View style={styles.metricItem}>
                    <Text style={styles.metricLabel}>Confidence</Text>
                    <View style={styles.confidenceBar}>
                      <View 
                        style={[
                          styles.confidenceFill,
                          { 
                            width: `${item.confidence * 100}%`,
                            backgroundColor: getConfidenceColor(item.confidence)
                          }
                        ]}
                      />
                    </View>
                    <Text style={styles.confidenceText}>{(item.confidence * 100).toFixed(0)}%</Text>
                  </View>
                </View>

                {item.reasons && item.reasons.length > 0 && (
                  <View style={styles.reasonsSection}>
                    <Text style={styles.reasonsTitle}>Supporting Evidence</Text>
                    {item.reasons.slice(0, 2).map((reason, idx) => (
                      <Text key={idx} style={styles.reasonText}>
                        • {reason.substring(0, 150)}...
                      </Text>
                    ))}
                  </View>
                )}

                {item.spec_refs && item.spec_refs.length > 0 && (
                  <View style={styles.specsSection}>
                    <Text style={styles.specText}>{item.spec_refs.join(', ')}</Text>
                  </View>
                )}
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 20,
    backgroundColor: '#00d4ff',
  },
  headerText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
  },
  subHeader: {
    fontSize: 14,
    color: 'white',
    marginTop: 5,
  },
  imageSection: {
    padding: 20,
    alignItems: 'center',
  },
  image: {
    width: '100%',
    height: 250,
    borderRadius: 10,
    resizeMode: 'cover',
  },
  imagePlaceholder: {
    width: '100%',
    height: 250,
    borderRadius: 10,
    backgroundColor: '#e0e0e0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    color: '#999',
    fontSize: 16,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
    marginBottom: 10,
  },
  analyzeButton: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  resultContainer: {
    padding: 20,
  },
  resultHeader: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  summaryCard: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
    elevation: 2,
  },
  summaryTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  infractionCard: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
    elevation: 2,
  },
  infractionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5,
  },
  infractionText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
  },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginVertical: 10,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#e0e0e0',
  },
  metric: {
    alignItems: 'center',
  },
  metricLabel: {
    fontSize: 12,
    color: '#999',
  },
  metricValue: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 2,
  },
  reasonsSection: {
    marginTop: 10,
  },
  reasonsTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  reasonText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 3,
  },
  specsSection: {
    marginTop: 10,
    padding: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 5,
  },
  specsTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 3,
  },
  specText: {
    fontSize: 11,
    color: '#666',
  },
});

export default PhotosQAScreen;
