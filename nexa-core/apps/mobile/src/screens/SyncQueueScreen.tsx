/**
 * Sync Queue Screen
 * Manage offline upload queue and sync status
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import NetInfo from '@react-native-community/netinfo';
import { theme } from '../theme';
import { RootState } from '../store';
import {
  QueueItem,
  updateItemStatus,
  removeFromQueue,
  clearCompletedItems,
  setSyncing,
} from '../store/slices/queueSlice';
import { setCurrentResult } from '../store/slices/auditSlice';
import { offlineQueue } from '../services/offlineQueue';
import { apiService } from '../services/api';

interface SyncQueueScreenProps {
  navigation: any;
}

export const SyncQueueScreen: React.FC<SyncQueueScreenProps> = ({ navigation }) => {
  const dispatch = useDispatch();
  const { items, syncing } = useSelector((state: RootState) => state.queue);
  const [isOnline, setIsOnline] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Monitor network status
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      const online = state.isConnected ?? false;
      setIsOnline(online);
      
      // Auto-sync when coming online
      if (online && !syncing && items.some(i => i.status === 'pending')) {
        handleSyncAll();
      }
    });
    return () => unsubscribe();
  }, [items, syncing]);

  // Sync all pending items
  const handleSyncAll = async () => {
    if (!isOnline) {
      Alert.alert('Offline', 'Cannot sync while offline');
      return;
    }

    const pendingItems = items.filter(i => i.status === 'pending');
    if (pendingItems.length === 0) {
      Alert.alert('Nothing to Sync', 'All items are already synced');
      return;
    }

    dispatch(setSyncing(true));

    for (const item of pendingItems) {
      try {
        // Update status to syncing
        dispatch(updateItemStatus({ id: item.id, status: 'syncing' }));

        // Upload based on file type
        let response;
        if (item.fileType === 'pdf') {
          response = await apiService.analyzeAudit(item.fileUri, item.fileName);
        } else {
          response = await apiService.analyzePhoto(item.fileUri, item.fileName);
        }

        // Mark as done
        dispatch(updateItemStatus({ id: item.id, status: 'done' }));
        
        // Update current result if this is the last item
        if (item === pendingItems[pendingItems.length - 1]) {
          dispatch(setCurrentResult(response));
        }
      } catch (error: any) {
        console.error(`Sync failed for ${item.id}:`, error);
        dispatch(updateItemStatus({
          id: item.id,
          status: 'error',
          error: error.message || 'Upload failed',
        }));
      }
    }

    dispatch(setSyncing(false));
    await offlineQueue.saveQueue(items);
  };

  // Sync single item
  const handleSyncItem = async (item: QueueItem) => {
    if (!isOnline) {
      Alert.alert('Offline', 'Cannot sync while offline');
      return;
    }

    try {
      dispatch(updateItemStatus({ id: item.id, status: 'syncing' }));

      let response;
      if (item.fileType === 'pdf') {
        response = await apiService.analyzeAudit(item.fileUri, item.fileName);
      } else {
        response = await apiService.analyzePhoto(item.fileUri, item.fileName);
      }

      dispatch(updateItemStatus({ id: item.id, status: 'done' }));
      dispatch(setCurrentResult(response));
      await offlineQueue.saveQueue(items);

      Alert.alert('Success', 'Item synced successfully', [
        { text: 'View Results', onPress: () => navigation.navigate('Results') },
        { text: 'OK' },
      ]);
    } catch (error: any) {
      console.error(`Sync failed for ${item.id}:`, error);
      dispatch(updateItemStatus({
        id: item.id,
        status: 'error',
        error: error.message || 'Upload failed',
      }));
      await offlineQueue.saveQueue(items);
      Alert.alert('Error', error.message || 'Failed to sync item');
    }
  };

  // Delete item from queue
  const handleDeleteItem = (item: QueueItem) => {
    Alert.alert(
      'Delete Item',
      `Remove "${item.fileName}" from queue?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            dispatch(removeFromQueue(item.id));
            await offlineQueue.saveQueue(items.filter(i => i.id !== item.id));
          },
        },
      ]
    );
  };

  // Clear all completed items
  const handleClearCompleted = () => {
    const completedCount = items.filter(i => i.status === 'done').length;
    if (completedCount === 0) {
      Alert.alert('No Completed Items', 'There are no completed items to clear');
      return;
    }

    Alert.alert(
      'Clear Completed',
      `Remove ${completedCount} completed item${completedCount !== 1 ? 's' : ''}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          onPress: async () => {
            dispatch(clearCompletedItems());
            await offlineQueue.saveQueue(items.filter(i => i.status !== 'done'));
          },
        },
      ]
    );
  };

  // Refresh queue
  const handleRefresh = async () => {
    setRefreshing(true);
    const savedQueue = await offlineQueue.loadQueue();
    if (savedQueue) {
      // Queue is already loaded in Redux, just refresh UI
    }
    setRefreshing(false);
  };

  // Get status color
  const getStatusColor = (status: QueueItem['status']) => {
    switch (status) {
      case 'pending':
        return theme.colors.warning;
      case 'syncing':
        return theme.colors.primary;
      case 'done':
        return theme.colors.success;
      case 'error':
        return theme.colors.danger;
    }
  };

  // Get status icon
  const getStatusIcon = (status: QueueItem['status']) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'syncing':
        return '🔄';
      case 'done':
        return '✅';
      case 'error':
        return '❌';
    }
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Render queue item
  const renderItem = ({ item }: { item: QueueItem }) => (
    <View style={styles.queueItem}>
      <View style={styles.itemHeader}>
        <View style={styles.itemInfo}>
          <Text style={styles.itemIcon}>
            {item.fileType === 'pdf' ? '📄' : '📷'}
          </Text>
          <View style={styles.itemDetails}>
            <Text style={styles.itemName} numberOfLines={1}>
              {item.fileName}
            </Text>
            <Text style={styles.itemMeta}>
              {formatFileSize(item.fileSize)} • {new Date(item.createdAt).toLocaleString()}
            </Text>
          </View>
        </View>
        
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
          <Text style={styles.statusIcon}>{getStatusIcon(item.status)}</Text>
          <Text style={styles.statusText}>{item.status.toUpperCase()}</Text>
        </View>
      </View>

      {item.error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>⚠️ {item.error}</Text>
        </View>
      )}

      <View style={styles.itemActions}>
        {item.status === 'pending' && (
          <TouchableOpacity
            style={[styles.actionButton, styles.syncButton]}
            onPress={() => handleSyncItem(item)}
            disabled={!isOnline || syncing}
          >
            <Text style={styles.actionButtonText}>Sync Now</Text>
          </TouchableOpacity>
        )}
        
        {item.status === 'error' && (
          <TouchableOpacity
            style={[styles.actionButton, styles.retryButton]}
            onPress={() => handleSyncItem(item)}
            disabled={!isOnline || syncing}
          >
            <Text style={styles.actionButtonText}>Retry</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[styles.actionButton, styles.deleteButton]}
          onPress={() => handleDeleteItem(item)}
          disabled={syncing}
        >
          <Text style={styles.actionButtonText}>Delete</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const pendingCount = items.filter(i => i.status === 'pending').length;
  const completedCount = items.filter(i => i.status === 'done').length;
  const errorCount = items.filter(i => i.status === 'error').length;

  return (
    <View style={styles.container}>
      {/* Network Status Banner */}
      {!isOnline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>📡 Offline - Items will sync when online</Text>
        </View>
      )}

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Sync Queue</Text>
        <View style={styles.stats}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{pendingCount}</Text>
            <Text style={styles.statLabel}>Pending</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{completedCount}</Text>
            <Text style={styles.statLabel}>Done</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{errorCount}</Text>
            <Text style={styles.statLabel}>Errors</Text>
          </View>
        </View>
      </View>

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionButton, styles.syncAllButton]}
          onPress={handleSyncAll}
          disabled={!isOnline || syncing || pendingCount === 0}
        >
          <Text style={styles.actionButtonText}>
            {syncing ? 'Syncing...' : `Sync All (${pendingCount})`}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionButton, styles.clearButton]}
          onPress={handleClearCompleted}
          disabled={completedCount === 0}
        >
          <Text style={styles.actionButtonText}>Clear Completed</Text>
        </TouchableOpacity>
      </View>

      {/* Queue List */}
      {items.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📦</Text>
          <Text style={styles.emptyText}>Queue is empty</Text>
          <Text style={styles.emptySubtext}>
            Uploads will appear here when offline
          </Text>
        </View>
      ) : (
        <FlatList
          data={items}
          renderItem={renderItem}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={theme.colors.primary}
            />
          }
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  offlineBanner: {
    backgroundColor: theme.colors.warning,
    padding: theme.spacing.sm,
  },
  offlineText: {
    color: '#fff',
    fontWeight: '600',
    textAlign: 'center',
  },
  header: {
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  title: {
    fontSize: theme.fontSizes.xlarge,
    fontWeight: '700',
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
  },
  stats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: theme.fontSizes.xlarge,
    fontWeight: '700',
    color: theme.colors.text,
  },
  statLabel: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
  actions: {
    flexDirection: 'row',
    padding: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  actionButton: {
    flex: 1,
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    borderRadius: theme.borderRadius.medium,
    alignItems: 'center',
  },
  syncAllButton: {
    backgroundColor: theme.colors.primary,
  },
  clearButton: {
    backgroundColor: theme.colors.textSecondary,
  },
  syncButton: {
    backgroundColor: theme.colors.primary,
  },
  retryButton: {
    backgroundColor: theme.colors.warning,
  },
  deleteButton: {
    backgroundColor: theme.colors.danger,
  },
  actionButtonText: {
    color: '#fff',
    fontSize: theme.fontSizes.medium,
    fontWeight: '600',
  },
  listContent: {
    padding: theme.spacing.md,
  },
  queueItem: {
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.medium,
    marginBottom: theme.spacing.md,
    ...theme.shadows.small,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: theme.spacing.sm,
  },
  itemInfo: {
    flexDirection: 'row',
    flex: 1,
    marginRight: theme.spacing.sm,
  },
  itemIcon: {
    fontSize: 32,
    marginRight: theme.spacing.sm,
  },
  itemDetails: {
    flex: 1,
  },
  itemName: {
    fontSize: theme.fontSizes.medium,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  itemMeta: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.small,
  },
  statusIcon: {
    marginRight: theme.spacing.xs,
  },
  statusText: {
    color: '#fff',
    fontSize: theme.fontSizes.small,
    fontWeight: '600',
  },
  errorContainer: {
    backgroundColor: '#ffe6e6',
    padding: theme.spacing.sm,
    borderRadius: theme.borderRadius.small,
    marginBottom: theme.spacing.sm,
  },
  errorText: {
    color: theme.colors.danger,
    fontSize: theme.fontSizes.small,
  },
  itemActions: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.xl,
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: theme.spacing.md,
  },
  emptyText: {
    fontSize: theme.fontSizes.xlarge,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  emptySubtext: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.textSecondary,
    textAlign: 'center',
  },
});
