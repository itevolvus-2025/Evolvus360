/**
 * Centralized list of available module permissions for role management.
 * These permissions directly control module visibility in user navigation and authorization guards.
 */
export const AVAILABLE_PERMISSIONS: readonly string[] = [
  'Dashboard',
  'Role Management',
  'User Management',
  'Approval',
  'Project',
  'Leave Request',
  'Leave Management',
] as const;

export type SystemPermission = (typeof AVAILABLE_PERMISSIONS)[number];
