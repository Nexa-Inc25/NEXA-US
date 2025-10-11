/**
 * Redux Slice for Offline Upload Queue
 * Manages pending uploads and sync status
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface QueueItem {
  id: string;
  fileUri: string;
  fileName: string;
  fileType: 'pdf' | 'photo';
  fileSize: number;
  status: 'pending' | 'syncing' | 'done' | 'error';
  createdAt: string;
  syncedAt?: string;
  error?: string;
  retryCount: number;
}

interface QueueState {
  items: QueueItem[];
  syncing: boolean;
}

const initialState: QueueState = {
  items: [],
  syncing: false,
};

const queueSlice = createSlice({
  name: 'queue',
  initialState,
  reducers: {
    addToQueue: (state, action: PayloadAction<Omit<QueueItem, 'status' | 'createdAt' | 'retryCount'>>) => {
      const newItem: QueueItem = {
        ...action.payload,
        status: 'pending',
        createdAt: new Date().toISOString(),
        retryCount: 0,
      };
      state.items.push(newItem);
    },
    
    updateItemStatus: (state, action: PayloadAction<{ id: string; status: QueueItem['status']; error?: string }>) => {
      const item = state.items.find(i => i.id === action.payload.id);
      if (item) {
        item.status = action.payload.status;
        if (action.payload.error) {
          item.error = action.payload.error;
        }
        if (action.payload.status === 'done') {
          item.syncedAt = new Date().toISOString();
        }
      }
    },
    
    incrementRetryCount: (state, action: PayloadAction<string>) => {
      const item = state.items.find(i => i.id === action.payload);
      if (item) {
        item.retryCount += 1;
      }
    },
    
    removeFromQueue: (state, action: PayloadAction<string>) => {
      state.items = state.items.filter(i => i.id !== action.payload);
    },
    
    clearCompletedItems: (state) => {
      state.items = state.items.filter(i => i.status !== 'done');
    },
    
    setSyncing: (state, action: PayloadAction<boolean>) => {
      state.syncing = action.payload;
    },
    
    loadQueue: (state, action: PayloadAction<QueueItem[]>) => {
      state.items = action.payload;
    },
  },
});

export const {
  addToQueue,
  updateItemStatus,
  incrementRetryCount,
  removeFromQueue,
  clearCompletedItems,
  setSyncing,
  loadQueue,
} = queueSlice.actions;

export default queueSlice.reducer;
