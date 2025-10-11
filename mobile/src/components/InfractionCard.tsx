/**
 * Infraction Card Component
 * Displays single infraction with validity, confidence, cost impact, and spec references
 */

import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme';
import { Infraction } from '../store/slices/auditSlice';
import { ConfidenceBar } from './ConfidenceBar';
import { CostBadge } from './CostBadge';

interface InfractionCardProps {
  infraction: Infraction;
  onPress?: () => void;
}

export const InfractionCard: React.FC<InfractionCardProps> = ({ 
  infraction, 
  onPress 
}) => {
  const [expanded, setExpanded] = useState(false);

  // Determine status color and icon
  const getStatusData = () => {
    switch (infraction.status) {
      case 'POTENTIALLY REPEALABLE':
        return {
          color: theme.colors.success,
          icon: 'checkmark-circle' as const,
          label: 'REPEALABLE',
        };
      case 'TRUE INFRACTION':
        return {
          color: theme.colors.danger,
          icon: 'close-circle' as const,
          label: 'TRUE INFRACTION',
        };
      default:
        return {
          color: theme.colors.warning,
          icon: 'alert-circle' as const,
          label: 'NEEDS REVIEW',
        };
    }
  };

  const statusData = getStatusData();
  const totalSavings = infraction.cost_impact?.total_savings || 0;

  return (
    <TouchableOpacity 
      style={styles.card}
      onPress={() => {
        setExpanded(!expanded);
        onPress?.();
      }}
      activeOpacity={0.7}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.statusRow}>
          <Ionicons 
            name={statusData.icon} 
            size={24} 
            color={statusData.color} 
          />
          <Text style={[styles.statusLabel, { color: statusData.color }]}>
            {statusData.label}
          </Text>
        </View>
        
        {totalSavings > 0 && (
          <CostBadge totalSavings={totalSavings} size="small" />
        )}
      </View>

      {/* Infraction Text */}
      <Text style={styles.infractionText} numberOfLines={expanded ? undefined : 3}>
        {infraction.infraction_text}
      </Text>

      {/* PM/Notification Numbers */}
      {(infraction.pm_number || infraction.notification_number) && (
        <View style={styles.jobNumbers}>
          {infraction.pm_number && (
            <Text style={styles.jobNumber}>PM: {infraction.pm_number}</Text>
          )}
          {infraction.notification_number && (
            <Text style={styles.jobNumber}>
              Notification: {infraction.notification_number}
            </Text>
          )}
        </View>
      )}

      {/* Confidence Bar */}
      <ConfidenceBar 
        confidence={infraction.confidence}
        confidenceValue={
          infraction.confidence === 'HIGH' ? 0.85 :
          infraction.confidence === 'MEDIUM' ? 0.65 : 0.40
        }
      />

      {/* Expanded Details */}
      {expanded && (
        <View style={styles.expandedSection}>
          {/* Cost Breakdown */}
          {infraction.cost_impact && (
            <View style={styles.costBreakdown}>
              <Text style={styles.sectionTitle}>💰 Cost Breakdown</Text>
              
              {infraction.cost_impact.base_cost !== undefined && (
                <View style={styles.costRow}>
                  <Text style={styles.costLabel}>Base Rate:</Text>
                  <Text style={styles.costValue}>
                    ${infraction.cost_impact.base_cost.toLocaleString()}
                  </Text>
                </View>
              )}

              {infraction.cost_impact.labor && (
                <View style={styles.costRow}>
                  <Text style={styles.costLabel}>
                    Labor ({infraction.cost_impact.labor.crew_size}-man, {infraction.cost_impact.labor.hours}hrs
                    {infraction.cost_impact.labor.premium_time ? ', premium' : ''}):
                  </Text>
                  <Text style={styles.costValue}>
                    ${infraction.cost_impact.labor.total.toLocaleString()}
                  </Text>
                </View>
              )}

              {infraction.cost_impact.equipment && (
                <View style={styles.costRow}>
                  <Text style={styles.costLabel}>Equipment:</Text>
                  <Text style={styles.costValue}>
                    ${infraction.cost_impact.equipment.total.toLocaleString()}
                  </Text>
                </View>
              )}

              {infraction.cost_impact.adders && infraction.cost_impact.adders.length > 0 && (
                <View style={styles.costRow}>
                  <Text style={styles.costLabel}>Adders:</Text>
                  <Text style={styles.costValue}>
                    ${infraction.cost_impact.adders.reduce((sum, a) => sum + (a.estimated || 0), 0).toLocaleString()}
                  </Text>
                </View>
              )}

              <View style={[styles.costRow, styles.totalRow]}>
                <Text style={styles.totalLabel}>Total Savings:</Text>
                <Text style={styles.totalValue}>
                  ${totalSavings.toLocaleString()}
                </Text>
              </View>
            </View>
          )}

          {/* Spec References */}
          {infraction.spec_matches && infraction.spec_matches.length > 0 && (
            <View style={styles.specSection}>
              <Text style={styles.sectionTitle}>📋 Spec References</Text>
              {infraction.spec_matches.slice(0, 3).map((match, idx) => (
                <View key={idx} style={styles.specMatch}>
                  <Text style={styles.specSource}>{match.source_spec}</Text>
                  <Text style={styles.specText} numberOfLines={2}>
                    {match.spec_text}
                  </Text>
                  <Text style={styles.specSimilarity}>
                    Match: {Math.round(match.similarity * 100)}%
                  </Text>
                </View>
              ))}
            </View>
          )}

          {/* Notes */}
          {infraction.cost_impact?.notes && infraction.cost_impact.notes.length > 0 && (
            <View style={styles.notesSection}>
              <Text style={styles.sectionTitle}>📝 Notes</Text>
              {infraction.cost_impact.notes.map((note, idx) => (
                <Text key={idx} style={styles.note}>• {note}</Text>
              ))}
            </View>
          )}
        </View>
      )}

      {/* Expand/Collapse Indicator */}
      <View style={styles.expandIndicator}>
        <Ionicons 
          name={expanded ? 'chevron-up' : 'chevron-down'} 
          size={20} 
          color={theme.colors.textSecondary} 
        />
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.medium,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    ...theme.shadows.medium,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusLabel: {
    fontSize: theme.fontSizes.medium,
    fontWeight: '700',
    marginLeft: theme.spacing.sm,
  },
  infractionText: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
    lineHeight: 22,
  },
  jobNumbers: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: theme.spacing.sm,
  },
  jobNumber: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    marginRight: theme.spacing.md,
    fontWeight: '500',
  },
  expandedSection: {
    marginTop: theme.spacing.md,
    paddingTop: theme.spacing.md,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
  },
  sectionTitle: {
    fontSize: theme.fontSizes.medium,
    fontWeight: '700',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  costBreakdown: {
    marginBottom: theme.spacing.md,
  },
  costRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.xs,
  },
  costLabel: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    flex: 1,
  },
  costValue: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.text,
    fontWeight: '600',
  },
  totalRow: {
    marginTop: theme.spacing.sm,
    paddingTop: theme.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
  },
  totalLabel: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    fontWeight: '700',
  },
  totalValue: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.success,
    fontWeight: '700',
  },
  specSection: {
    marginBottom: theme.spacing.md,
  },
  specMatch: {
    backgroundColor: theme.colors.background,
    padding: theme.spacing.sm,
    borderRadius: theme.borderRadius.small,
    marginBottom: theme.spacing.sm,
  },
  specSource: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.primary,
    fontWeight: '600',
    marginBottom: theme.spacing.xs,
  },
  specText: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  specSimilarity: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    fontStyle: 'italic',
  },
  notesSection: {
    marginBottom: theme.spacing.sm,
  },
  note: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
  },
  expandIndicator: {
    alignItems: 'center',
    marginTop: theme.spacing.sm,
  },
});
