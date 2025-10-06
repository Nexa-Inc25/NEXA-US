import Constants from 'expo-constants';

// Environment-specific configuration
const ENV = {
  development: {
    apiUrl: 'http://192.168.1.176:4000',
    auth0Domain: 'dev-kbnx7pja3zpg0lud.us.auth0.com',
    auth0ClientId: 'glA8cdWZIAKvNUUjxd2XQRcwLI4HM2f1',
    auth0Audience: 'https://api.nexa.local',
    environment: 'development',
    enableDebug: true,
  },
  preview: {
    apiUrl: 'https://nexa-api-staging.onrender.com',
    auth0Domain: 'dev-kbnx7pja3zpg0lud.us.auth0.com',
    auth0ClientId: 'glA8cdWZIAKvNUUjxd2XQRcwLI4HM2f1',
    auth0Audience: 'https://api.nexa-staging.local',
    environment: 'preview',
    enableDebug: true,
  },
  production: {
    apiUrl: 'https://nexa-api.onrender.com',
    auth0Domain: 'nexa-usa.us.auth0.com', // Update with production Auth0
    auth0ClientId: 'PRODUCTION_CLIENT_ID', // Update with production client
    auth0Audience: 'https://api.nexa-usa.io',
    environment: 'production',
    enableDebug: false,
  },
};

// Get environment from EAS build or default to development
const getEnvironment = () => {
  const env = Constants.expoConfig?.extra?.EXPO_PUBLIC_ENV || 'development';
  return ENV[env] || ENV.development;
};

export default getEnvironment();

// Export individual configs for backward compatibility
export const API_BASE_URL = getEnvironment().apiUrl;
export const AUTH0_DOMAIN = getEnvironment().auth0Domain;
export const AUTH0_CLIENT_ID = getEnvironment().auth0ClientId;
export const AUTH0_AUDIENCE = getEnvironment().auth0Audience;
export const IS_DEBUG = getEnvironment().enableDebug;
export const ENVIRONMENT = getEnvironment().environment;
