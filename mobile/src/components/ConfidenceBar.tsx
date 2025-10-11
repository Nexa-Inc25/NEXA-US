/**
 * Confidence Bar Component
 * Visual progress bar showing confidence level with color coding
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '../theme';

interface ConfidenceBarProps {
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  confidenceValue?: number; // 0-1 scale
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ 
  confidence, 
  confidenceValue 
}) => {
  // Map confidence to percentage and color
  const getConfidenceData = () => {
    switch (confidence) {
      case 'HIGH':
        return {
          percentage: confidenceValue ? confidenceValue * 100 : 85,
          color: theme.colors.success,
          label: 'HIGH',
        };
      case 'MEDIUM':
        return {
          percentage: confidenceValue ? confidenceValue * 100 : 65,
          color: theme.colors.warning,
          label: 'MEDIUM',
        };
      case 'LOW':
        return {
          percentage: confidenceValue ? confidenceValue * 100 : 40,
          color: theme.colors.danger,
          label: 'LOW',
        };
    }
  };

  const data = getConfidenceData();

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.label}>Confidence</Text>
        <Text style={[styles.value, { color: data.color }]}>
          {data.label} ({Math.round(data.percentage)}%)
        </Text>
      </View>
      
      <View style={styles.barContainer}>
        <View style={styles.barBackground}>
          <View 
            style={[
              styles.barFill, 
              { 
                width: `${data.percentage}%`,
                backgroundColor: data.color 
              }
            ]} 
          />
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: theme.spacing.sm,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  label: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    fontWeight: '500',
  },
  value: {
    fontSize: theme.fontSizes.small,
    fontWeight: '700',
  },
  barContainer: {
    width: '100%',
  },
  barBackground: {
    height: 8,
    backgroundColor: theme.colors.border,
    borderRadius: theme.borderRadius.small,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: theme.borderRadius.small,
  },
});
