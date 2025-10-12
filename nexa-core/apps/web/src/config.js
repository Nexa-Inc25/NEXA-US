// API Configuration for different environments
const config = {
  development: {
    API_URL: 'http://localhost:8000',
    ENV: 'development'
  },
  production: {
    API_URL: process.env.REACT_APP_API_URL || 'https://nexa-doc-analyzer-oct2025.onrender.com',
    ENV: 'production'
  }
};

const environment = process.env.NODE_ENV || 'development';

export default config[environment];
