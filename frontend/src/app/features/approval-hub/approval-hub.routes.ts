import { Routes } from '@angular/router';
import { ApprovalHubComponent } from './pages/approval-hub/approval-hub.component';

export const APPROVAL_HUB_ROUTES: Routes = [
  {
    path: '',
    component: ApprovalHubComponent,
  },
  {
    path: ':id',
    component: ApprovalHubComponent,
  },
];
