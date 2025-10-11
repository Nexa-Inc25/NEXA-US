import React, { useEffect, useState } from 'react';
import { View, Text, Button, FlatList } from 'react-native';
import Constants from 'expo-constants';
import * as Network from 'expo-network';
import { useAuth, fetchWithAuth } from '../auth/AuthProvider';
import { initDb, getCursor, setCursor, upsertTable, readJobs } from '../db/db';

export default function TodayScreen() {
  const { accessToken } = useAuth();
  const [jobs, setJobs] = useState([]);
  const apiBase = Constants?.expoConfig?.extra?.API_BASE_URL;

  useEffect(() => {
    initDb();
    readJobs(setJobs);
  }, []);

  const sync = async () => {
    try {
      const state = await Network.getNetworkStateAsync();
      if (!state.isConnected) {
        console.log('Offline; skipping sync.');
        return;
      }
      getCursor('updated_at', async (since) => {
        const url = since ? `${apiBase}/sync?since=${encodeURIComponent(since)}` : `${apiBase}/sync`;
        const data = await fetchWithAuth(url, {}, accessToken);
        upsertTable('jobs', data.jobs || []);
        upsertTable('materials', data.materials || []);
        upsertTable('pins', data.pins || []);
        upsertTable('checklist', data.checklist || []);
        setCursor('updated_at', data.now);
        readJobs(setJobs);
      });
    } catch (err) {
      console.error('Sync error:', err.message);
    }
  };

  return (
    <View style={{ flex: 1 }}>
      <Button title="Sync" onPress={sync} />
      <FlatList
        data={jobs}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={{ paddingVertical: 8, borderBottomWidth: 1, borderColor: '#eee' }}>
            <Text style={{ fontSize: 16 }}>{item.name}</Text>
            <Text style={{ color: '#888' }}>Profit: {item.profit_chip}</Text>
          </View>
        )}
      />
    </View>
  );
}
