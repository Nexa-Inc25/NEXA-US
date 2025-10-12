import React, { memo, useMemo } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface AnalyticsProps {
  results: Array<{
    infraction_id: string;
    repealable: boolean;
    confidence: number;
    cost_impact: {
      total_savings: number;
    };
    job_info: {
      date: string;
      location: string;
    };
  }>;
}

const DetailedAnalytics: React.FC<AnalyticsProps> = memo(({ results }) => {
  // Memoized analytics data
  const chartData = useMemo(() => {
    // Group by repealable status
    const statusBreakdown = [
      {
        name: 'Repealable',
        value: results.filter(r => r.repealable).length,
        color: '#10b981'
      },
      {
        name: 'Valid Go-Back',
        value: results.filter(r => !r.repealable).length,
        color: '#ef4444'
      }
    ];

    // Confidence distribution
    const confidenceRanges = [
      { range: '90-100%', count: 0, color: '#10b981' },
      { range: '80-89%', count: 0, color: '#3b82f6' },
      { range: '70-79%', count: 0, color: '#f59e0b' },
      { range: '<70%', count: 0, color: '#ef4444' }
    ];

    results.forEach(r => {
      const conf = r.confidence * 100;
      if (conf >= 90) confidenceRanges[0].count++;
      else if (conf >= 80) confidenceRanges[1].count++;
      else if (conf >= 70) confidenceRanges[2].count++;
      else confidenceRanges[3].count++;
    });

    // Cost impact by location
    const locationCosts = results.reduce((acc, r) => {
      const location = r.job_info.location.split(' - ')[0]; // Get area name
      if (!acc[location]) {
        acc[location] = { location, savings: 0, count: 0 };
      }
      acc[location].savings += r.cost_impact.total_savings;
      acc[location].count++;
      return acc;
    }, {} as Record<string, { location: string; savings: number; count: number }>);

    const topLocations = Object.values(locationCosts)
      .sort((a, b) => b.savings - a.savings)
      .slice(0, 5);

    // Daily trend (last 7 days)
    const dailyTrend = Array.from({ length: 7 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - i));
      const dateStr = date.toISOString().split('T')[0];
      
      const dayResults = results.filter(r => 
        r.job_info.date.startsWith(dateStr)
      );

      return {
        day: date.toLocaleDateString('en-US', { weekday: 'short' }),
        infractions: dayResults.length,
        savings: dayResults.reduce((sum, r) => sum + r.cost_impact.total_savings, 0)
      };
    });

    return {
      statusBreakdown,
      confidenceRanges,
      topLocations,
      dailyTrend
    };
  }, [results]);

  return (
    <div style={{
      padding: '2rem',
      background: 'white',
      borderRadius: '8px',
      margin: '1rem 2rem',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
    }}>
      <h2 style={{ marginBottom: '2rem', color: '#111827' }}>Analytics Dashboard</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
        {/* Status Breakdown Pie Chart */}
        <div>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem', color: '#374151' }}>
            Infraction Status Distribution
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={chartData.statusBreakdown}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({name, percent}) => `${name}: ${(percent * 100).toFixed(0)}%`}
                >
                  {chartData.statusBreakdown.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Confidence Distribution Bar Chart */}
        <div>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem', color: '#374151' }}>
            Confidence Score Distribution
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={chartData.confidenceRanges}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#2563eb">
                  {chartData.confidenceRanges.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Locations by Cost Savings */}
        <div>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem', color: '#374151' }}>
            Top Locations by Cost Savings
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={chartData.topLocations} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="location" type="category" width={100} />
                <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
                <Bar dataKey="savings" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Daily Trend Line Chart */}
        <div>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem', color: '#374151' }}>
            7-Day Trend
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={chartData.dailyTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="infractions" 
                  stroke="#2563eb" 
                  name="Infractions"
                  strokeWidth={2}
                />
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="savings" 
                  stroke="#10b981" 
                  name="Savings ($)"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Summary Statistics */}
      <div style={{
        marginTop: '2rem',
        padding: '1.5rem',
        background: '#f9fafb',
        borderRadius: '6px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '1rem'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e3a8a' }}>
            {results.length}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            Total Infractions
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#10b981' }}>
            {Math.round(results.filter(r => r.repealable).length / results.length * 100)}%
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            Repeal Rate
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f59e0b' }}>
            ${results.reduce((sum, r) => sum + r.cost_impact.total_savings, 0).toLocaleString()}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            Total Savings
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>
            {Math.round(results.reduce((sum, r) => sum + r.confidence, 0) / results.length * 100)}%
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            Avg Confidence
          </div>
        </div>
      </div>
    </div>
  );
});

DetailedAnalytics.displayName = 'DetailedAnalytics';

export default DetailedAnalytics;
