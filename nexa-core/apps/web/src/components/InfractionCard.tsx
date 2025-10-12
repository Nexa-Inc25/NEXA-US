import React, { memo } from 'react';
import { CheckCircle, AlertTriangle, DollarSign } from 'lucide-react';

interface InfractionData {
  infraction_id: string;
  description: string;
  valid: boolean;
  repealable: boolean;
  confidence: number;
  repeal_reasons: string[];
  spec_references: string[];
  cost_impact: {
    total_savings: number;
    labor: {
      hours: number;
      rate: number;
      total: number;
    };
    equipment: {
      type: string;
      hours: number;
      rate: number;
      total: number;
    };
    materials: number;
  };
}

interface InfractionCardProps {
  infraction: InfractionData;
  onSelect?: (infraction: InfractionData) => void;
}

// Memoized component to prevent unnecessary re-renders
const InfractionCard = memo<InfractionCardProps>(({ infraction, onSelect }) => {
  // Extract values for cleaner JSX
  const isRepealable = !infraction.valid && infraction.repealable;
  const confidencePercent = Math.round(infraction.confidence * 100);
  const hasCostSavings = infraction.cost_impact.total_savings > 0;
  
  return (
    <div 
      className="infraction-card"
      onClick={() => onSelect?.(infraction)}
      style={{
        padding: '1rem',
        marginBottom: '0.75rem',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        cursor: onSelect ? 'pointer' : 'default',
        border: `2px solid ${isRepealable ? '#10b981' : '#ef4444'}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          {/* Status indicator with conditional rendering */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            {isRepealable ? (
              <>
                <CheckCircle size={20} color="#10b981" />
                <span style={{ color: '#10b981', fontWeight: 600 }}>
                  Repealable - {confidencePercent}% Confidence
                </span>
              </>
            ) : (
              <>
                <AlertTriangle size={20} color="#ef4444" />
                <span style={{ color: '#ef4444', fontWeight: 600 }}>
                  True Go-Back - Manual Fix Required
                </span>
              </>
            )}
          </div>
          
          {/* Description */}
          <p style={{ margin: '0.5rem 0', color: '#374151' }}>
            {infraction.description}
          </p>
          
          {/* Conditional repeal reasons - only render if exists */}
          {isRepealable && infraction.repeal_reasons.length > 0 && (
            <div style={{ marginTop: '0.5rem' }}>
              <strong>Repeal Justification:</strong>
              <ul style={{ margin: '0.25rem 0 0 1.5rem', padding: 0 }}>
                {infraction.repeal_reasons.map((reason, idx) => (
                  <li key={`${infraction.infraction_id}-reason-${idx}`}>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Spec references if available */}
          {infraction.spec_references.length > 0 && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6b7280' }}>
              <strong>Spec References:</strong> {infraction.spec_references.join(', ')}
            </div>
          )}
        </div>
        
        {/* Cost badge - only render if savings > 0 */}
        {hasCostSavings && (
          <CostBadge savings={infraction.cost_impact.total_savings} />
        )}
      </div>
      
      {/* Detailed cost breakdown on expansion */}
      {hasCostSavings && (
        <CostBreakdown costImpact={infraction.cost_impact} />
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom equality check for optimization
  return prevProps.infraction.infraction_id === nextProps.infraction.infraction_id &&
         prevProps.infraction.confidence === nextProps.infraction.confidence;
});

// Memoized cost badge component
const CostBadge = memo<{ savings: number }>(({ savings }) => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: '0.25rem',
    padding: '0.5rem 0.75rem',
    backgroundColor: '#fef3c7',
    borderRadius: '6px',
    border: '1px solid #fbbf24',
  }}>
    <DollarSign size={16} color="#d97706" />
    <span style={{ color: '#d97706', fontWeight: 600 }}>
      ${savings.toLocaleString()}
    </span>
  </div>
));

// Memoized cost breakdown
const CostBreakdown = memo<{ costImpact: InfractionData['cost_impact'] }>(({ costImpact }) => (
  <details style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: '#6b7280' }}>
    <summary style={{ cursor: 'pointer' }}>Cost Details</summary>
    <div style={{ marginTop: '0.5rem', paddingLeft: '1rem' }}>
      <div>Labor: ${costImpact.labor.total.toFixed(2)} ({costImpact.labor.hours}h @ ${costImpact.labor.rate}/hr)</div>
      <div>Equipment: ${costImpact.equipment.total.toFixed(2)} ({costImpact.equipment.type})</div>
      {costImpact.materials > 0 && <div>Materials: ${costImpact.materials.toFixed(2)}</div>}
    </div>
  </details>
));

// Display names for debugging
InfractionCard.displayName = 'InfractionCard';
CostBadge.displayName = 'CostBadge';
CostBreakdown.displayName = 'CostBreakdown';

export default InfractionCard;
