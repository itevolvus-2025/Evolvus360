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

  // 05 Profile & Employee Details
  readonly employeeDetails = signal<any>(null);
  readonly todayDate = new Date().toISOString().slice(0, 10);
  readonly sensitiveUpdates = signal<Record<string, string>>({});
  readonly selectedDocuments = signal<{ identity_proof: File | null; cancelled_cheque: File | null }>({
    identity_proof: null,
    cancelled_cheque: null,
  });

  // Deactivate Confirmation Modal
  readonly showDeactivateModal = signal(false);
  readonly isDeactivating = signal(false);

  ngOnInit(): void {
    this.userService.loadMasterData();
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      const id: number | string = /^\d+$/.test(idParam) ? parseInt(idParam, 10) : idParam;
      this.userId.set(id);

      this.userService.getEmployee(id, (existing, fullData) => {
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

    const deptId = existing.departmentId || this.resolveDepartmentId(existing.department);
    this.department.set(deptId);

    const roleId = existing.roleId || this.resolveRoleId(existing.role);
    this.role.set(roleId);

    this.designation.set(existing.designation || '');
    this.location.set(existing.location || '');

    const entityId = existing.entityId || this.resolveEntityId(existing.entity);
    this.entity.set(entityId);

    this.code.set(existing.code || '');
    this.companyEmail.set(existing.companyEmail || existing.email || '');
    this.personalEmail.set(existing.personalEmail || '');
    this.pfApplicable.set(existing.pfApplicable || 'Yes');
    this.status.set(existing.status || 'Active');
    this.profile.set(existing.profile || 'Pending');
    if (existing.reasonForChange) {
      this.reasonForChange.set(existing.reasonForChange);
    }
    this.joiningDate.set(this.formatToIso(existing.joiningDate || ''));
    this.startDate.set(this.formatToIso(existing.startDate || ''));
    this.endDate.set(this.formatToIso(existing.endDate || ''));
    if (existing.employeeDetails) {
      this.employeeDetails.set(existing.employeeDetails);
    }
  }

  private resolveDepartmentId(val?: string): string {
    if (!val) return '';
    const match = this.departments().find((d) => d.id === val || d.name.toLowerCase() === val.toLowerCase());
    return match ? match.id : val;
  }

  private resolveRoleId(val?: string): string {
    if (!val) return '';
    const match = this.roles().find((r) => r.id === val || r.name.toLowerCase() === val.toLowerCase());
    return match ? match.id : val;
  }

  private resolveEntityId(val?: string): string {
    if (!val) return '';
    const match = this.entities().find((e) => e.id === val || e.name.toLowerCase() === val.toLowerCase());
    return match ? match.id : val;
  }

  private formatToIso(val: string): string {
    if (!val) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(val)) return val;
    const match = /^(\d{2})-(\d{2})-(\d{4})$/.exec(val);
    return match ? `${match[3]}-${match[2]}-${match[1]}` : val;
  }

  selectOption(event: Event, target: 'department' | 'role' | 'entity'): void {
    const value = (event.target as HTMLSelectElement).value;
    if (target === 'department') this.department.set(value);
    else if (target === 'role') this.role.set(value);
    else this.entity.set(value);
  }

  openDatePicker(input: HTMLInputElement): void {
    try {
      if ('showPicker' in input && typeof input.showPicker === 'function') {
        input.showPicker();
      } else {
        input.focus();
      }
    } catch {
      input.focus();
    }
  }

  updateEmployeeDetail(field: string, value: string | string[]): void {
    const current = this.employeeDetails();
    if (current) this.employeeDetails.set({ ...current, [field]: value });
  }

  updateNestedEmployeeDetail(group: 'emergency_contact' | 'bank_details', field: string, value: string): void {
    const current = this.employeeDetails();
    if (current) {
      this.employeeDetails.set({
        ...current,
        [group]: { ...(current[group] || {}), [field]: value },
      });
    }
  }

  updateSensitiveDetail(field: string, value: string): void {
    this.sensitiveUpdates.update((current) => ({ ...current, [field]: value }));
  }

  updateLanguages(value: string): void {
    this.updateEmployeeDetail(
      'languages',
      value.split(',').map((language) => language.trim()).filter(Boolean),
    );
  }

  selectDocument(type: 'identity_proof' | 'cancelled_cheque', event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0] ?? null;
    this.selectedDocuments.update((current) => ({ ...current, [type]: file }));
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
    const endDate = this.endDate().trim();

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

    if (endDate && startDate > endDate) {
      this.notification.show('End date must be on or after start date', 'error');
      return;
    }

    const parseDate = (value: string): string => {
      if (!value) return '';
      if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
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

      const payload: Record<string, unknown> = {
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
        end_date: endDate ? parseDate(endDate) : null,
        account_status: this.status() === 'Active'
          ? 'ACTIVE'
          : this.status() === 'Pending'
            ? 'INVITED'
            : 'INACTIVE',
      };
      const employeeDetails = this.employeeDetails();
      if (employeeDetails) {
        Object.assign(payload, {
          date_of_birth: employeeDetails.date_of_birth,
          gender: employeeDetails.gender,
          blood_group: employeeDetails.blood_group,
          mother_tongue: employeeDetails.mother_tongue,
          marital_status: employeeDetails.marital_status,
          mobile_number: employeeDetails.mobile_number,
          landline_number: employeeDetails.landline_number,
          alternate_phone_number: employeeDetails.alternate_phone_number,
          emergency_contact_name: employeeDetails.emergency_contact?.name,
          emergency_contact_phone: employeeDetails.emergency_contact?.phone,
          emergency_contact_relationship: employeeDetails.emergency_contact?.relationship,
          bank_name: employeeDetails.bank_details?.bank_name,
          account_holder_name: employeeDetails.bank_details?.account_holder_name,
          ifsc_code: employeeDetails.bank_details?.ifsc_code,
          qualification: employeeDetails.qualification,
          skills: employeeDetails.skills,
          hobbies: employeeDetails.hobbies,
          languages: Array.isArray(employeeDetails.languages) ? employeeDetails.languages : [],
          languages_read_and_written: employeeDetails.languages_read_and_written,
        });
        for (const [field, value] of Object.entries(this.sensitiveUpdates())) {
          if (value.trim()) payload[field] = value.trim();
        }
      }

      this.userService.updateEmployee(id, payload, () => {
        const documents = this.selectedDocuments();
        if (documents.identity_proof || documents.cancelled_cheque) {
          this.userService.updateEmployeeDocuments(id, documents, () => {
            this.finishSave(fullName);
          }, (message) => {
            this.notification.show(`Profile details were saved, but document update failed: ${message}`, 'error');
          });
          return;
        }
        this.finishSave(fullName);
      }, (errMsg) => {
        this.notification.show(errMsg, 'error');
      });
      return;
    }

    this.notification.show('This user does not have a valid server ID and cannot be saved.', 'error');
  }

  private finishSave(fullName: string): void {
    this.notification.show(`User "${fullName}" updated successfully!`, 'success');
    void this.router.navigateByUrl('/users');
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

  openDeactivateConfirm(): void {
    this.showDeactivateModal.set(true);
  }

  closeDeactivateConfirm(): void {
    this.showDeactivateModal.set(false);
  }

  confirmDeactivate(): void {
    const id = this.userId();
    const fullName = [this.firstName(), this.lastName()].filter(Boolean).join(' ') || this.code();
    this.isDeactivating.set(true);
    this.userService.deactivateEmployee(
      id,
      () => {
        this.isDeactivating.set(false);
        this.showDeactivateModal.set(false);
        this.status.set('Inactive');
        this.notification.show(`User "${fullName}" has been deactivated successfully.`, 'success');
        void this.router.navigateByUrl('/users');
      },
      (errMsg) => {
        this.isDeactivating.set(false);
        this.notification.show(errMsg, 'error');
      }
    );
  }
}
