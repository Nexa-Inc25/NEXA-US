import React, { useEffect, useState } from 'react';
import { 
  View, 
  Text, 
  FlatList, 
  StyleSheet, 
  TouchableOpacity,
  StatusBar,
  SafeAreaView,
  ActivityIndicator
} from 'react-native';
import Constants from 'expo-constants';

const TodayScreen = ({ navigation }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const subscriptionTier = Constants.expoConfig?.extra?.SUBSCRIPTION_TIER || 'enterprise';
  const subscriptionCost = Constants.expoConfig?.extra?.SUBSCRIPTION_COST || '$500/user/month';

  useEffect(() => {
    // Mock job data - replace with WatermelonDB
    setTimeout(() => {
      setJobs([
        { id: '1', title: 'Pre-trip Inspection', status: 'pending', time: '7:00 AM' },
        { id: '2', title: 'PG&E Substation #4521', status: 'active', time: '8:30 AM' },
        { id: '3', title: 'Transformer Installation', status: 'completed', time: '2:00 PM' },
        { id: '4', title: 'QA Audit - Site 7', status: 'review', time: '4:30 PM' }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const getStatusColor = (status) => {
    switch(status) {
      case 'active': return '#4682B4';
      case 'completed': return '#10B981';
      case 'review': return '#F59E0B';
      default: return '#9CA3AF';
    }
  };

  const getStatusText = (status) => {
    switch(status) {
      case 'active': return 'In Progress';
      case 'completed': return 'Completed';
      case 'review': return 'Needs Review';
      default: return 'Pending';
    }
  };

  const renderJob = ({ item }) => (
    <TouchableOpacity 
      style={styles.jobCard}
      onPress={() => navigation.navigate('PhotosQA', { jobId: item.id, jobTitle: item.title })}
      activeOpacity={0.7}
    >
      <View style={[styles.statusIndicator, { backgroundColor: getStatusColor(item.status) }]} />
      <View style={styles.jobContent}>
        <View style={styles.jobHeader}>
          <Text style={styles.jobTitle}>{item.title}</Text>
          <Text style={styles.jobTime}>{item.time}</Text>
        </View>
        <View style={styles.jobFooter}>
          <View style={styles.statusBadge}>
            <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
              {getStatusText(item.status)}
            </Text>
          </View>
          <Text style={styles.arrow}>→</Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />
      
      {/* Premium Header */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <View>
            <Text style={styles.greeting}>Good {new Date().getHours() < 12 ? 'Morning' : 'Afternoon'}</Text>
            <Text style={styles.headerTitle}>Today's Schedule</Text>
          </View>
          <View style={styles.subscriptionBadge}>
            <Text style={styles.subscriptionTier}>{subscriptionTier.toUpperCase()}</Text>
            <Text style={styles.subscriptionCost}>{subscriptionCost}</Text>
          </View>
        </View>
        <Text style={styles.headerDate}>
          {new Date().toLocaleDateString('en-US', { 
            weekday: 'long', 
            month: 'long', 
            day: 'numeric',
            year: 'numeric'
          })}
        </Text>
      </View>

      {/* Stats Cards */}
      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <Text style={styles.statNumber}>4</Text>
          <Text style={styles.statLabel}>Active Jobs</Text>
        </View>
        <View style={[styles.statCard, styles.statCardCenter]}>
          <Text style={styles.statNumber}>92%</Text>
          <Text style={styles.statLabel}>Compliance</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statNumber}>1.2k</Text>
          <Text style={styles.statLabel}>API Calls</Text>
        </View>
      </View>

      {/* Job List */}
      <View style={styles.listContainer}>
        <Text style={styles.sectionTitle}>Job Schedule</Text>
        {loading ? (
          <ActivityIndicator size="large" color="#4682B4" style={styles.loader} />
        ) : (
          <FlatList
            data={jobs}
            renderItem={renderJob}
            keyExtractor={item => item.id}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          />
        )}
      </View>

      {/* Quick Action Button */}
      <TouchableOpacity 
        style={styles.floatingButton}
        onPress={() => navigation.navigate('Closeout')}
        activeOpacity={0.8}
      >
        <Text style={styles.floatingButtonText}>Generate Closeout</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  header: {
    padding: 16,
    backgroundColor: '#F8FAFC',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  greeting: {
    fontSize: 14,
    color: '#5A7A9A',
    fontWeight: '400',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#2D3748',
    marginTop: 4,
  },
  headerDate: {
    fontSize: 14,
    color: '#5A7A9A',
    fontWeight: '500',
  },
  subscriptionBadge: {
    backgroundColor: '#4682B4',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  subscriptionTier: {
    fontSize: 10,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  subscriptionCost: {
    fontSize: 11,
    color: '#FFFFFF',
    fontWeight: '500',
    marginTop: 2,
  },
  statsContainer: {
    flexDirection: 'row',
    padding: 16,
    paddingBottom: 8,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    padding: 16,
    borderRadius: 4,
    alignItems: 'center',
  },
  statCardCenter: {
    marginHorizontal: 8,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4682B4',
  },
  statLabel: {
    fontSize: 12,
    color: '#5A7A9A',
    fontWeight: '500',
    marginTop: 4,
  },
  listContainer: {
    flex: 1,
    padding: 16,
    paddingTop: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2D3748',
    marginBottom: 16,
  },
  listContent: {
    paddingBottom: 80,
  },
  jobCard: {
    flexDirection: 'row',
    backgroundColor: '#F8FAFC',
    borderRadius: 4,
    marginBottom: 8,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  statusIndicator: {
    width: 4,
  },
  jobContent: {
    flex: 1,
    padding: 16,
  },
  jobHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  jobTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2D3748',
    flex: 1,
    marginRight: 8,
  },
  jobTime: {
    fontSize: 14,
    color: '#5A7A9A',
    fontWeight: '500',
  },
  jobFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusBadge: {
    backgroundColor: 'transparent',
  },
  statusText: {
    fontSize: 14,
    fontWeight: '500',
  },
  arrow: {
    fontSize: 20,
    color: '#5A7A9A',
    fontWeight: '400',
  },
  loader: {
    marginTop: 50,
  },
  floatingButton: {
    position: 'absolute',
    bottom: 24,
    left: 16,
    right: 16,
    backgroundColor: '#4682B4',
    paddingVertical: 16,
    borderRadius: 4,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  floatingButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
  }
});

export default TodayScreen;
