import { Routes } from '@angular/router';

export const ADMINISTRATION_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/role-management/role-management.component')
        .then((m) => m.RoleManagementComponent),
  },
  {
    path: 'roles',
    loadComponent: () =>
      import('./pages/role-management/role-management.component')
        .then((m) => m.RoleManagementComponent),
  },
  {
    path: 'roles/new',
    loadComponent: () =>
      import('./pages/role-add/role-add.component')
        .then((m) => m.RoleAddComponent),
  },
  {
    path: 'roles/edit/:id',
    loadComponent: () =>
      import('./pages/role-edit/role-edit.component')
        .then((m) => m.RoleEditComponent),
  },
  {
    path: 'roles/:id/edit',
    loadComponent: () =>
      import('./pages/role-edit/role-edit.component')
        .then((m) => m.RoleEditComponent),
  },
];
