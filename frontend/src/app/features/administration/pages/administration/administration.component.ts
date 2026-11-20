import { Component } from '@angular/core';
import { RoleManagementComponent } from '../role-management/role-management.component';

@Component({
  selector: 'app-administration',
  standalone: true,
  imports: [RoleManagementComponent],
  template: `<app-role-management />`,
})
export class AdministrationComponent {}
