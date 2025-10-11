/**
 * Offline Queue Management Service
 * Handles AsyncStorage persistence and sync logic
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { store } from '../store';
import { 
  QueueItem, 
  loadQueue, 
  updateItemStatus, 
  incrementRetryCount,
  setSyncing 
} from '../store/slices/queueSlice';
import { analyzeAuditWithRetry } from './api';
import { setCurrentResult, addResult } from '../store/slices/auditSlice';

const QUEUE_STORAGE_KEY = '@nexa_upload_queue';
const MAX_RETRIES = 3;

/**
 * Load queue from AsyncStorage on app start
 */
export const loadQueueFromStorage = async (): Promise<void> => {
  try {
    const saved = await AsyncStorage.getItem(QUEUE_STORAGE_KEY);
    if (saved) {
      const items: QueueItem[] = JSON.parse(saved);
      store.dispatch(loadQueue(items));
      console.log(`[Offline] Loaded ${items.length} items from storage`);
    }
  } catch (error) {
    console.error('[Offline] Failed to load queue:', error);
  }
};

/**
 * Save queue to AsyncStorage
 */
export const saveQueueToStorage = async (): Promise<void> => {
  try {
    const state = store.getState();
    const items = state.queue.items;
    await AsyncStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(items));
    console.log(`[Offline] Saved ${items.length} items to storage`);
  } catch (error) {
    console.error('[Offline] Failed to save queue:', error);
  }
};

/**
 * Sync pending items in queue
 */
export const syncQueue = async (): Promise<void> => {
  const state = store.getState();
  const pendingItems = state.queue.items.filter(
    item => item.status === 'pending' || item.status === 'error'
  );

  if (pendingItems.length === 0) {
    console.log('[Offline] No pending items to sync');
    return;
  }

  // Check network connectivity
  const netInfo = await NetInfo.fetch();
  if (!netInfo.isConnected) {
    console.log('[Offline] No network connection, skipping sync');
    return;
  }

  console.log(`[Offline] Syncing ${pendingItems.length} pending items`);
  store.dispatch(setSyncing(true));

  for (const item of pendingItems) {
    // Skip if already retried too many times
    if (item.retryCount >= MAX_RETRIES) {
      console.log(`[Offline] Skipping ${item.id} - max retries reached`);
      continue;
    }

    try {
      // Update status to syncing
      store.dispatch(updateItemStatus({ id: item.id, status: 'syncing' }));
      
      // Upload and analyze
      console.log(`[Offline] Uploading ${item.fileName}...`);
      const result = await analyzeAuditWithRetry(
        item.fileUri,
        item.fileName,
        item.fileType,
        MAX_RETRIES - item.retryCount
      );

      // Success - update status and add result
      store.dispatch(updateItemStatus({ id: item.id, status: 'done' }));
      store.dispatch(setCurrentResult(result));
      store.dispatch(addResult(result));
      
      console.log(`[Offline] Successfully synced ${item.fileName}`);
    } catch (error) {
      // Failed - increment retry count and update status
      console.error(`[Offline] Failed to sync ${item.fileName}:`, error);
      store.dispatch(incrementRetryCount(item.id));
      store.dispatch(updateItemStatus({ 
        id: item.id, 
        status: 'error',
        error: error instanceof Error ? error.message : 'Upload failed'
      }));
    }
  }

  store.dispatch(setSyncing(false));
  
  // Save updated queue to storage
  await saveQueueToStorage();
  
  console.log('[Offline] Sync complete');
};

/**
 * Setup network listener for auto-sync
 */
export const setupNetworkListener = (): (() => void) => {
  const unsubscribe = NetInfo.addEventListener(state => {
    console.log('[Offline] Network state changed:', state.isConnected);
    
    if (state.isConnected) {
      // Network restored - trigger sync
      console.log('[Offline] Network restored, triggering sync...');
      syncQueue();
    }
  });

  return unsubscribe;
};

/**
 * Check if device is online
 */
export const isOnline = async (): Promise<boolean> => {
  const netInfo = await NetInfo.fetch();
  return netInfo.isConnected || false;
};

/**
 * Clear completed items from queue
 */
export const clearCompletedFromStorage = async (): Promise<void> => {
  const state = store.getState();
  const activeItems = state.queue.items.filter(item => item.status !== 'done');
  await AsyncStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(activeItems));
  console.log('[Offline] Cleared completed items from storage');
};
