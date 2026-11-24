import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  {
    path: 'auth',
    loadComponent: () =>
      import('./layout/auth-layout/auth-layout.component')
        .then((m) => m.AuthLayoutComponent),
    loadChildren: () =>
      import('./features/auth/auth.routes')
        .then((m) => m.AUTH_ROUTES)
  },
  {
    path: 'onboarding',
    loadChildren: () =>
      import('./features/onboarding/onboarding.routes')
        .then((m) => m.ONBOARDING_ROUTES)
  },
  {
    path: 'forgot-password',
    redirectTo: 'auth/forgot-password',
    pathMatch: 'full'
  },
  {
    path: 'reset-password',
    redirectTo: 'auth/reset-password'
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./layout/main-layout/main-layout.component')
        .then((m) => m.MainLayoutComponent),
    children: [
      {
        path: 'dashboard',
        canActivate: [roleGuard],
        data: { permissions: ['Dashboard'] },
        loadChildren: () =>
          import('./features/dashboard/dashboard.routes')
            .then((m) => m.DASHBOARD_ROUTES)
      },
      {
        path: 'users',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/users/user.routes')
            .then((m) => m.USER_ROUTES)
      },
      {
        path: 'employees',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/users/user.routes')
            .then((m) => m.USER_ROUTES)
      },
      {
        path: 'organization',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/organization/organization.routes')
            .then((m) => m.ORGANIZATION_ROUTES)
      },
      {
        path: 'attendance',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/attendance/attendance.routes')
            .then((m) => m.ATTENDANCE_ROUTES)
      },
      {
        path: 'approval-hub',
        canActivate: [roleGuard],
        data: { permissions: ['Approval'] },
        loadChildren: () =>
          import('./features/approval-hub/approval-hub.routes')
            .then((m) => m.APPROVAL_HUB_ROUTES)
      },
      {
        path: 'projects',
        canActivate: [roleGuard],
        data: { permissions: ['Project'] },
        loadChildren: () =>
          import('./features/projects/project.routes')
            .then((m) => m.PROJECT_ROUTES)
      },
      {
        path: 'leave',
        canActivate: [roleGuard],
        data: { permissions: ['Leave Request', 'Leave Management'] },
        loadChildren: () =>
          import('./features/leave/leave.routes')
            .then((m) => m.LEAVE_ROUTES)
      },
      {
        path: 'timesheets',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/timesheets/timesheet.routes')
            .then((m) => m.TIMESHEET_ROUTES)
      },
      {
        path: 'payroll',
        canActivate: [roleGuard],
        data: { roles: ['Super Admin', 'HR Manager', 'Payroll Viewer'] },
        loadChildren: () =>
          import('./features/payroll/payroll.routes')
            .then((m) => m.PAYROLL_ROUTES)
      },
      {
        path: 'performance',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/performance/performance.routes')
            .then((m) => m.PERFORMANCE_ROUTES)
      },
      {
        path: 'recruitment',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/recruitment/recruitment.routes')
            .then((m) => m.RECRUITMENT_ROUTES)
      },
      {
        path: 'documents',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/documents/document.routes')
            .then((m) => m.DOCUMENT_ROUTES)
      },
      {
        path: 'reports',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/reports/report.routes')
            .then((m) => m.REPORT_ROUTES)
      },
      {
        path: 'administration',
        canActivate: [roleGuard],
        data: { permissions: ['Role Management'] },
        loadChildren: () =>
          import('./features/administration/administration.routes')
            .then((m) => m.ADMINISTRATION_ROUTES)
      },
      {
        path: 'settings',
        canActivate: [roleGuard],
        data: { permissions: ['User Management'] },
        loadChildren: () =>
          import('./features/settings/settings.routes')
            .then((m) => m.SETTINGS_ROUTES)
      },
      {
        path: 'icons',
        canActivate: [roleGuard],
        data: { permissions: ['Dashboard'] },
        loadComponent: () =>
          import('./features/icons-gallery/icons-gallery.component')
            .then((m) => m.IconsGalleryComponent)
      },
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'dashboard'
      }
    ]
  },
  {
    path: 'access-denied',
    loadComponent: () =>
      import('./features/auth/pages/access-denied/access-denied.component')
        .then((m) => m.AccessDeniedComponent)
  },
  {
    path: '**',
    loadComponent: () =>
      import('./features/auth/pages/not-found/not-found.component')
        .then((m) => m.NotFoundComponent)
  }
];
