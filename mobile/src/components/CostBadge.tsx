/**
 * Cost Badge Component
 * Displays cost savings with color coding by value
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '../theme';

interface CostBadgeProps {
  totalSavings: number;
  size?: 'small' | 'medium' | 'large';
}

export const CostBadge: React.FC<CostBadgeProps> = ({ 
  totalSavings, 
  size = 'medium' 
}) => {
  // Determine color based on savings amount
  const getBadgeColor = () => {
    if (totalSavings >= 10000) {
      return {
        bg: theme.colors.highValue,
        label: 'HIGH VALUE',
      };
    } else if (totalSavings >= 5000) {
      return {
        bg: theme.colors.mediumValue,
        label: 'MEDIUM VALUE',
      };
    } else if (totalSavings > 0) {
      return {
        bg: theme.colors.lowValue,
        label: 'LOW VALUE',
      };
    } else {
      return {
        bg: theme.colors.textSecondary,
        label: 'TBD',
      };
    }
  };

  const badgeData = getBadgeColor();
  
  // Size-based styling
  const sizeStyles = {
    small: {
      container: { paddingHorizontal: 8, paddingVertical: 4 },
      amount: { fontSize: 14 },
      label: { fontSize: 10 },
    },
    medium: {
      container: { paddingHorizontal: 12, paddingVertical: 6 },
      amount: { fontSize: 18 },
      label: { fontSize: 11 },
    },
    large: {
      container: { paddingHorizontal: 16, paddingVertical: 8 },
      amount: { fontSize: 24 },
      label: { fontSize: 12 },
    },
  };

  const currentSize = sizeStyles[size];

  return (
    <View 
      style={[
        styles.container, 
        currentSize.container,
        { backgroundColor: badgeData.bg }
      ]}
    >
      <Text style={[styles.amount, currentSize.amount]}>
        ${totalSavings.toLocaleString('en-US', { 
          minimumFractionDigits: 0,
          maximumFractionDigits: 0 
        })}
      </Text>
      <Text style={[styles.label, currentSize.label]}>
        {badgeData.label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: theme.borderRadius.medium,
    alignItems: 'center',
    justifyContent: 'center',
    ...theme.shadows.small,
  },
  amount: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  label: {
    color: '#FFFFFF',
    fontWeight: '600',
    marginTop: 2,
  },
});
