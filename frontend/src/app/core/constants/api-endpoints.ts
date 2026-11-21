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
    documents: (id: string | number) => `${BASE_URL}/users/${id}/documents`,
    deactivate: (id: string | number) => `${BASE_URL}/users/${id}/deactivate`,
    invite: (id: string | number) => `${BASE_URL}/users/${id}/invite`,
    inviteRetry: (id: string | number) => `${BASE_URL}/users/${id}/invite/retry`,
    approve: (id: string | number) => `${BASE_URL}/users/${id}/approve`,
    reject: (id: string | number) => `${BASE_URL}/approvals/employees/${id}/reject`,
  },

  /** Employee profile approval and email delivery endpoints */
  approvals: {
    employees: `${BASE_URL}/approvals/employees`,
    employee: (id: string | number) => `${BASE_URL}/approvals/employees/${id}`,
    document: (employeeId: string | number, documentId: string | number) =>
      `${BASE_URL}/approvals/employees/${employeeId}/documents/${documentId}`,
    approveEmployee: (id: string | number) => `${BASE_URL}/approvals/employees/${id}/approve`,
    rejectEmployee: (id: string | number) => `${BASE_URL}/approvals/employees/${id}/reject`,
    retryEmail: (id: string | number, event: 'approval' | 'rejection' | string) =>
      `${BASE_URL}/approvals/employees/${id}/emails/${event}/retry`,
    regenerateCredentials: (id: string | number) =>
      `${BASE_URL}/approvals/employees/${id}/credentials/regenerate`,
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
    employeeForm: `${BASE_URL}/employee/onboarding/form`,
    employeeSubmit: `${BASE_URL}/employee/onboarding/submit`,
  },
} as const;
