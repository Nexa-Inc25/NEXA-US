/**
 * Redux Store Configuration
 * Combines all slices and configures middleware
 */

import { configureStore } from '@reduxjs/toolkit';
import auditReducer from './slices/auditSlice';
import queueReducer from './slices/queueSlice';

export const store = configureStore({
  reducer: {
    audits: auditReducer,
    queue: queueReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for serialization checks
        ignoredActions: ['queue/addToQueue'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
