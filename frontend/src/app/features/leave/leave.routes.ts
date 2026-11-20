import { Routes } from '@angular/router';

export const LEAVE_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/leave/leave.component').then((m) => m.LeaveComponent),
  },
  {
    path: 'request',
    loadComponent: () =>
      import('./pages/leave-request/leave-request.component').then(
        (m) => m.LeaveRequestComponent
      ),
  },
];
