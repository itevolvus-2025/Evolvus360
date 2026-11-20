import { Routes } from '@angular/router';

export const USER_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/user-list/user-list.component').then(
        (m) => m.UserListComponent
      ),
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./pages/user-add/user-add.component').then(
        (m) => m.UserAddComponent
      ),
  },
  {
    path: 'edit/:id',
    loadComponent: () =>
      import('./pages/user-edit/user-edit.component').then(
        (m) => m.UserEditComponent
      ),
  },
  {
    path: ':id/edit',
    loadComponent: () =>
      import('./pages/user-edit/user-edit.component').then(
        (m) => m.UserEditComponent
      ),
  },
];
