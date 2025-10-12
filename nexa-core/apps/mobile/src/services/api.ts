/**
 * API Service for NEXA Document Analyzer
 * Connects to Render.com backend with retry logic
 */

import axios, { AxiosError } from 'axios';
import { AuditResult } from '../store/slices/auditSlice';

const API_URL = 'https://nexa-doc-analyzer-oct2025.onrender.com';

const api = axios.create({
  baseURL: API_URL,
  timeout: 60000, // 60 seconds for large PDFs
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response ${response.status} from ${response.config.url}`);
    return response;
  },
  (error: AxiosError) => {
    console.error('[API] Response error:', error.message);
    return Promise.reject(error);
  }
);

/**
 * Upload and analyze PDF audit document
 */
export const analyzeAudit = async (
  fileUri: string,
  fileName: string
): Promise<AuditResult> => {
  const formData = new FormData();
  
  // Prepare file for upload
  const file: any = {
    uri: fileUri,
    type: 'application/pdf',
    name: fileName,
  };
  
  formData.append('file', file);
  
  try {
    const response = await api.post('/analyze-audit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    // Transform backend response to AuditResult format
    const data = response.data;
    
    const result: AuditResult = {
      id: `audit_${Date.now()}`,
      filename: fileName,
      timestamp: new Date().toISOString(),
      infractions: data.analysis_results || [],
      summary: {
        total: data.analysis_results?.length || 0,
        repealable: data.analysis_results?.filter((i: any) => 
          i.status === 'POTENTIALLY REPEALABLE'
        ).length || 0,
        true_infractions: data.analysis_results?.filter((i: any) => 
          i.status === 'TRUE INFRACTION'
        ).length || 0,
        total_savings: data.analysis_results?.reduce((sum: number, i: any) => 
          sum + (i.cost_impact?.total_savings || 0), 0
        ) || 0,
      },
    };
    
    return result;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message);
    }
    throw error;
  }
};

/**
 * Upload and analyze photo
 */
export const analyzePhoto = async (
  fileUri: string,
  fileName: string
): Promise<AuditResult> => {
  const formData = new FormData();
  
  // Prepare file for upload
  const file: any = {
    uri: fileUri,
    type: 'image/jpeg',
    name: fileName,
  };
  
  formData.append('file', file);
  
  try {
    const response = await api.post('/analyze-audit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    // Transform backend response to AuditResult format
    const data = response.data;
    
    const result: AuditResult = {
      id: `photo_${Date.now()}`,
      filename: fileName,
      timestamp: new Date().toISOString(),
      infractions: data.analysis_results || [],
      summary: {
        total: data.analysis_results?.length || 0,
        repealable: data.analysis_results?.filter((i: any) => 
          i.status === 'POTENTIALLY REPEALABLE'
        ).length || 0,
        true_infractions: data.analysis_results?.filter((i: any) => 
          i.status === 'TRUE INFRACTION'
        ).length || 0,
        total_savings: data.analysis_results?.reduce((sum: number, i: any) => 
          sum + (i.cost_impact?.total_savings || 0), 0
        ) || 0,
      },
    };
    
    return result;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message);
    }
    throw error;
  }
};

/**
 * Fill as-built from photos using YOLO detection and spec cross-reference
 */
export const fillAsBuilt = async (formData: FormData): Promise<any> => {
  try {
    const response = await api.post('/fill-as-built', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000, // 2 minutes for processing multiple photos
    });
    
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'Failed to fill as-built');
    }
    throw error;
  }
};

/**
 * Upload and analyze audit with retry logic
 */
export const analyzeAuditWithRetry = async (
  fileUri: string,
  fileName: string,
  fileType: 'pdf' | 'photo',
  maxRetries: number = 3
): Promise<AuditResult> => {
  let lastError: Error | null = null;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`[API] Attempt ${attempt}/${maxRetries} for ${fileName}`);
      if (fileType === 'pdf') {
        return await analyzeAudit(fileUri, fileName);
      } else {
        return await analyzePhoto(fileUri, fileName);
      }
    } catch (error) {
      lastError = error as Error;
      console.error(`[API] Attempt ${attempt} failed:`, error);
      
      if (attempt < maxRetries) {
        // Exponential backoff: 2s, 4s, 8s
        const delay = Math.pow(2, attempt) * 1000;
        console.log(`[API] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError || new Error('Upload failed after retries');
};

/**
 * Check spec library status
 */
export const getSpecLibraryStatus = async () => {
  try {
    const response = await api.get('/spec-library');
    return response.data;
  } catch (error) {
    console.error('[API] Failed to get spec library status:', error);
    throw error;
  }
};

/**
 * Check pricing status
 */
export const getPricingStatus = async () => {
  try {
    const response = await api.get('/pricing/pricing-status');
    return response.data;
  } catch (error) {
    console.error('[API] Failed to get pricing status:', error);
    throw error;
  }
};

/**
 * Health check
 */
export const healthCheck = async (): Promise<boolean> => {
  try {
    const response = await api.get('/health');
    return response.status === 200;
  } catch (error) {
    return false;
  }
};

// Export as named export for consistency
export const apiService = {
  analyzeAudit,
  analyzePhoto,
  fillAsBuilt,
  analyzeAuditWithRetry,
  getSpecLibraryStatus,
  getPricingStatus,
  healthCheck,
};

export default api;
