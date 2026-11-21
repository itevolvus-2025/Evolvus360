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
import { UserService, UserRow, UserStatus, ProfileStatus } from '../../data-access/user.service';
import { MasterDataOption } from '../../../../core/models/api.models';

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

  readonly userId = signal<number | string>('');
  readonly departments = this.userService.departments;
  readonly roles = this.userService.roles;
  readonly entities = this.userService.entities;

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
  readonly code = signal('');

  // 03 Contact Information & Compliance
  readonly companyEmail = signal('');
  readonly personalEmail = signal('');
  readonly pfApplicable = signal<'Yes' | 'No'>('Yes');
  readonly status = signal<UserStatus>('Active');
  readonly profile = signal<ProfileStatus>('Pending');
  readonly reasonForChange = signal('');

  // 04 Employment Timeline
  readonly joiningDate = signal('');
  readonly startDate = signal('');
  readonly endDate = signal('');

  // Delete Confirmation Modal
  readonly showDeleteModal = signal(false);

  ngOnInit(): void {
    this.userService.loadMasterData();
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      const id: number | string = /^\d+$/.test(idParam) ? parseInt(idParam, 10) : idParam;
      this.userId.set(id);

      this.userService.getEmployee(id, (existing) => {
        this.populateFields(existing);
      }, (message) => {
        this.notification.show(message, 'error');
      });
    }
  }

  private populateFields(existing: UserRow): void {
    this.firstName.set(existing.firstName || '');
    this.middleName.set(existing.middleName || '');
    this.lastName.set(existing.lastName || '');
    this.department.set(existing.departmentId || existing.department || '');
    this.role.set(existing.roleId || existing.role || '');
    this.designation.set(existing.designation || '');
    this.location.set(existing.location || '');
    this.entity.set(existing.entityId || existing.entity || '');
    this.code.set(existing.code || '');
    this.companyEmail.set(existing.companyEmail || existing.email || '');
    this.personalEmail.set(existing.personalEmail || '');
    this.pfApplicable.set(existing.pfApplicable || 'Yes');
    this.status.set(existing.status || 'Active');
    this.profile.set(existing.profile || 'Pending');
    if (existing.reasonForChange) {
      this.reasonForChange.set(existing.reasonForChange);
    }
    this.joiningDate.set(existing.joiningDate || '');
    this.startDate.set(existing.startDate || '');
    this.endDate.set(existing.endDate || '');
  }

  selectOption(event: Event, target: 'department' | 'role' | 'entity'): void {
    const value = (event.target as HTMLSelectElement).value;
    if (target === 'department') this.department.set(value);
    else if (target === 'role') this.role.set(value);
    else this.entity.set(value);
  }

  saveUser(): void {
    const firstName = this.firstName().trim();
    const lastName = this.lastName().trim();
    const department = this.department().trim();
    const role = this.role().trim();
    const designation = this.designation().trim();
    const companyEmail = this.companyEmail().trim();
    const personalEmail = this.personalEmail().trim();
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

    if (!personalEmail) {
      this.notification.show('Personal email is mandatory', 'error');
      return;
    }

    if (!this.reasonForChange().trim()) {
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

    const parseDate = (value: string): string => {
      const match = value.match(/^(\d{2})-(\d{2})-(\d{4})$/);
      return match ? `${match[3]}-${match[2]}-${match[1]}` : value;
    };

    const id = this.userId();
    const fullName = [firstName, lastName].filter(Boolean).join(' ');

    // Every persisted user must be updated through the backend API.
    const isBackendUuid = typeof id === 'string' && id.includes('-') && id.length >= 32;

    if (isBackendUuid) {
      const deptOption = this.departments().find((d) => d.id === department || d.name === department);
      const roleOption = this.roles().find((r) => r.id === role || r.name === role);
      const entityOption = this.entities().find((e) => e.id === this.entity() || e.name === this.entity());

      this.userService.updateEmployee(id, {
        first_name: firstName,
        middle_name: this.middleName().trim() || null,
        last_name: lastName,
        reason_for_change: this.reasonForChange().trim(),
        department_id: deptOption?.id || (department.includes('-') ? department : undefined),
        role_id: roleOption?.id || (role.includes('-') ? role : undefined),
        entity_id: entityOption?.id || (this.entity().includes('-') ? this.entity() : undefined),
        designation,
        location: this.location().trim() || null,
        company_email: companyEmail || null,
        personal_email: personalEmail,
        pf_applicable: this.pfApplicable() === 'Yes',
        joining_date: parseDate(joiningDate),
        start_date: parseDate(startDate),
        end_date: this.endDate().trim() ? parseDate(this.endDate().trim()) : null,
        account_status: this.status() === 'Active'
          ? 'ACTIVE'
          : this.status() === 'Pending'
            ? 'INVITED'
            : 'INACTIVE',
      }, () => {
        this.notification.show(`User "${fullName}" updated successfully!`, 'success');
        void this.router.navigateByUrl('/users');
      }, (errMsg) => {
        this.notification.show(errMsg, 'error');
      });
      return;
    }

    this.notification.show('This user does not have a valid server ID and cannot be saved.', 'error');
  }

  sendInvitationEmail(): void {
    this.userService.sendInvitation(this.userId(), (success, message) => {
      this.notification.show(message, success ? 'success' : 'error');
    });
  }

  retryInvitationEmail(): void {
    this.userService.retryInvitation(this.userId(), (success, message) => {
      this.notification.show(message, success ? 'success' : 'error');
    });
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
