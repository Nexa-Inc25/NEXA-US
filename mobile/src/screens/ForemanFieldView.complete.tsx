import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  TextInput,
  RefreshControl,
  ActivityIndicator,
  Alert,
  Modal,
} from 'react-native';

interface Job {
  id: string;
  name: string;
  location: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed';
  assignedBy: string;
  dueDate: Date;
  description: string;
  crew: string[];
}

interface TimeEntry {
  id: string;
  date: Date;
  hours: number;
  jobId: string;
  notes: string;
}

export default function ForemanFieldView() {
  const [selectedTab, setSelectedTab] = useState<'jobs' | 'time' | 'safety' | 'photos'>('jobs');
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showTimeModal, setShowTimeModal] = useState(false);
  const [showSafetyModal, setShowSafetyModal] = useState(false);
  const [timeHours, setTimeHours] = useState('');
  const [timeNotes, setTimeNotes] = useState('');
  const [safetyChecks, setSafetyChecks] = useState({
    ppe: false,
    hazards: false,
    permits: false,
    briefing: false,
  });

  useEffect(() => {
    loadForemanData();
  }, []);

  const loadForemanData = async () => {
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setJobs([
        {
          id: 'J001',
          name: 'TAG-2 Pole Replacement',
          location: 'Stockton North - Grid 42B',
          priority: 'high',
          status: 'in_progress',
          assignedBy: 'John Smith (GF)',
          dueDate: new Date(Date.now() + 86400000),
          description: 'Replace deteriorated pole with new TAG-2 rated pole. Check guy wires and ground connections.',
          crew: ['Mike Johnson', 'Tom Wilson', 'Steve Brown'],
        },
        {
          id: 'J002',
          name: 'Transformer Installation',
          location: 'Stockton South - Grid 18A',
          priority: 'medium',
          status: 'pending',
          assignedBy: 'John Smith (GF)',
          dueDate: new Date(Date.now() + 172800000),
          description: 'Install new 50kVA transformer. Coordinate with switching center for outage.',
          crew: ['Mike Johnson', 'Tom Wilson'],
        },
      ]);
      
      setCurrentJob({
        id: 'J001',
        name: 'TAG-2 Pole Replacement',
        location: 'Stockton North - Grid 42B',
        priority: 'high',
        status: 'in_progress',
        assignedBy: 'John Smith (GF)',
        dueDate: new Date(Date.now() + 86400000),
        description: 'Replace deteriorated pole with new TAG-2 rated pole. Check guy wires and ground connections.',
        crew: ['Mike Johnson', 'Tom Wilson', 'Steve Brown'],
      });

      setTimeEntries([
        { id: 'T001', date: new Date(), hours: 3.5, jobId: 'J001', notes: 'Site preparation and safety setup' },
        { id: 'T002', date: new Date(Date.now() - 86400000), hours: 8, jobId: 'J001', notes: 'Old pole removal' },
      ]);

      setLoading(false);
    }, 1000);
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadForemanData().then(() => setRefreshing(false));
  };

  const updateJobStatus = (jobId: string, newStatus: 'pending' | 'in_progress' | 'completed') => {
    Alert.alert(
      'Update Status',
      `Change job status to ${newStatus}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Update',
          onPress: () => {
            setJobs(jobs.map(job => 
              job.id === jobId ? { ...job, status: newStatus } : job
            ));
            Alert.alert('Success', 'Job status updated');
          },
        },
      ]
    );
  };

  const submitTimeEntry = () => {
    if (!timeHours || !currentJob) return;
    
    const newEntry: TimeEntry = {
      id: `T${Date.now()}`,
      date: new Date(),
      hours: parseFloat(timeHours),
      jobId: currentJob.id,
      notes: timeNotes,
    };
    
    setTimeEntries([newEntry, ...timeEntries]);
    setShowTimeModal(false);
    setTimeHours('');
    setTimeNotes('');
    Alert.alert('Success', 'Time entry submitted');
  };

  const submitSafetyReport = () => {
    const allChecked = Object.values(safetyChecks).every(v => v);
    if (!allChecked) {
      Alert.alert('Incomplete', 'Please complete all safety checks');
      return;
    }
    
    setShowSafetyModal(false);
    setSafetyChecks({ ppe: false, hazards: false, permits: false, briefing: false });
    Alert.alert('Success', 'Safety report submitted');
  };

  const renderJobsTab = () => (
    <ScrollView style={styles.tabContent}>
      {currentJob && (
        <View style={styles.currentJobCard}>
          <View style={[styles.priorityIndicator, { backgroundColor: getPriorityColor(currentJob.priority) }]} />
          <View style={styles.jobHeader}>
            <Text style={styles.currentJobTitle}>Current Job</Text>
            <TouchableOpacity 
              style={[styles.statusBadge, { backgroundColor: getStatusColor(currentJob.status) }]}
              onPress={() => {
                const nextStatus = currentJob.status === 'pending' ? 'in_progress' : 
                                 currentJob.status === 'in_progress' ? 'completed' : 'pending';
                updateJobStatus(currentJob.id, nextStatus);
              }}
            >
              <Text style={styles.statusText}>{currentJob.status.replace('_', ' ').toUpperCase()}</Text>
            </TouchableOpacity>
          </View>
          
          <Text style={styles.jobName}>{currentJob.name}</Text>
          <Text style={styles.jobLocation}>{currentJob.location}</Text>
          <Text style={styles.jobDescription}>{currentJob.description}</Text>
          
          <View style={styles.jobMeta}>
            <View style={styles.metaItem}>
              <Text style={styles.metaLabel}>Assigned By:</Text>
              <Text style={styles.metaValue}>{currentJob.assignedBy}</Text>
            </View>
            <View style={styles.metaItem}>
              <Text style={styles.metaLabel}>Due:</Text>
              <Text style={styles.metaValue}>{currentJob.dueDate.toLocaleDateString()}</Text>
            </View>
          </View>

          <View style={styles.crewSection}>
            <Text style={styles.crewTitle}>Crew ({currentJob.crew.length} members)</Text>
            {currentJob.crew.map((member, index) => (
              <Text key={index} style={styles.crewMember}>• {member}</Text>
            ))}
          </View>
        </View>
      )}

      <Text style={styles.sectionTitle}>Upcoming Jobs</Text>
      {jobs.filter(j => j.id !== currentJob?.id).map(job => (
        <TouchableOpacity 
          key={job.id} 
          style={styles.jobCard}
          onPress={() => setCurrentJob(job)}
        >
          <View style={[styles.priorityIndicator, { backgroundColor: getPriorityColor(job.priority) }]} />
          <View style={styles.jobCardContent}>
            <Text style={styles.jobCardName}>{job.name}</Text>
            <Text style={styles.jobCardLocation}>{job.location}</Text>
            <Text style={styles.jobCardDue}>Due: {job.dueDate.toLocaleDateString()}</Text>
          </View>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );

  const renderTimeTab = () => (
    <ScrollView style={styles.tabContent}>
      <TouchableOpacity 
        style={styles.primaryButton}
        onPress={() => setShowTimeModal(true)}
      >
        <Text style={styles.primaryButtonText}>Log Time Entry</Text>
      </TouchableOpacity>

      <View style={styles.summaryCard}>
        <Text style={styles.summaryTitle}>Today's Hours</Text>
        <Text style={styles.summaryValue}>
          {timeEntries
            .filter(t => t.date.toDateString() === new Date().toDateString())
            .reduce((sum, t) => sum + t.hours, 0)
            .toFixed(1)} hours
        </Text>
      </View>

      <View style={styles.summaryCard}>
        <Text style={styles.summaryTitle}>Week Total</Text>
        <Text style={styles.summaryValue}>
          {timeEntries.reduce((sum, t) => sum + t.hours, 0).toFixed(1)} hours
        </Text>
      </View>

      <Text style={styles.sectionTitle}>Recent Entries</Text>
      {timeEntries.map(entry => (
        <View key={entry.id} style={styles.timeCard}>
          <View style={styles.timeCardHeader}>
            <Text style={styles.timeCardDate}>{entry.date.toLocaleDateString()}</Text>
            <Text style={styles.timeCardHours}>{entry.hours} hours</Text>
          </View>
          <Text style={styles.timeCardNotes}>{entry.notes}</Text>
        </View>
      ))}
    </ScrollView>
  );

  const renderSafetyTab = () => (
    <ScrollView style={styles.tabContent}>
      <TouchableOpacity 
        style={styles.primaryButton}
        onPress={() => setShowSafetyModal(true)}
      >
        <Text style={styles.primaryButtonText}>Complete Safety Check</Text>
      </TouchableOpacity>

      <View style={[styles.summaryCard, { backgroundColor: '#4CAF50' }]}>
        <Text style={[styles.summaryTitle, { color: 'white' }]}>Safety Status</Text>
        <Text style={[styles.summaryValue, { color: 'white' }]}>All Clear</Text>
      </View>

      <Text style={styles.sectionTitle}>Safety Requirements</Text>
      <View style={styles.safetyCard}>
        <Text style={styles.safetyItem}>✓ Hard hats required</Text>
        <Text style={styles.safetyItem}>✓ Safety glasses required</Text>
        <Text style={styles.safetyItem}>✓ Gloves required</Text>
        <Text style={styles.safetyItem}>✓ Steel-toed boots required</Text>
      </View>

      <Text style={styles.sectionTitle}>Hazards</Text>
      <View style={styles.safetyCard}>
        <Text style={styles.hazardItem}>⚠ Overhead power lines</Text>
        <Text style={styles.hazardItem}>⚠ Underground utilities marked</Text>
        <Text style={styles.hazardItem}>⚠ Traffic control required</Text>
      </View>
    </ScrollView>
  );

  const renderPhotosTab = () => (
    <ScrollView style={styles.tabContent}>
      <TouchableOpacity style={styles.primaryButton}>
        <Text style={styles.primaryButtonText}>Take Photo</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[styles.primaryButton, { backgroundColor: '#666' }]}>
        <Text style={styles.primaryButtonText}>Upload Document</Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Recent Photos</Text>
      <View style={styles.photoGrid}>
        {[1, 2, 3, 4].map(i => (
          <View key={i} style={styles.photoPlaceholder}>
            <Text style={styles.photoPlaceholderText}>Photo {i}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#ff6b6b';
      case 'medium': return '#FF9800';
      case 'low': return '#4CAF50';
      default: return '#9E9E9E';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#4CAF50';
      case 'in_progress': return '#2196F3';
      case 'pending': return '#FF9800';
      default: return '#9E9E9E';
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#1e3a8a" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Foreman Dashboard</Text>
          <Text style={styles.headerSubtitle}>Mike Johnson - Crew Alpha</Text>
        </View>
        <TouchableOpacity style={styles.syncButton} onPress={onRefresh}>
          <Text style={styles.syncButtonText}>SYNC</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.tabBar}>
        {(['jobs', 'time', 'safety', 'photos'] as const).map(tab => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, selectedTab === tab && styles.activeTab]}
            onPress={() => setSelectedTab(tab)}
          >
            <Text style={[styles.tabText, selectedTab === tab && styles.activeTabText]}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView 
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {selectedTab === 'jobs' && renderJobsTab()}
        {selectedTab === 'time' && renderTimeTab()}
        {selectedTab === 'safety' && renderSafetyTab()}
        {selectedTab === 'photos' && renderPhotosTab()}
      </ScrollView>

      {/* Time Entry Modal */}
      <Modal
        visible={showTimeModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowTimeModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Log Time Entry</Text>
            
            <Text style={styles.inputLabel}>Hours Worked</Text>
            <TextInput
              style={styles.input}
              value={timeHours}
              onChangeText={setTimeHours}
              keyboardType="numeric"
              placeholder="8.0"
            />
            
            <Text style={styles.inputLabel}>Notes</Text>
            <TextInput
              style={[styles.input, { height: 80 }]}
              value={timeNotes}
              onChangeText={setTimeNotes}
              multiline
              placeholder="Work performed..."
            />
            
            <View style={styles.modalButtons}>
              <TouchableOpacity 
                style={[styles.modalButton, styles.cancelButton]}
                onPress={() => setShowTimeModal(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={[styles.modalButton, styles.submitButton]}
                onPress={submitTimeEntry}
              >
                <Text style={styles.submitButtonText}>Submit</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Safety Check Modal */}
      <Modal
        visible={showSafetyModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowSafetyModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Daily Safety Check</Text>
            
            {Object.entries(safetyChecks).map(([key, value]) => (
              <TouchableOpacity
                key={key}
                style={styles.checkboxRow}
                onPress={() => setSafetyChecks({ ...safetyChecks, [key]: !value })}
              >
                <View style={[styles.checkbox, value && styles.checkboxChecked]}>
                  {value && <Text style={styles.checkmark}>✓</Text>}
                </View>
                <Text style={styles.checkboxLabel}>
                  {key === 'ppe' ? 'PPE worn by all crew' :
                   key === 'hazards' ? 'Hazards identified and mitigated' :
                   key === 'permits' ? 'Permits in place' :
                   'Safety briefing completed'}
                </Text>
              </TouchableOpacity>
            ))}
            
            <View style={styles.modalButtons}>
              <TouchableOpacity 
                style={[styles.modalButton, styles.cancelButton]}
                onPress={() => setShowSafetyModal(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={[styles.modalButton, styles.submitButton]}
                onPress={submitSafetyReport}
              >
                <Text style={styles.submitButtonText}>Submit</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
  },
  header: {
    backgroundColor: '#1e3a8a',
    padding: 20,
    paddingTop: 60,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 5,
  },
  syncButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 5,
  },
  syncButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: 'white',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  tab: {
    flex: 1,
    paddingVertical: 15,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 3,
    borderBottomColor: '#1e3a8a',
  },
  tabText: {
    color: '#666',
    fontSize: 14,
  },
  activeTabText: {
    color: '#1e3a8a',
    fontWeight: 'bold',
  },
  tabContent: {
    padding: 15,
  },
  currentJobCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    marginBottom: 20,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  priorityIndicator: {
    height: 5,
    width: '100%',
  },
  jobHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    paddingBottom: 0,
  },
  currentJobTitle: {
    fontSize: 12,
    color: '#666',
    textTransform: 'uppercase',
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 5,
  },
  statusText: {
    color: 'white',
    fontSize: 10,
    fontWeight: 'bold',
  },
  jobName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    paddingHorizontal: 15,
    paddingTop: 10,
  },
  jobLocation: {
    fontSize: 14,
    color: '#666',
    paddingHorizontal: 15,
    paddingTop: 5,
  },
  jobDescription: {
    fontSize: 14,
    color: '#333',
    paddingHorizontal: 15,
    paddingTop: 10,
    lineHeight: 20,
  },
  jobMeta: {
    flexDirection: 'row',
    padding: 15,
    gap: 30,
  },
  metaItem: {
    flex: 1,
  },
  metaLabel: {
    fontSize: 12,
    color: '#666',
  },
  metaValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
    marginTop: 2,
  },
  crewSection: {
    padding: 15,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  crewTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  crewMember: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
    marginTop: 10,
  },
  jobCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    marginBottom: 10,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  jobCardContent: {
    padding: 15,
  },
  jobCardName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  jobCardLocation: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  jobCardDue: {
    fontSize: 12,
    color: '#999',
    marginTop: 5,
  },
  primaryButton: {
    backgroundColor: '#1e3a8a',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 15,
  },
  primaryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  summaryCard: {
    backgroundColor: '#1e3a8a',
    padding: 20,
    borderRadius: 10,
    marginBottom: 15,
    alignItems: 'center',
  },
  summaryTitle: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 14,
  },
  summaryValue: {
    color: 'white',
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 5,
  },
  timeCard: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
  },
  timeCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  timeCardDate: {
    fontSize: 14,
    color: '#666',
  },
  timeCardHours: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#1e3a8a',
  },
  timeCardNotes: {
    fontSize: 14,
    color: '#333',
  },
  safetyCard: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
  },
  safetyItem: {
    fontSize: 14,
    color: '#333',
    marginBottom: 10,
  },
  hazardItem: {
    fontSize: 14,
    color: '#FF9800',
    marginBottom: 10,
  },
  photoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  photoPlaceholder: {
    width: '48%',
    height: 150,
    backgroundColor: '#ddd',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  photoPlaceholderText: {
    color: '#999',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 20,
    width: '90%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 20,
  },
  inputLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    padding: 10,
    fontSize: 14,
    marginBottom: 15,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 20,
  },
  modalButton: {
    flex: 1,
    padding: 12,
    borderRadius: 5,
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: '#f5f5f5',
  },
  cancelButtonText: {
    color: '#666',
    fontWeight: 'bold',
  },
  submitButton: {
    backgroundColor: '#1e3a8a',
  },
  submitButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: '#1e3a8a',
    borderRadius: 4,
    marginRight: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxChecked: {
    backgroundColor: '#1e3a8a',
  },
  checkmark: {
    color: 'white',
    fontWeight: 'bold',
  },
  checkboxLabel: {
    flex: 1,
    fontSize: 14,
    color: '#333',
  },
});
