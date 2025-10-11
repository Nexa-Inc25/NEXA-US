/**
 * Redux Slice for Audit Results
 * Manages analysis results with cost impact and confidence
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface CostImpact {
  ref_code?: string;
  base_rate?: number;
  base_cost?: number;
  labor?: {
    total: number;
    crew_size: number;
    hours: number;
    premium_time: boolean;
    breakdown: Array<{
      classification: string;
      rate: number;
      hours: number;
      total: number;
    }>;
  };
  equipment?: {
    total: number;
    breakdown: Array<{
      description: string;
      rate: number;
      quantity: number;
      hours: number;
      total: number;
    }>;
  };
  adders?: Array<{
    type: string;
    percent?: number;
    estimated?: number;
  }>;
  total_savings: number;
  notes?: string[];
}

export interface Infraction {
  infraction_id: number;
  infraction_text: string;
  status: 'POTENTIALLY REPEALABLE' | 'TRUE INFRACTION' | 'NEEDS REVIEW';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  spec_matches: Array<{
    source_spec: string;
    spec_text: string;
    similarity: number;
  }>;
  cost_impact?: CostImpact;
  pm_number?: string;
  notification_number?: string;
}

export interface AuditResult {
  id: string;
  filename: string;
  timestamp: string;
  infractions: Infraction[];
  summary: {
    total: number;
    repealable: number;
    true_infractions: number;
    total_savings: number;
  };
}

interface AuditState {
  currentResult: AuditResult | null;
  results: AuditResult[];
  loading: boolean;
  error: string | null;
}

const initialState: AuditState = {
  currentResult: null,
  results: [],
  loading: false,
  error: null,
};

const auditSlice = createSlice({
  name: 'audits',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
      if (action.payload) {
        state.error = null;
      }
    },
    
    setCurrentResult: (state, action: PayloadAction<AuditResult>) => {
      state.currentResult = action.payload;
      
      // Sort infractions by total savings (high-value first)
      if (state.currentResult) {
        state.currentResult.infractions.sort((a, b) => {
          const aSavings = a.cost_impact?.total_savings || 0;
          const bSavings = b.cost_impact?.total_savings || 0;
          return bSavings - aSavings;
        });
      }
      
      state.loading = false;
      state.error = null;
    },
    
    addResult: (state, action: PayloadAction<AuditResult>) => {
      state.results.unshift(action.payload);
      // Keep only last 50 results
      if (state.results.length > 50) {
        state.results = state.results.slice(0, 50);
      }
    },
    
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.loading = false;
    },
    
    clearCurrentResult: (state) => {
      state.currentResult = null;
    },
    
    clearError: (state) => {
      state.error = null;
    },
  },
});

export const {
  setLoading,
  setCurrentResult,
  addResult,
  setError,
  clearCurrentResult,
  clearError,
} = auditSlice.actions;

export default auditSlice.reducer;
