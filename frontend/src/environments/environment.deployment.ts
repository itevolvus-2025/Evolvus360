/**
 * Deployment environment configuration for Evolvus360 Frontend.
 * Used when building with: npm run build:deployment
 * 
 * In production deployment, relative API path '/api/v1' enables seamless reverse-proxying
 * through Nginx, Apache, or cloud load balancers without CORS or hardcoded hostnames.
 */
export const environment = {
  production: true,
  apiUrl: '/api/v1',
  appName: 'Evolvus360 HRMS',
  appVersion: '1.0.0',
  enableDebugLogging: false,
  sessionTimeoutMinutes: 60,
  tokenStorageKey: 'evolvus360_access_token',
  refreshTokenStorageKey: 'evolvus360_refresh_token',
  apiTimeoutMs: 30000,
};
