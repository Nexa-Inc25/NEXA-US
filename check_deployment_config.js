#!/usr/bin/env node

/**
 * Deployment Configuration Checker
 * Verifies all API endpoints are using HTTPS
 */

const https = require('https');
const http = require('http');

const ENDPOINTS_TO_CHECK = [
  {
    name: 'Doc Analyzer API',
    url: 'https://nexa-doc-analyzer-oct2025.onrender.com/status',
    expected: 'https'
  },
  {
    name: 'Dashboard',
    url: 'https://nexa-dashboard.onrender.com/',
    expected: 'https'
  }
];

console.log('🔍 NEXA Deployment Configuration Check\n');
console.log('=' .repeat(50));

// Check environment variables
console.log('\n📋 Environment Variables:');
console.log('-'.repeat(50));

const envVars = {
  'ANALYZER_URL': process.env.ANALYZER_URL,
  'REACT_APP_DOC_ANALYZER_URL': process.env.REACT_APP_DOC_ANALYZER_URL,
  'NODE_ENV': process.env.NODE_ENV
};

for (const [key, value] of Object.entries(envVars)) {
  if (value) {
    const protocol = value.startsWith('https') ? '✅ HTTPS' : '❌ HTTP';
    console.log(`${key}: ${value} ${value.includes('http') ? protocol : ''}`);
  } else {
    console.log(`${key}: Not set`);
  }
}

// Check if endpoints are accessible
console.log('\n🌐 Endpoint Accessibility:');
console.log('-'.repeat(50));

async function checkEndpoint(endpoint) {
  return new Promise((resolve) => {
    const url = new URL(endpoint.url);
    const client = url.protocol === 'https:' ? https : http;
    
    const req = client.get(endpoint.url, (res) => {
      const protocol = url.protocol.replace(':', '');
      const status = res.statusCode;
      let icon = '✅';
      
      if (protocol !== endpoint.expected) {
        icon = '⚠️';
      }
      if (status >= 400) {
        icon = '❌';
      }
      
      console.log(`${icon} ${endpoint.name}:`);
      console.log(`   URL: ${endpoint.url}`);
      console.log(`   Protocol: ${protocol.toUpperCase()} (expected: ${endpoint.expected.toUpperCase()})`);
      console.log(`   Status: ${status}`);
      
      // Check for redirect
      if (res.headers.location) {
        console.log(`   ↳ Redirects to: ${res.headers.location}`);
      }
      
      resolve();
    });
    
    req.on('error', (err) => {
      console.log(`❌ ${endpoint.name}:`);
      console.log(`   URL: ${endpoint.url}`);
      console.log(`   Error: ${err.message}`);
      resolve();
    });
    
    req.setTimeout(5000, () => {
      console.log(`⏱️ ${endpoint.name}: Timeout after 5s`);
      req.destroy();
      resolve();
    });
  });
}

// Run checks
Promise.all(ENDPOINTS_TO_CHECK.map(checkEndpoint)).then(() => {
  console.log('\n' + '='.repeat(50));
  console.log('🔧 Recommended Actions:');
  console.log('-'.repeat(50));
  console.log('1. If any URLs show HTTP instead of HTTPS:');
  console.log('   → Update environment variables in Render/Vercel dashboard');
  console.log('   → Redeploy the service');
  console.log('\n2. For local development:');
  console.log('   → Update .env files with HTTPS URLs');
  console.log('   → Restart development servers');
  console.log('\n3. Clear browser cache and test again');
  console.log('='.repeat(50));
});
