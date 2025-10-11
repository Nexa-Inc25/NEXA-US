/**
 * Results Screen
 * Display analysis results with cost impact breakdown
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Modal,
} from 'react-native';
import { useSelector } from 'react-redux';
import { theme } from '../theme';
import { RootState } from '../store';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { CostBadge } from '../components/CostBadge';
import { InfractionCard } from '../components/InfractionCard';
import { Infraction, CostImpact } from '../store/slices/auditSlice';

interface ResultsScreenProps {
  navigation: any;
}

export const ResultsScreen: React.FC<ResultsScreenProps> = ({ navigation }) => {
  const { currentResult } = useSelector((state: RootState) => state.audits);
  const [selectedInfraction, setSelectedInfraction] = useState<Infraction | null>(null);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);

  if (!currentResult) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyIcon}>📋</Text>
        <Text style={styles.emptyText}>No results yet</Text>
        <Text style={styles.emptySubtext}>Upload an audit to see analysis</Text>
        <TouchableOpacity
          style={styles.uploadButton}
          onPress={() => navigation.navigate('PhotosQA')}
        >
          <Text style={styles.uploadButtonText}>Upload Audit</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const { infractions, summary } = currentResult;

  const handleInfractionPress = (infraction: Infraction) => {
    setSelectedInfraction(infraction);
    setDetailsModalVisible(true);
  };

  const renderCostBreakdown = (costImpact: CostImpact) => {
    return (
      <View style={styles.costBreakdown}>
        {/* Base Cost */}
        {costImpact.base_cost && (
          <View style={styles.breakdownRow}>
            <Text style={styles.breakdownLabel}>Base Cost:</Text>
            <Text style={styles.breakdownValue}>
              ${costImpact.base_cost.toLocaleString()}
            </Text>
          </View>
        )}

        {/* Labor Breakdown */}
        {costImpact.labor && (
          <View style={styles.breakdownSection}>
            <Text style={styles.breakdownSectionTitle}>
              👷 Labor ({costImpact.labor.crew_size}-man crew, {costImpact.labor.hours}h
              {costImpact.labor.premium_time ? ' premium' : ''})
            </Text>
            {costImpact.labor.breakdown.map((item, idx) => (
              <View key={idx} style={styles.breakdownSubRow}>
                <Text style={styles.breakdownSubLabel}>
                  {item.classification}
                </Text>
                <Text style={styles.breakdownSubValue}>
                  ${item.rate}/hr × {item.hours}h = ${item.total.toLocaleString()}
                </Text>
              </View>
            ))}
            <View style={styles.breakdownRow}>
              <Text style={styles.breakdownLabelBold}>Labor Total:</Text>
              <Text style={styles.breakdownValueBold}>
                ${costImpact.labor.total.toLocaleString()}
              </Text>
            </View>
          </View>
        )}

        {/* Equipment Breakdown */}
        {costImpact.equipment && (
          <View style={styles.breakdownSection}>
            <Text style={styles.breakdownSectionTitle}>🚜 Equipment</Text>
            {costImpact.equipment.breakdown.map((item, idx) => (
              <View key={idx} style={styles.breakdownSubRow}>
                <Text style={styles.breakdownSubLabel}>
                  {item.description}
                </Text>
                <Text style={styles.breakdownSubValue}>
                  ${item.rate}/hr × {item.quantity} × {item.hours}h = $
                  {item.total.toLocaleString()}
                </Text>
              </View>
            ))}
            <View style={styles.breakdownRow}>
              <Text style={styles.breakdownLabelBold}>Equipment Total:</Text>
              <Text style={styles.breakdownValueBold}>
                ${costImpact.equipment.total.toLocaleString()}
              </Text>
            </View>
          </View>
        )}

        {/* Adders */}
        {costImpact.adders && costImpact.adders.length > 0 && (
          <View style={styles.breakdownSection}>
            <Text style={styles.breakdownSectionTitle}>📊 Adders</Text>
            {costImpact.adders.map((adder, idx) => (
              <View key={idx} style={styles.breakdownSubRow}>
                <Text style={styles.breakdownSubLabel}>{adder.type}</Text>
                <Text style={styles.breakdownSubValue}>
                  {adder.percent ? `${adder.percent}% ` : ''}
                  {adder.estimated ? `$${adder.estimated.toLocaleString()}` : ''}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Total */}
        <View style={[styles.breakdownRow, styles.totalRow]}>
          <Text style={styles.totalLabel}>Total Savings:</Text>
          <Text style={styles.totalValue}>
            ${costImpact.total_savings.toLocaleString()}
          </Text>
        </View>

        {/* Notes */}
        {costImpact.notes && costImpact.notes.length > 0 && (
          <View style={styles.notesSection}>
            <Text style={styles.notesTitle}>📝 Notes:</Text>
            {costImpact.notes.map((note, idx) => (
              <Text key={idx} style={styles.noteText}>
                • {note}
              </Text>
            ))}
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Summary Header */}
      <View style={styles.summaryHeader}>
        <Text style={styles.filename}>{currentResult.filename}</Text>
        <Text style={styles.timestamp}>
          {new Date(currentResult.timestamp).toLocaleString()}
        </Text>
        
        <View style={styles.summaryCards}>
          <View style={[styles.summaryCard, styles.totalCard]}>
            <Text style={styles.summaryCardValue}>{summary.total}</Text>
            <Text style={styles.summaryCardLabel}>Total</Text>
          </View>
          
          <View style={[styles.summaryCard, styles.repealableCard]}>
            <Text style={styles.summaryCardValue}>{summary.repealable}</Text>
            <Text style={styles.summaryCardLabel}>Repealable</Text>
          </View>
          
          <View style={[styles.summaryCard, styles.trueCard]}>
            <Text style={styles.summaryCardValue}>{summary.true_infractions}</Text>
            <Text style={styles.summaryCardLabel}>True</Text>
          </View>
        </View>

        <CostBadge amount={summary.total_savings} size="large" />
      </View>

      {/* Infractions List */}
      <ScrollView style={styles.infractionsList}>
        {infractions.map((infraction) => (
          <TouchableOpacity
            key={infraction.infraction_id}
            onPress={() => handleInfractionPress(infraction)}
          >
            <InfractionCard infraction={infraction} />
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Details Modal */}
      <Modal
        visible={detailsModalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setDetailsModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Infraction Details</Text>
            <TouchableOpacity onPress={() => setDetailsModalVisible(false)}>
              <Text style={styles.closeButton}>✕</Text>
            </TouchableOpacity>
          </View>

          {selectedInfraction && (
            <ScrollView style={styles.modalContent}>
              {/* Status & Confidence */}
              <View style={styles.modalSection}>
                <Text style={styles.modalSectionTitle}>Status</Text>
                <Text
                  style={[
                    styles.statusBadge,
                    selectedInfraction.status === 'POTENTIALLY REPEALABLE'
                      ? styles.repealableBadge
                      : styles.trueBadge,
                  ]}
                >
                  {selectedInfraction.status}
                </Text>
                <ConfidenceBar confidence={selectedInfraction.confidence} />
              </View>

              {/* Infraction Text */}
              <View style={styles.modalSection}>
                <Text style={styles.modalSectionTitle}>Infraction Text</Text>
                <Text style={styles.infractionText}>
                  {selectedInfraction.infraction_text}
                </Text>
              </View>

              {/* Cost Impact */}
              {selectedInfraction.cost_impact && (
                <View style={styles.modalSection}>
                  <Text style={styles.modalSectionTitle}>Cost Impact</Text>
                  {renderCostBreakdown(selectedInfraction.cost_impact)}
                </View>
              )}

              {/* Spec Matches */}
              {selectedInfraction.spec_matches &&
                selectedInfraction.spec_matches.length > 0 && (
                  <View style={styles.modalSection}>
                    <Text style={styles.modalSectionTitle}>Spec Matches</Text>
                    {selectedInfraction.spec_matches.map((match, idx) => (
                      <View key={idx} style={styles.specMatch}>
                        <Text style={styles.specSource}>{match.source_spec}</Text>
                        <Text style={styles.specText}>{match.spec_text}</Text>
                        <Text style={styles.specSimilarity}>
                          Similarity: {(match.similarity * 100).toFixed(1)}%
                        </Text>
                      </View>
                    ))}
                  </View>
                )}

              {/* PM/Notification Numbers */}
              {(selectedInfraction.pm_number || selectedInfraction.notification_number) && (
                <View style={styles.modalSection}>
                  <Text style={styles.modalSectionTitle}>Reference Numbers</Text>
                  {selectedInfraction.pm_number && (
                    <Text style={styles.referenceText}>
                      PM: {selectedInfraction.pm_number}
                    </Text>
                  )}
                  {selectedInfraction.notification_number && (
                    <Text style={styles.referenceText}>
                      Notification: {selectedInfraction.notification_number}
                    </Text>
                  )}
                </View>
              )}
            </ScrollView>
          )}
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.xl,
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: theme.spacing.md,
  },
  emptyText: {
    fontSize: theme.fontSizes.xlarge,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  emptySubtext: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.lg,
  },
  uploadButton: {
    backgroundColor: theme.colors.primary,
    paddingHorizontal: theme.spacing.xl,
    paddingVertical: theme.spacing.md,
    borderRadius: theme.borderRadius.medium,
  },
  uploadButtonText: {
    color: '#fff',
    fontSize: theme.fontSizes.large,
    fontWeight: '600',
  },
  summaryHeader: {
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    ...theme.shadows.small,
  },
  filename: {
    fontSize: theme.fontSizes.large,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  timestamp: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
  },
  summaryCards: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.md,
  },
  summaryCard: {
    flex: 1,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.medium,
    marginHorizontal: theme.spacing.xs,
    alignItems: 'center',
  },
  totalCard: {
    backgroundColor: theme.colors.primary + '20',
  },
  repealableCard: {
    backgroundColor: theme.colors.success + '20',
  },
  trueCard: {
    backgroundColor: theme.colors.danger + '20',
  },
  summaryCardValue: {
    fontSize: theme.fontSizes.xlarge,
    fontWeight: '700',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  summaryCardLabel: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
  },
  infractionsList: {
    flex: 1,
    padding: theme.spacing.md,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  modalTitle: {
    fontSize: theme.fontSizes.xlarge,
    fontWeight: '700',
    color: theme.colors.text,
  },
  closeButton: {
    fontSize: theme.fontSizes.xlarge,
    color: theme.colors.textSecondary,
    padding: theme.spacing.sm,
  },
  modalContent: {
    flex: 1,
    padding: theme.spacing.md,
  },
  modalSection: {
    marginBottom: theme.spacing.lg,
  },
  modalSectionTitle: {
    fontSize: theme.fontSizes.large,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  statusBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.medium,
    marginBottom: theme.spacing.sm,
  },
  repealableBadge: {
    backgroundColor: theme.colors.success,
  },
  trueBadge: {
    backgroundColor: theme.colors.danger,
  },
  infractionText: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    lineHeight: 22,
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.medium,
  },
  costBreakdown: {
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.medium,
  },
  breakdownRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: theme.spacing.xs,
  },
  breakdownLabel: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.textSecondary,
  },
  breakdownValue: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    fontWeight: '500',
  },
  breakdownLabelBold: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    fontWeight: '600',
  },
  breakdownValueBold: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    fontWeight: '700',
  },
  breakdownSection: {
    marginTop: theme.spacing.md,
    paddingTop: theme.spacing.md,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
  },
  breakdownSectionTitle: {
    fontSize: theme.fontSizes.medium,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  breakdownSubRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: theme.spacing.xs,
    paddingLeft: theme.spacing.md,
  },
  breakdownSubLabel: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    flex: 1,
  },
  breakdownSubValue: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.text,
    textAlign: 'right',
  },
  totalRow: {
    marginTop: theme.spacing.md,
    paddingTop: theme.spacing.md,
    borderTopWidth: 2,
    borderTopColor: theme.colors.primary,
  },
  totalLabel: {
    fontSize: theme.fontSizes.large,
    fontWeight: '700',
    color: theme.colors.text,
  },
  totalValue: {
    fontSize: theme.fontSizes.large,
    fontWeight: '700',
    color: theme.colors.success,
  },
  notesSection: {
    marginTop: theme.spacing.md,
    paddingTop: theme.spacing.md,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
  },
  notesTitle: {
    fontSize: theme.fontSizes.medium,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  noteText: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
    lineHeight: 18,
  },
  specMatch: {
    backgroundColor: theme.colors.background,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.medium,
    marginBottom: theme.spacing.sm,
  },
  specSource: {
    fontSize: theme.fontSizes.small,
    fontWeight: '600',
    color: theme.colors.primary,
    marginBottom: theme.spacing.xs,
  },
  specText: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
    lineHeight: 18,
  },
  specSimilarity: {
    fontSize: theme.fontSizes.small,
    color: theme.colors.textSecondary,
    fontStyle: 'italic',
  },
  referenceText: {
    fontSize: theme.fontSizes.medium,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
});
