import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';

export default function GeneralForemanDashboard() {
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1000);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>General Foreman Dashboard</Text>
        <Text style={styles.headerSubtitle}>PG&E Stockton Division</Text>
      </View>

      <ScrollView 
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Active Crews</Text>
          
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Crew Alpha</Text>
            <Text style={styles.cardText}>Foreman: John Smith</Text>
            <Text style={styles.cardText}>Status: Active</Text>
            <Text style={styles.cardText}>Job: TAG-2 Pole Replacement</Text>
            <Text style={styles.cardText}>Progress: 65%</Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Crew Bravo</Text>
            <Text style={styles.cardText}>Foreman: Mike Johnson</Text>
            <Text style={styles.cardText}>Status: Active</Text>
            <Text style={styles.cardText}>Job: Transformer Installation</Text>
            <Text style={styles.cardText}>Progress: 30%</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Metrics</Text>
          
          <View style={styles.metricsGrid}>
            <View style={styles.metricCard}>
              <Text style={styles.metricValue}>5/8</Text>
              <Text style={styles.metricLabel}>Active Crews</Text>
            </View>

            <View style={styles.metricCard}>
              <Text style={styles.metricValue}>7/12</Text>
              <Text style={styles.metricLabel}>Jobs Today</Text>
            </View>

            <View style={styles.metricCard}>
              <Text style={styles.metricValue}>2</Text>
              <Text style={styles.metricLabel}>Infractions</Text>
            </View>

            <View style={styles.metricCard}>
              <Text style={styles.metricValue}>92%</Text>
              <Text style={styles.metricLabel}>On Time</Text>
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pending Jobs</Text>
          
          <View style={styles.card}>
            <Text style={styles.cardTitle}>07D-1 Cable Replacement</Text>
            <Text style={styles.cardText}>Priority: High</Text>
            <Text style={styles.cardText}>Est. Cost: $12,500</Text>
            <TouchableOpacity style={styles.assignButton}>
              <Text style={styles.assignButtonText}>Assign to Crew</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#1e3a8a',
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
    color: 'rgba(255,255,255,0.9)',
    marginTop: 5,
  },
  content: {
    flex: 1,
  },
  section: {
    padding: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 15,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1e3a8a',
    marginBottom: 8,
  },
  cardText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  metricCard: {
    backgroundColor: 'white',
    borderRadius: 8,
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
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e3a8a',
  },
  metricLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  assignButton: {
    backgroundColor: '#1e3a8a',
    padding: 10,
    borderRadius: 6,
    marginTop: 10,
    alignItems: 'center',
  },
  assignButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
});
