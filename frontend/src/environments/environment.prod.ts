/**
 * Production environment configuration for Evolvus360 Frontend.
 * Used when building with: npm run build:prod
 */
export const environment = {
  production: true,
  apiUrl: 'http://3.111.89.13:7006/api/v1',
  deploymentUrl: 'http://3.111.89.13:7006/',
  appName: 'Evolvus360 HRMS',
  appVersion: '1.0.0',
  enableDebugLogging: false,
  sessionTimeoutMinutes: 60,
  tokenStorageKey: 'evolvus360_access_token',
  refreshTokenStorageKey: 'evolvus360_refresh_token',
  apiTimeoutMs: 30000,
};
