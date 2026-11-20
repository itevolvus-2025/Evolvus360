import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { NotificationService } from '../../../../core/services/notification.service';
import { UserService, UserStatus, ProfileStatus } from '../../data-access/user.service';

@Component({
  selector: 'app-user-edit',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent],
  templateUrl: './user-edit.component.html',
  styleUrl: './user-edit.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserEditComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly userService = inject(UserService);
  private readonly notification = inject(NotificationService);

  readonly userId = signal<number | string>(1);

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
  readonly status = signal<UserStatus>('Active');
  readonly profile = signal<ProfileStatus>('Approved');
  readonly reasonForChange = signal(
    'Update user role and organizational identity profile'
  );

  // 04 Employment Timeline
  readonly joiningDate = signal('');
  readonly startDate = signal('');
  readonly endDate = signal('');

  // Delete Confirmation Modal
  readonly showDeleteModal = signal(false);

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      const id: number | string = /^\d+$/.test(idParam) ? parseInt(idParam, 10) : idParam;
      this.userId.set(id);

      const existing = this.userService.getUserById(id);
      if (existing) {
        this.firstName.set(existing.firstName || '');
        this.middleName.set(existing.middleName || '');
        this.lastName.set(existing.lastName || '');
        this.department.set(existing.department || 'Engineering');
        this.role.set(existing.role || 'Employee');
        this.designation.set(existing.designation || '');
        this.location.set(existing.location || 'Bengaluru');
        this.entity.set(existing.entity || 'Evolvus India Pvt Ltd');
        this.code.set(existing.code || '');
        this.companyEmail.set(existing.companyEmail || existing.email || '');
        this.personalEmail.set(existing.personalEmail || '');
        this.pfApplicable.set(existing.pfApplicable || 'Yes');
        this.status.set(existing.status || 'Active');
        this.profile.set(existing.profile || 'Approved');
        if (existing.reasonForChange) {
          this.reasonForChange.set(existing.reasonForChange);
        }
        this.joiningDate.set(existing.joiningDate || '17-11-2026');
        this.startDate.set(existing.startDate || '17-11-2026');
        this.endDate.set(existing.endDate || '');
      }
    }
  }

  saveUser(): void {
    const firstName = this.firstName().trim();
    const lastName = this.lastName().trim();
    const department = this.department().trim();
    const role = this.role().trim();
    const designation = this.designation().trim();
    const code = this.code().trim();
    const companyEmail = this.companyEmail().trim();
    const personalEmail = this.personalEmail().trim();
    const joiningDate = this.joiningDate().trim();
    const startDate = this.startDate().trim();
    const reasonForChange = this.reasonForChange().trim();

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

    if (!reasonForChange) {
      this.notification.show('Reason for change is mandatory', 'error');
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

    this.userService.updateUser(this.userId(), {
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
      pfApplicable: this.pfApplicable(),
      status: this.status(),
      profile: this.profile(),
      reasonForChange,
      joiningDate,
      startDate,
      endDate: this.endDate().trim(),
    });

    const fullName = [firstName, lastName].filter(Boolean).join(' ');
    this.notification.show(`User "${fullName}" updated successfully!`, 'success');
    void this.router.navigateByUrl('/users');
  }

  openDeleteConfirm(): void {
    this.showDeleteModal.set(true);
  }

  closeDeleteConfirm(): void {
    this.showDeleteModal.set(false);
  }

  confirmDelete(): void {
    const fullName = [this.firstName(), this.lastName()].filter(Boolean).join(' ') || this.code();
    this.userService.deleteUser(this.userId());
    this.showDeleteModal.set(false);
    this.notification.show(`User "${fullName}" has been deleted.`, 'info');
    void this.router.navigateByUrl('/users');
  }
}
