import React, { useState, useEffect } from 'react';
import { View, Text, Button, StyleSheet, ScrollView, Alert, ActivityIndicator } from 'react-native';
import axios from 'axios';
import Constants from 'expo-constants';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

const CloseoutScreen = ({ route, navigation }) => {
  const [closeoutData, setCloseoutData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pdfGenerated, setPdfGenerated] = useState(false);
  
  const API_URL = Constants.expoConfig?.extra?.API_URL || 'http://localhost:8000';

  // Mock data for demo - replace with actual job data from WatermelonDB
  const mockAnalysisData = [
    {
      infraction: "Missing proper marking on transformer pad location",
      validity: "NO",
      repealable: "YES",
      confidence: 0.92,
      reasons: ["No specific requirement in PG&E spec book section 022168"],
      spec_refs: ["022168 - Page 12", "043816 - Page 3"]
    },
    {
      infraction: "Incorrect clearance for high-voltage equipment",
      validity: "YES",
      repealable: "NO",
      confidence: 0.88,
      reasons: ["Violates UG-1 specifications requiring 1-1/2 inch clearance"],
      spec_refs: ["UG-1 - Page 45", "043817 - Page 7"]
    },
    {
      infraction: "No alignment with marking tags requirement",
      validity: "NO",
      repealable: "YES",
      confidence: 0.85,
      reasons: ["Spec section 033582 allows flexibility in tag placement"],
      spec_refs: ["033582 - Page 8"]
    }
  ];

  const generateCloseout = async () => {
    setLoading(true);
    
    try {
      const response = await axios.post(
        `${API_URL}/closeout/generate`,
        {
          analysis: mockAnalysisData,
          user_id: "foreman_user",
          analysis_date: new Date().toISOString(),
          analysis_depth: "Detailed"
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          responseType: 'blob',
          timeout: 30000,
        }
      );

      // Save PDF to device
      const pdfUri = `${FileSystem.documentDirectory}closeout_${Date.now()}.pdf`;
      await FileSystem.writeAsStringAsync(pdfUri, response.data, {
        encoding: FileSystem.EncodingType.Base64,
      });

      setPdfGenerated(true);
      setCloseoutData({
        uri: pdfUri,
        analysis: mockAnalysisData,
        generatedAt: new Date().toISOString()
      });

      Alert.alert('Success', 'Closeout PDF generated successfully!');
    } catch (error) {
      console.error('Closeout generation error:', error);
      Alert.alert(
        'Generation Failed',
        'Unable to generate closeout. Check your connection and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const sharePdf = async () => {
    if (!closeoutData?.uri) return;
    
    const isAvailable = await Sharing.isAvailableAsync();
    if (isAvailable) {
      await Sharing.shareAsync(closeoutData.uri, {
        mimeType: 'application/pdf',
        dialogTitle: 'Share Closeout Report',
      });
    } else {
      Alert.alert('Sharing not available', 'Unable to share on this device');
    }
  };

  const calculateStats = () => {
    if (!mockAnalysisData.length) return { total: 0, repealable: 0, valid: 0 };
    
    const total = mockAnalysisData.length;
    const repealable = mockAnalysisData.filter(item => item.repealable === 'YES').length;
    const valid = mockAnalysisData.filter(item => item.validity === 'YES').length;
    const avgConfidence = mockAnalysisData.reduce((acc, item) => acc + item.confidence, 0) / total;
    
    return { total, repealable, valid, avgConfidence };
  };

  const stats = calculateStats();

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>QA Audit Closeout</Text>
        <Text style={styles.subHeader}>
          Generate comprehensive closeout reports with PG&E spec validation
        </Text>
      </View>

      <View style={styles.statsContainer}>
        <Text style={styles.statsTitle}>Analysis Overview</Text>
        
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.total}</Text>
            <Text style={styles.statLabel}>Total Infractions</Text>
          </View>
          
          <View style={styles.statCard}>
            <Text style={[styles.statValue, styles.repealableText]}>{stats.repealable}</Text>
            <Text style={styles.statLabel}>Repealable</Text>
          </View>
          
          <View style={styles.statCard}>
            <Text style={[styles.statValue, styles.validText]}>{stats.valid}</Text>
            <Text style={styles.statLabel}>Valid</Text>
          </View>
          
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{(stats.avgConfidence * 100).toFixed(0)}%</Text>
            <Text style={styles.statLabel}>Avg Confidence</Text>
          </View>
        </View>
      </View>

      <View style={styles.infractionsList}>
        <Text style={styles.listTitle}>Infractions Summary</Text>
        
        {mockAnalysisData.map((item, index) => (
          <View key={index} style={styles.infractionItem}>
            <View style={styles.infractionHeader}>
              <Text style={styles.infractionNumber}>#{index + 1}</Text>
              <View style={styles.statusBadge}>
                <Text style={[
                  styles.statusText,
                  item.repealable === 'YES' ? styles.repealable : styles.notRepealable
                ]}>
                  {item.repealable === 'YES' ? 'Repealable' : 'Valid'}
                </Text>
              </View>
            </View>
            
            <Text style={styles.infractionDescription}>
              {item.infraction}
            </Text>
            
            <View style={styles.confidenceBar}>
              <View 
                style={[
                  styles.confidenceFill,
                  { 
                    width: `${item.confidence * 100}%`,
                    backgroundColor: item.confidence > 0.8 ? '#4CAF50' : 
                                   item.confidence > 0.6 ? '#FFC107' : '#F44336'
                  }
                ]}
              />
            </View>
            <Text style={styles.confidenceText}>
              Confidence: {(item.confidence * 100).toFixed(0)}%
            </Text>
            
            <Text style={styles.specRef}>
              Spec Refs: {item.spec_refs.join(', ')}
            </Text>
          </View>
        ))}
      </View>

      <View style={styles.actionSection}>
        <Button
          title={loading ? "Generating..." : "📄 Generate Closeout PDF"}
          onPress={generateCloseout}
          disabled={loading}
        />
        
        {pdfGenerated && (
          <>
            <View style={styles.successMessage}>
              <Text style={styles.successText}>✅ PDF Generated Successfully!</Text>
              <Text style={styles.timestampText}>
                {new Date(closeoutData.generatedAt).toLocaleString()}
              </Text>
            </View>
            
            <View style={styles.shareButton}>
              <Button
                title="📤 Share PDF"
                onPress={sharePdf}
              />
            </View>
          </>
        )}
      </View>

      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#00d4ff" />
          <Text style={styles.loadingText}>Generating closeout report...</Text>
        </View>
      )}
    </ScrollView>
  );
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
  statsContainer: {
    padding: 20,
  },
  statsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    alignItems: 'center',
    elevation: 2,
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
  },
  repealableText: {
    color: '#4CAF50',
  },
  validText: {
    color: '#F44336',
  },
  infractionsList: {
    padding: 20,
  },
  listTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  infractionItem: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    elevation: 2,
  },
  infractionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  infractionNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 15,
  },
  statusText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  repealable: {
    color: '#4CAF50',
  },
  notRepealable: {
    color: '#F44336',
  },
  infractionDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
  },
  confidenceBar: {
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    marginBottom: 5,
    overflow: 'hidden',
  },
  confidenceFill: {
    height: '100%',
    borderRadius: 3,
  },
  confidenceText: {
    fontSize: 11,
    color: '#999',
    marginBottom: 5,
  },
  specRef: {
    fontSize: 11,
    color: '#999',
    fontStyle: 'italic',
  },
  actionSection: {
    padding: 20,
  },
  successMessage: {
    backgroundColor: '#E8F5E9',
    padding: 15,
    borderRadius: 10,
    marginTop: 15,
    alignItems: 'center',
  },
  successText: {
    fontSize: 16,
    color: '#4CAF50',
    fontWeight: 'bold',
  },
  timestampText: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
  },
  shareButton: {
    marginTop: 10,
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: 'white',
    marginTop: 10,
    fontSize: 16,
  },
});

export default CloseoutScreen;
