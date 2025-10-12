/**
 * Offline Queue Service
 * Manages offline upload queue for photos and documents
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

export interface QueueItem {
  id: string;
  fileUri: string;
  fileName: string;
  fileType: 'pdf' | 'photo';
  fileSize: number;
  status?: 'pending' | 'uploading' | 'completed' | 'failed';
  retryCount?: number;
  createdAt?: string;
  error?: string;
}

class OfflineQueueService {
  private readonly QUEUE_KEY = '@nexa_offline_queue';
  private readonly MAX_RETRIES = 3;

  /**
   * Save queue to persistent storage
   */
  async saveQueue(items: QueueItem[]): Promise<void> {
    try {
      const data = JSON.stringify(items);
      await AsyncStorage.setItem(this.QUEUE_KEY, data);
    } catch (error) {
      console.error('Failed to save queue:', error);
      throw error;
    }
  }

  /**
   * Load queue from persistent storage
   */
  async loadQueue(): Promise<QueueItem[]> {
    try {
      const data = await AsyncStorage.getItem(this.QUEUE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('Failed to load queue:', error);
      return [];
    }
  }

  /**
   * Add item to queue
   */
  async addToQueue(item: QueueItem): Promise<void> {
    const queue = await this.loadQueue();
    const newItem = {
      ...item,
      status: 'pending' as const,
      retryCount: 0,
      createdAt: new Date().toISOString()
    };
    queue.push(newItem);
    await this.saveQueue(queue);
  }

  /**
   * Remove item from queue
   */
  async removeFromQueue(itemId: string): Promise<void> {
    const queue = await this.loadQueue();
    const filtered = queue.filter(item => item.id !== itemId);
    await this.saveQueue(filtered);
  }

  /**
   * Update item status
   */
  async updateItemStatus(
    itemId: string, 
    status: QueueItem['status'], 
    error?: string
  ): Promise<void> {
    const queue = await this.loadQueue();
    const itemIndex = queue.findIndex(item => item.id === itemId);
    
    if (itemIndex !== -1) {
      queue[itemIndex].status = status;
      if (error) {
        queue[itemIndex].error = error;
      }
      if (status === 'failed') {
        queue[itemIndex].retryCount = (queue[itemIndex].retryCount || 0) + 1;
      }
      await this.saveQueue(queue);
    }
  }

  /**
   * Get pending items for upload
   */
  async getPendingItems(): Promise<QueueItem[]> {
    const queue = await this.loadQueue();
    return queue.filter(
      item => item.status === 'pending' && 
      (item.retryCount || 0) < this.MAX_RETRIES
    );
  }

  /**
   * Clear completed items
   */
  async clearCompleted(): Promise<void> {
    const queue = await this.loadQueue();
    const filtered = queue.filter(item => item.status !== 'completed');
    await this.saveQueue(filtered);
  }

  /**
   * Get queue statistics
   */
  async getQueueStats(): Promise<{
    total: number;
    pending: number;
    uploading: number;
    completed: number;
    failed: number;
  }> {
    const queue = await this.loadQueue();
    return {
      total: queue.length,
      pending: queue.filter(i => i.status === 'pending').length,
      uploading: queue.filter(i => i.status === 'uploading').length,
      completed: queue.filter(i => i.status === 'completed').length,
      failed: queue.filter(i => i.status === 'failed').length,
    };
  }
}

export const offlineQueue = new OfflineQueueService();
