import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { NotificationService } from '../../../../core/services/notification.service';
import { UserService } from '../../data-access/user.service';
import { MasterDataOption } from '../../../../core/models/api.models';

@Component({
  selector: 'app-user-add',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent],
  templateUrl: './user-add.component.html',
  styleUrl: './user-add.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserAddComponent {
  private readonly router = inject(Router);
  private readonly userService = inject(UserService);
  private readonly notification = inject(NotificationService);
  readonly userServiceRef = this.userService;

  // 01 Personal Identity
  readonly firstName = signal('');
  readonly middleName = signal('');
  readonly lastName = signal('');

  // 02 Department & Role Assignment
  readonly department = signal('');
  readonly role = signal('');
  readonly designation = signal('');
  readonly location = signal('');
  readonly entity = signal('');

  // 03 Contact Information & Compliance
  readonly companyEmail = signal('');
  readonly personalEmail = signal('');
  readonly pfApplicable = signal<'Yes' | 'No'>('Yes');

  // 04 Employment Timeline
  readonly joiningDate = signal('');
  readonly startDate = signal('');
  readonly endDate = signal('');

  constructor() {
    this.userService.loadMasterData();
  }

  readonly departments = this.userService.departments;
  readonly roles = this.userService.roles;
  readonly entities = this.userService.entities;

  selectOption(event: Event, target: 'department' | 'role' | 'entity'): void {
    const value = (event.target as HTMLSelectElement).value;
    if (target === 'department') this.department.set(value);
    else if (target === 'role') this.role.set(value);
    else this.entity.set(value);
  }

  optionName(options: MasterDataOption[], id: string): string {
    return options.find((option) => option.id === id)?.name || '';
  }

  saveUser(): void {
    const firstName = this.firstName().trim();
    const lastName = this.lastName().trim();
    const departmentId = this.department().trim();
    const roleId = this.role().trim();
    const designation = this.designation().trim();
    const entityId = this.entity().trim();
    const companyEmail = this.companyEmail().trim();
    const personalEmail = this.personalEmail().trim();
    const pfApplicable = this.pfApplicable();
    const joiningDate = this.joiningDate().trim();
    const startDate = this.startDate().trim();

    if (!firstName) {
      this.notification.show('First name is mandatory', 'error');
      return;
    }

    if (!lastName) {
      this.notification.show('Last name is mandatory', 'error');
      return;
    }

    if (!departmentId) {
      this.notification.show('Department is mandatory', 'error');
      return;
    }

    if (!roleId) {
      this.notification.show('Role is mandatory', 'error');
      return;
    }

    if (!designation) {
      this.notification.show('Designation is mandatory', 'error');
      return;
    }

    if (!personalEmail) {
      this.notification.show('Personal email is mandatory', 'error');
      return;
    }

    if (!joiningDate) {
      this.notification.show('Joining date is mandatory', 'error');
      return;
    }

    if (!startDate) {
      this.notification.show('Start date is mandatory', 'error');
      return;
    }

    if (!entityId) {
      this.notification.show('Entity is mandatory', 'error');
      return;
    }

    const parseDate = (value: string): string => {
      const match = value.match(/^(\d{2})-(\d{2})-(\d{4})$/);
      return match ? `${match[3]}-${match[2]}-${match[1]}` : value;
    };

    this.userService.createEmployee({
      first_name: firstName,
      middle_name: this.middleName().trim() || null,
      last_name: lastName,
      department_id: departmentId,
      role_id: roleId,
      designation,
      entity_id: entityId,
      location: this.location().trim() || null,
      company_email: companyEmail || null,
      personal_email: personalEmail,
      pf_applicable: pfApplicable === 'Yes',
      joining_date: parseDate(joiningDate),
      start_date: parseDate(startDate),
      end_date: this.endDate().trim() ? parseDate(this.endDate().trim()) : null,
    }, (result) => {
      const fullName = [firstName, lastName].filter(Boolean).join(' ');
      this.notification.show(
        result.email_dispatch_status === 'FAILED'
          ? `User "${fullName}" created, but invitation email failed. Retry it from User Management.`
          : `User "${fullName}" created and invitation sent.`,
        result.email_dispatch_status === 'FAILED' ? 'info' : 'success'
      );
      void this.router.navigateByUrl('/users');
    }, (message) => this.notification.show(message, 'error'));
  }
}
