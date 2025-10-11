/**
 * Theme Configuration for NEXA Mobile App
 * Steel blue theme matching Streamlit dashboard
 */

export const theme = {
  colors: {
    primary: '#4682B4',      // Steel blue
    primaryDark: '#36648B',  // Darker steel blue
    primaryLight: '#87CEEB', // Sky blue
    
    success: '#28a745',      // Green for repealable/high value
    warning: '#ffc107',      // Yellow for medium confidence
    danger: '#dc3545',       // Red for valid infractions/low confidence
    
    background: '#f8f9fa',   // Light gray background
    surface: '#ffffff',      // White cards/surfaces
    text: '#212529',         // Dark text
    textSecondary: '#6c757d', // Gray text
    border: '#dee2e6',       // Light border
    
    // Cost impact colors
    highValue: '#28a745',    // Green for >$10k
    mediumValue: '#ffc107',  // Yellow for $5k-$10k
    lowValue: '#17a2b8',     // Blue for <$5k
  },
  
  fontSizes: {
    small: 12,
    medium: 16,
    large: 20,
    xlarge: 24,
  },
  
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  
  borderRadius: {
    small: 4,
    medium: 8,
    large: 12,
  },
  
  shadows: {
    small: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.1,
      shadowRadius: 2,
      elevation: 2,
    },
    medium: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.15,
      shadowRadius: 4,
      elevation: 4,
    },
  },
};

export type Theme = typeof theme;
