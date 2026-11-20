import { environment } from '../../../environments/environment';

/**
 * Centralized API endpoints registry following Angular enterprise coding standards.
 * Base URL is driven by environment configuration.
 */
const BASE_URL = environment.apiUrl.replace(/\/$/, '');

export const API_ENDPOINTS = {
  /** Authentication & Session endpoints */
  auth: {
    login: `${BASE_URL}/auth/login`,
    refresh: `${BASE_URL}/auth/refresh`,
    logout: `${BASE_URL}/auth/logout`,
    forgotPassword: `${BASE_URL}/auth/forgot-password`,
    resetPassword: `${BASE_URL}/auth/reset-password`,
    me: `${BASE_URL}/auth/me`,
  },

  /** User Management endpoints */
  users: {
    list: `${BASE_URL}/users`,
    create: `${BASE_URL}/users`,
    detail: (id: string | number) => `${BASE_URL}/users/${id}`,
    update: (id: string | number) => `${BASE_URL}/users/${id}`,
    invite: (id: string | number) => `${BASE_URL}/users/${id}/invite`,
    inviteRetry: (id: string | number) => `${BASE_URL}/users/${id}/invite/retry`,
    approve: (id: string | number) => `${BASE_URL}/users/${id}/approve`,
  },

  /** Role Management endpoints */
  roles: {
    list: `${BASE_URL}/roles`,
    create: `${BASE_URL}/roles`,
    detail: (id: string | number) => `${BASE_URL}/roles/${id}`,
    update: (id: string | number) => `${BASE_URL}/roles/${id}`,
    delete: (id: string | number) => `${BASE_URL}/roles/${id}`,
  },

  /** Master Data endpoints */
  masterData: {
    departments: `${BASE_URL}/master-data/departments`,
    entities: `${BASE_URL}/master-data/entities`,
    roles: `${BASE_URL}/master-data/roles`,
  },

  /** Onboarding endpoints */
  onboarding: {
    validate: `${BASE_URL}/onboarding/invitations/validate`,
    submit: `${BASE_URL}/onboarding/submit`,
  },
} as const;
