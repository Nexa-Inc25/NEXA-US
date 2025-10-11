import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  FlatList,
  Alert,
} from 'react-native';

interface CrewStatus {
  id: string;
  name: string;
  foreman: string;
  status: 'active' | 'idle' | 'break' | 'completed';
  currentJob: string | null;
  location: string;
  members: number;
  progress: number;
  lastUpdate: Date;
}

interface JobPackage {
  id: string;
  name: string;
  priority: 'high' | 'medium' | 'low';
  crew: string | null;
  status: 'pending' | 'assigned' | 'in_progress' | 'completed';
  dueDate: Date;
  infractions: number;
  estimatedCost: number;
}

interface Metrics {
  totalCrews: number;
  activeCrews: number;
  jobsToday: number;
  completedToday: number;
  infractionsToday: number;
  safetyIncidents: number;
  budgetUtilization: number;
  onTimeCompletion: number;
}

export default function GeneralForemanDashboard() {
  const [crews, setCrews] = useState<CrewStatus[]>([]);
  const [jobPackages, setJobPackages] = useState<JobPackage[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<'crews' | 'jobs' | 'metrics'>('crews');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    // Simulated data - replace with API calls
    setTimeout(() => {
      setCrews([
        {
          id: '1',
          name: 'Crew Alpha',
          foreman: 'John Smith',
          status: 'active',
          currentJob: 'TAG-2 Pole Replacement',
          location: 'Stockton North',
          members: 4,
          progress: 65,
          lastUpdate: new Date(),
        },
        {
          id: '2',
          name: 'Crew Bravo',
          foreman: 'Mike Johnson',
          status: 'active',
          currentJob: 'Transformer Installation',
          location: 'Stockton South',
          members: 5,
          progress: 30,
          lastUpdate: new Date(),
        },
        {
          id: '3',
          name: 'Crew Charlie',
          foreman: 'Sarah Davis',
          status: 'break',
          currentJob: null,
          location: 'Base',
          members: 3,
          progress: 0,
          lastUpdate: new Date(),
        },
      ]);

      setJobPackages([
        {
          id: 'JP001',
          name: '07D-1 Cable Replacement',
          priority: 'high',
          crew: null,
          status: 'pending',
          dueDate: new Date(Date.now() + 86400000),
          infractions: 0,
          estimatedCost: 12500,
        },
        {
          id: 'JP002',
          name: 'Grounding System Upgrade',
          priority: 'medium',
          crew: 'Crew Alpha',
          status: 'in_progress',
          dueDate: new Date(Date.now() + 172800000),
          infractions: 1,
          estimatedCost: 8750,
        },
      ]);

      setMetrics({
        totalCrews: 8,
        activeCrews: 5,
        jobsToday: 12,
        completedToday: 7,
        infractionsToday: 2,
        safetyIncidents: 0,
        budgetUtilization: 78,
        onTimeCompletion: 92,
      });

      setLoading(false);
    }, 1000);
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadDashboardData().then(() => setRefreshing(false));
  };

  const assignJobToCrew = (jobId: string, crewId: string) => {
    Alert.alert(
      'Assign Job',
      `Assign job ${jobId} to ${crewId}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Assign',
          onPress: () => {
            // API call to assign job
            Alert.alert('Success', 'Job assigned successfully');
            onRefresh();
          },
        },
      ]
    );
  };

  const renderCrewCard = ({ item }: { item: CrewStatus }) => (
    <TouchableOpacity style={styles.crewCard}>
      <LinearGradient
        colors={item.status === 'active' ? ['#4CAF50', '#45a049'] : ['#9E9E9E', '#757575']}
        style={styles.crewStatus}
      >
        <Text style={styles.crewStatusText}>{item.status.toUpperCase()}</Text>
      </LinearGradient>
      
      <View style={styles.crewInfo}>
        <Text style={styles.crewName}>{item.name}</Text>
        <Text style={styles.foremanName}>
          <FontAwesome5 name="hard-hat" size={12} color="#666" /> {item.foreman}
        </Text>
        
        <View style={styles.crewDetails}>
          <View style={styles.detailRow}>
            <Ionicons name="people" size={16} color="#666" />
            <Text style={styles.detailText}>{item.members} members</Text>
          </View>
          
          <View style={styles.detailRow}>
            <Ionicons name="location" size={16} color="#666" />
            <Text style={styles.detailText}>{item.location}</Text>
          </View>
        </View>

        {item.currentJob && (
          <>
            <Text style={styles.jobText}>{item.currentJob}</Text>
            <View style={styles.progressBar}>
              <View style={[styles.progressFill, { width: `${item.progress}%` }]} />
            </View>
            <Text style={styles.progressText}>{item.progress}% Complete</Text>
          </>
        )}
      </View>
    </TouchableOpacity>
  );

  const renderJobCard = ({ item }: { item: JobPackage }) => (
    <TouchableOpacity style={styles.jobCard}>
      <View style={[styles.priorityBadge, { backgroundColor: getPriorityColor(item.priority) }]}>
        <Text style={styles.priorityText}>{item.priority.toUpperCase()}</Text>
      </View>
      
      <View style={styles.jobInfo}>
        <Text style={styles.jobName}>{item.name}</Text>
        <Text style={styles.jobId}>ID: {item.id}</Text>
        
        <View style={styles.jobDetails}>
          <Text style={styles.jobDetailText}>
            <Ionicons name="calendar" size={14} color="#666" /> Due: {item.dueDate.toLocaleDateString()}
          </Text>
          <Text style={styles.jobDetailText}>
            <FontAwesome5 name="dollar-sign" size={14} color="#666" /> Est: ${item.estimatedCost.toLocaleString()}
          </Text>
        </View>

        {item.infractions > 0 && (
          <View style={styles.warningBadge}>
            <MaterialIcons name="warning" size={16} color="#ff6b6b" />
            <Text style={styles.warningText}>{item.infractions} Infractions</Text>
          </View>
        )}

        {!item.crew && (
          <TouchableOpacity 
            style={styles.assignButton}
            onPress={() => assignJobToCrew(item.id, 'Crew Alpha')}
          >
            <Text style={styles.assignButtonText}>ASSIGN TO CREW</Text>
          </TouchableOpacity>
        )}
      </View>
    </TouchableOpacity>
  );

  const renderMetrics = () => (
    <ScrollView style={styles.metricsContainer}>
      <View style={styles.metricsGrid}>
        <MetricCard
          icon="groups"
          title="Active Crews"
          value={`${metrics?.activeCrews}/${metrics?.totalCrews}`}
          color="#4CAF50"
        />
        <MetricCard
          icon="assignment"
          title="Jobs Today"
          value={`${metrics?.completedToday}/${metrics?.jobsToday}`}
          color="#2196F3"
        />
        <MetricCard
          icon="warning"
          title="Infractions"
          value={metrics?.infractionsToday.toString() || '0'}
          color="#ff6b6b"
        />
        <MetricCard
          icon="health-and-safety"
          title="Safety"
          value={metrics?.safetyIncidents === 0 ? 'Clear' : metrics?.safetyIncidents.toString() || '0'}
          color={metrics?.safetyIncidents === 0 ? '#4CAF50' : '#ff6b6b'}
        />
        <MetricCard
          icon="attach-money"
          title="Budget Used"
          value={`${metrics?.budgetUtilization}%`}
          color="#FF9800"
        />
        <MetricCard
          icon="schedule"
          title="On Time"
          value={`${metrics?.onTimeCompletion}%`}
          color="#9C27B0"
        />
      </View>

      <View style={styles.chartContainer}>
        <Text style={styles.chartTitle}>Performance Trends</Text>
        {/* Add chart component here */}
        <View style={styles.chartPlaceholder}>
          <Text style={styles.chartPlaceholderText}>Chart Coming Soon</Text>
        </View>
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

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#1e3a8a" />
        <Text style={styles.loadingText}>Loading Dashboard...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#1e3a8a', '#2563eb']} style={styles.header}>
        <Text style={styles.headerTitle}>General Foreman Dashboard</Text>
        <Text style={styles.headerSubtitle}>PG&E Stockton Division</Text>
      </LinearGradient>

      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, selectedTab === 'crews' && styles.activeTab]}
          onPress={() => setSelectedTab('crews')}
        >
          <Ionicons name="people" size={20} color={selectedTab === 'crews' ? '#1e3a8a' : '#666'} />
          <Text style={[styles.tabText, selectedTab === 'crews' && styles.activeTabText]}>Crews</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, selectedTab === 'jobs' && styles.activeTab]}
          onPress={() => setSelectedTab('jobs')}
        >
          <MaterialIcons name="work" size={20} color={selectedTab === 'jobs' ? '#1e3a8a' : '#666'} />
          <Text style={[styles.tabText, selectedTab === 'jobs' && styles.activeTabText]}>Jobs</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, selectedTab === 'metrics' && styles.activeTab]}
          onPress={() => setSelectedTab('metrics')}
        >
          <Ionicons name="stats-chart" size={20} color={selectedTab === 'metrics' ? '#1e3a8a' : '#666'} />
          <Text style={[styles.tabText, selectedTab === 'metrics' && styles.activeTabText]}>Metrics</Text>
        </TouchableOpacity>
      </View>

      {selectedTab === 'crews' && (
        <FlatList
          data={crews}
          renderItem={renderCrewCard}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          contentContainerStyle={styles.listContent}
        />
      )}

      {selectedTab === 'jobs' && (
        <FlatList
          data={jobPackages}
          renderItem={renderJobCard}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          contentContainerStyle={styles.listContent}
        />
      )}

      {selectedTab === 'metrics' && renderMetrics()}
    </View>
  );
}

const MetricCard = ({ icon, title, value, color }: any) => (
  <View style={styles.metricCard}>
    <MaterialIcons name={icon} size={32} color={color} />
    <Text style={styles.metricValue}>{value}</Text>
    <Text style={styles.metricTitle}>{title}</Text>
  </View>
);

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
    padding: 20,
    paddingTop: 60,
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
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    gap: 5,
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
  listContent: {
    padding: 15,
  },
  crewCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    marginBottom: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    overflow: 'hidden',
  },
  crewStatus: {
    padding: 10,
    alignItems: 'center',
  },
  crewStatusText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  crewInfo: {
    padding: 15,
  },
  crewName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  foremanName: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  crewDetails: {
    flexDirection: 'row',
    marginTop: 10,
    gap: 20,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  detailText: {
    fontSize: 12,
    color: '#666',
  },
  jobText: {
    fontSize: 14,
    color: '#333',
    marginTop: 10,
    fontWeight: '500',
  },
  progressBar: {
    height: 8,
    backgroundColor: '#e0e0e0',
    borderRadius: 4,
    marginTop: 10,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
  },
  progressText: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
  },
  jobCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    marginBottom: 15,
    padding: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  priorityBadge: {
    position: 'absolute',
    top: 0,
    right: 0,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderBottomLeftRadius: 10,
    borderTopRightRadius: 10,
  },
  priorityText: {
    color: 'white',
    fontSize: 10,
    fontWeight: 'bold',
  },
  jobInfo: {
    flex: 1,
  },
  jobName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginRight: 60,
  },
  jobId: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
  },
  jobDetails: {
    flexDirection: 'row',
    gap: 20,
    marginTop: 10,
  },
  jobDetailText: {
    fontSize: 12,
    color: '#666',
  },
  warningBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 10,
  },
  warningText: {
    color: '#ff6b6b',
    fontSize: 12,
  },
  assignButton: {
    backgroundColor: '#1e3a8a',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 5,
    marginTop: 10,
    alignSelf: 'flex-start',
  },
  assignButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  metricsContainer: {
    flex: 1,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 15,
    gap: 10,
  },
  metricCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 15,
    width: '48%',
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  metricValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 10,
  },
  metricTitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
  },
  chartContainer: {
    backgroundColor: 'white',
    margin: 15,
    padding: 15,
    borderRadius: 10,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  chartTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  chartPlaceholder: {
    height: 200,
    backgroundColor: '#f5f5f5',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  chartPlaceholderText: {
    color: '#999',
  },
});
