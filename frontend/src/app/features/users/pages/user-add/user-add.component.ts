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

  // 01 Personal Identity
  readonly firstName = signal('');
  readonly middleName = signal('');
  readonly lastName = signal('');

  // 02 Department & Role Assignment
  readonly department = signal('Engineering');
  readonly role = signal('Employee');
  readonly designation = signal('');
  readonly location = signal('Bengaluru');
  readonly entity = signal('Evolvus India Pvt Ltd');
  readonly code = signal('');

  // 03 Contact Information & Compliance
  readonly companyEmail = signal('');
  readonly personalEmail = signal('');
  readonly pfApplicable = signal<'Yes' | 'No'>('Yes');

  // 04 Employment Timeline
  readonly joiningDate = signal('');
  readonly startDate = signal('');
  readonly endDate = signal('');

  saveUser(): void {
    const firstName = this.firstName().trim();
    const lastName = this.lastName().trim();
    const department = this.department().trim();
    const role = this.role().trim();
    const designation = this.designation().trim();
    const code = this.code().trim();
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

    if (!department) {
      this.notification.show('Department is mandatory', 'error');
      return;
    }

    if (!role) {
      this.notification.show('Role is mandatory', 'error');
      return;
    }

    if (!designation) {
      this.notification.show('Designation is mandatory', 'error');
      return;
    }

    if (!code) {
      this.notification.show('User/Employee code is mandatory', 'error');
      return;
    }

    if (!companyEmail) {
      this.notification.show('Company email is mandatory', 'error');
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

    this.userService.addUser({
      firstName,
      middleName: this.middleName().trim(),
      lastName,
      department,
      role,
      designation,
      location: this.location(),
      entity: this.entity(),
      code,
      companyEmail,
      personalEmail,
      email: companyEmail,
      pfApplicable,
      joiningDate,
      startDate,
      endDate: this.endDate().trim(),
      status: 'Active',
      profile: 'Pending',
    });

    const fullName = [firstName, lastName].filter(Boolean).join(' ');
    this.notification.show(`User "${fullName}" created successfully!`, 'success');
    void this.router.navigateByUrl('/users');
  }
}
