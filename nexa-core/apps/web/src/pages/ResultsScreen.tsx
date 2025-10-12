import React, { memo, useMemo, useState, useCallback, Suspense, lazy } from 'react';
import { Search, Filter, Download, TrendingUp, TrendingDown } from 'lucide-react';
import InfractionCard from '../components/InfractionCard';
import '../styles/results.css';

// Lazy load heavy components for better initial load
const DetailedAnalytics = lazy(() => import('../components/DetailedAnalytics'));

interface AuditResult {
  infraction_id: string;
  description: string;
  valid: boolean;
  repealable: boolean;
  confidence: number;
  repeal_reasons: string[];
  spec_references: string[];
  cost_impact: {
    total_savings: number;
    labor: { hours: number; rate: number; total: number };
    equipment: { type: string; hours: number; rate: number; total: number };
    materials: number;
  };
  job_info: {
    pm_number?: string;
    notification_number?: string;
    location: string;
    date: string;
  };
}

const ResultsScreen: React.FC = memo(() => {
  // State management
  const [results, setResults] = useState<AuditResult[]>(mockResults);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'repealable' | 'valid'>('all');
  const [sortBy, setSortBy] = useState<'cost' | 'confidence' | 'date'>('cost');
  const [selectedResult, setSelectedResult] = useState<AuditResult | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);

  // Memoized filtered and sorted results
  const processedResults = useMemo(() => {
    let filtered = [...results];

    // Apply filter
    if (filterType !== 'all') {
      filtered = filtered.filter(r => 
        filterType === 'repealable' ? r.repealable && !r.valid : r.valid
      );
    }

    // Apply search
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(r => 
        r.description.toLowerCase().includes(term) ||
        r.job_info.pm_number?.toLowerCase().includes(term) ||
        r.job_info.notification_number?.toLowerCase().includes(term)
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'cost':
          return b.cost_impact.total_savings - a.cost_impact.total_savings;
        case 'confidence':
          return b.confidence - a.confidence;
        case 'date':
          return new Date(b.job_info.date).getTime() - new Date(a.job_info.date).getTime();
        default:
          return 0;
      }
    });

    return filtered;
  }, [results, filterType, searchTerm, sortBy]);

  // Memoized statistics
  const stats = useMemo(() => {
    const repealable = results.filter(r => r.repealable && !r.valid);
    const totalSavings = repealable.reduce((sum, r) => sum + r.cost_impact.total_savings, 0);
    const avgConfidence = repealable.length > 0 
      ? repealable.reduce((sum, r) => sum + r.confidence, 0) / repealable.length 
      : 0;

    return {
      total: results.length,
      repealable: repealable.length,
      valid: results.filter(r => r.valid).length,
      totalSavings,
      avgConfidence,
    };
  }, [results]);

  // Callbacks to prevent re-creation
  const handleSearch = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  }, []);

  const handleFilterChange = useCallback((type: typeof filterType) => {
    setFilterType(type);
  }, []);

  const handleSort = useCallback((sort: typeof sortBy) => {
    setSortBy(sort);
  }, []);

  const handleSelectResult = useCallback((result: AuditResult) => {
    setSelectedResult(result);
  }, []);

  const handleExport = useCallback(() => {
    // Export logic here
    const csv = processedResults.map(r => ({
      ID: r.infraction_id,
      Description: r.description,
      Repealable: r.repealable ? 'Yes' : 'No',
      Confidence: `${Math.round(r.confidence * 100)}%`,
      Savings: `$${r.cost_impact.total_savings}`,
      PM: r.job_info.pm_number || 'N/A',
    }));
    
    console.log('Exporting:', csv);
    // Implement actual CSV export
  }, [processedResults]);

  return (
    <div className="results-container">
      {/* Header with stats */}
      <header className="results-header">
        <div className="header-content">
          <h1>Audit Analysis Results</h1>
          <p>Analyzed {stats.total} infractions from job package</p>
        </div>
        <button onClick={handleExport} className="export-btn">
          <Download size={20} />
          Export Results
        </button>
      </header>

      {/* Summary stats */}
      <div className="stats-grid">
        <StatCard
          label="Total Infractions"
          value={stats.total}
          icon={<Filter size={24} />}
          color="#6b7280"
        />
        <StatCard
          label="Repealable"
          value={stats.repealable}
          icon={<TrendingUp size={24} />}
          color="#10b981"
        />
        <StatCard
          label="Valid Go-Backs"
          value={stats.valid}
          icon={<TrendingDown size={24} />}
          color="#ef4444"
        />
        <StatCard
          label="Total Savings"
          value={`$${stats.totalSavings.toLocaleString()}`}
          icon={<DollarSign size={24} />}
          color="#f59e0b"
        />
        <StatCard
          label="Avg Confidence"
          value={`${Math.round(stats.avgConfidence * 100)}%`}
          icon={<Activity size={24} />}
          color="#3b82f6"
        />
      </div>

      {/* Controls */}
      <div className="controls-bar">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search by description, PM#, or notification#..."
            value={searchTerm}
            onChange={handleSearch}
          />
        </div>
        
        <div className="filter-controls">
          <select 
            value={filterType} 
            onChange={(e) => handleFilterChange(e.target.value as typeof filterType)}
            className="filter-select"
          >
            <option value="all">All Results</option>
            <option value="repealable">Repealable Only</option>
            <option value="valid">Valid Go-Backs Only</option>
          </select>
          
          <select 
            value={sortBy} 
            onChange={(e) => handleSort(e.target.value as typeof sortBy)}
            className="sort-select"
          >
            <option value="cost">Sort by Cost Impact</option>
            <option value="confidence">Sort by Confidence</option>
            <option value="date">Sort by Date</option>
          </select>
        </div>
        
        <button 
          onClick={() => setShowAnalytics(!showAnalytics)}
          className="analytics-toggle"
        >
          {showAnalytics ? 'Hide' : 'Show'} Analytics
        </button>
      </div>

      {/* Lazy loaded analytics */}
      {showAnalytics && (
        <Suspense fallback={<div className="loading">Loading analytics...</div>}>
          <DetailedAnalytics results={processedResults} />
        </Suspense>
      )}

      {/* Results list with virtualization for large datasets */}
      <div className="results-list">
        {processedResults.length === 0 ? (
          <div className="no-results">
            <p>No results match your criteria</p>
          </div>
        ) : (
          // Use React.Fragment to avoid extra wrapper
          <>
            {processedResults.map(result => (
              <InfractionCard
                key={result.infraction_id}
                infraction={result}
                onSelect={handleSelectResult}
              />
            ))}
          </>
        )}
      </div>

      {/* Selected result detail modal */}
      {selectedResult && (
        <ResultDetailModal
          result={selectedResult}
          onClose={() => setSelectedResult(null)}
        />
      )}
    </div>
  );
});

// Memoized stat card component
const StatCard = memo<{
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}>(({ label, value, icon, color }) => (
  <div className="stat-card" style={{ borderColor: color }}>
    <div className="stat-icon" style={{ color }}>
      {icon}
    </div>
    <div className="stat-content">
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
    </div>
  </div>
));

// Memoized modal component
const ResultDetailModal = memo<{
  result: AuditResult;
  onClose: () => void;
}>(({ result, onClose }) => (
  <div className="modal-overlay" onClick={onClose}>
    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
      <h2>Infraction Details</h2>
      <div className="detail-grid">
        <div>
          <strong>PM Number:</strong> {result.job_info.pm_number || 'N/A'}
        </div>
        <div>
          <strong>Notification:</strong> {result.job_info.notification_number || 'N/A'}
        </div>
        <div>
          <strong>Location:</strong> {result.job_info.location}
        </div>
        <div>
          <strong>Date:</strong> {new Date(result.job_info.date).toLocaleDateString()}
        </div>
      </div>
      <button onClick={onClose} className="close-btn">Close</button>
    </div>
  </div>
));

// Mock data for development
const mockResults: AuditResult[] = [
  {
    infraction_id: 'INF-001',
    description: 'TAG-2 crossarm installation non-compliant with spacing requirements',
    valid: false,
    repealable: true,
    confidence: 0.92,
    repeal_reasons: [
      'Per SECTION 3.2: Pre-2020 installations have variance allowance',
      'Grandfather clause applies to this structure',
    ],
    spec_references: ['GO 95 Rule 44.2', 'PG&E Greenbook Section 3.2'],
    cost_impact: {
      total_savings: 6388,
      labor: { hours: 30, rate: 79.04, total: 2371 },
      equipment: { type: 'Bucket Truck', hours: 16, rate: 150, total: 2400 },
      materials: 1617,
    },
    job_info: {
      pm_number: '46369836',
      notification_number: '126465328',
      location: 'Stockton North - Grid 42B',
      date: '2025-10-10',
    },
  },
  {
    infraction_id: 'INF-002',
    description: 'Grounding wire gauge below specification',
    valid: true,
    repealable: false,
    confidence: 0.98,
    repeal_reasons: [],
    spec_references: ['GO 95 Rule 33.3'],
    cost_impact: {
      total_savings: 0,
      labor: { hours: 4, rate: 79.04, total: 316 },
      equipment: { type: 'Service Truck', hours: 4, rate: 75, total: 300 },
      materials: 150,
    },
    job_info: {
      pm_number: '46369836',
      location: 'Stockton North - Grid 42B',
      date: '2025-10-10',
    },
  },
  // Add more mock results as needed
];

// Imports for missing components
const DollarSign = () => <span>$</span>;
const Activity = () => <span>📊</span>;

// Display names for debugging
ResultsScreen.displayName = 'ResultsScreen';
StatCard.displayName = 'StatCard';
ResultDetailModal.displayName = 'ResultDetailModal';

export default ResultsScreen;
