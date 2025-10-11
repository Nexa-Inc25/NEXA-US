/**
 * Camera and File Picker Service
 * Handles photo capture and document selection
 */

import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { Alert } from 'react-native';

export interface PickedFile {
  uri: string;
  name: string;
  type: 'pdf' | 'photo';
  size: number;
}

/**
 * Request camera permissions
 */
export const requestCameraPermission = async (): Promise<boolean> => {
  try {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert(
        'Permission Required',
        'Camera permission is required to take photos of poles and audit documents.',
        [{ text: 'OK' }]
      );
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('[Camera] Permission error:', error);
    return false;
  }
};

/**
 * Take photo with camera
 */
export const takePhoto = async (): Promise<PickedFile | null> => {
  try {
    const hasPermission = await requestCameraPermission();
    if (!hasPermission) {
      return null;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsEditing: false,
    });

    if (result.canceled) {
      return null;
    }

    const asset = result.assets[0];
    
    return {
      uri: asset.uri,
      name: `photo_${Date.now()}.jpg`,
      type: 'photo',
      size: asset.fileSize || 0,
    };
  } catch (error) {
    console.error('[Camera] Take photo error:', error);
    Alert.alert('Error', 'Failed to take photo. Please try again.');
    return null;
  }
};

/**
 * Pick image from gallery
 */
export const pickImage = async (): Promise<PickedFile | null> => {
  try {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert(
        'Permission Required',
        'Media library permission is required to select photos.',
        [{ text: 'OK' }]
      );
      return null;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsEditing: false,
    });

    if (result.canceled) {
      return null;
    }

    const asset = result.assets[0];
    
    return {
      uri: asset.uri,
      name: `photo_${Date.now()}.jpg`,
      type: 'photo',
      size: asset.fileSize || 0,
    };
  } catch (error) {
    console.error('[Camera] Pick image error:', error);
    Alert.alert('Error', 'Failed to select image. Please try again.');
    return null;
  }
};

/**
 * Pick PDF document
 */
export const pickDocument = async (): Promise<PickedFile | null> => {
  try {
    const result = await DocumentPicker.getDocumentAsync({
      type: 'application/pdf',
      copyToCacheDirectory: true,
    });

    if (result.canceled) {
      return null;
    }

    const file = result.assets[0];
    
    // Check file size (max 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size && file.size > maxSize) {
      Alert.alert(
        'File Too Large',
        'Please select a PDF file smaller than 50MB.',
        [{ text: 'OK' }]
      );
      return null;
    }

    return {
      uri: file.uri,
      name: file.name,
      type: 'pdf',
      size: file.size || 0,
    };
  } catch (error) {
    console.error('[Camera] Pick document error:', error);
    Alert.alert('Error', 'Failed to select document. Please try again.');
    return null;
  }
};

/**
 * Format file size for display
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};
