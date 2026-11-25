import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { DropdownComponent, DropdownOption } from '../../../../shared/ui/dropdown';
import { NotificationService } from '../../../../core/services/notification.service';
import { UserService, UserRow, UserStatus, ProfileStatus } from '../../data-access/user.service';
import { MasterDataOption } from '../../../../core/models/api.models';

@Component({
  selector: 'app-user-edit',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent, DropdownComponent],
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

  // Dropdown Options
  readonly departmentOptions = computed<DropdownOption[]>(() =>
    this.departments().map((d) => ({ label: d.name, value: d.id }))
  );
  readonly roleOptions = computed<DropdownOption[]>(() =>
    this.roles().map((r) => ({ label: r.name, value: r.id }))
  );
  readonly entityOptions = computed<DropdownOption[]>(() =>
    this.entities().map((e) => ({ label: e.name, value: e.id }))
  );
  readonly pfOptions: DropdownOption[] = [
    { label: 'Yes', value: 'Yes' },
    { label: 'No', value: 'No' },
  ];
  readonly statusOptions: DropdownOption[] = [
    { label: 'Active', value: 'Active' },
    { label: 'Inactive', value: 'Inactive' },
  ];
  readonly genderOptions: DropdownOption[] = [
    { label: 'Male', value: 'MALE' },
    { label: 'Female', value: 'FEMALE' },
    { label: 'Other', value: 'OTHER' },
    { label: 'Prefer not to say', value: 'PREFER_NOT_TO_SAY' },
  ];

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

  /** Profile is in read-only mode when account is Inactive/Deactive */
  readonly isReadOnly = computed(() => this.status() === 'Inactive');

  /** Whether deactivation is disabled: when user is deactive, inactive, pending, or profile is pending or submitted */
  readonly isDeactivateDisabled = computed(() => {
    return (
      this.status() === 'Inactive' ||
      this.profile() === 'Pending' ||
      this.profile() === 'Submitted'
    );
  });

  readonly deactivateTooltip = computed(() => {
    if (this.status() === 'Inactive') {
      return 'User account is already deactivated';
    }
    if (this.profile() === 'Submitted') {
      return 'Cannot deactivate user while onboarding profile is submitted for approval';
    }
    if (this.profile() === 'Pending') {
      return 'Cannot deactivate user with pending status';
    }
    return 'Deactivate user account and revoke access';
  });

  // 04 Employment Timeline
  readonly joiningDate = signal('');
  readonly startDate = signal('');
  readonly endDate = signal('');

  // 05 Profile & Employee Details
  readonly employeeDetails = signal<any>(null);
  readonly todayDate = new Date().toISOString().slice(0, 10);
  readonly sensitiveUpdates = signal<Record<string, string>>({});
  readonly contactFieldErrors = signal<Record<string, string>>({});
  readonly showAadhaar = signal(true);
  readonly showPan = signal(true);
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

      this.userService.getEmployee(
        id,
        (existing) => {
          this.populateFields(existing);
        },
        (message) => {
          this.notification.show(message, 'error');
        }
      );
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

  resolveDepartmentId(val?: string): string {
    if (!val) return '';
    const match = this.departments().find((d) => d.id === val || d.name.toLowerCase() === val.toLowerCase());
    return match ? match.id : val;
  }

  resolveRoleId(val?: string): string {
    if (!val) return '';
    const match = this.roles().find((r) => r.id === val || r.name.toLowerCase() === val.toLowerCase());
    return match ? match.id : val;
  }

  resolveEntityId(val?: string): string {
    if (!val) return '';
    const match = this.entities().find((e) => e.id === val || e.name.toLowerCase() === val.toLowerCase());
    return match ? match.id : val;
  }

  formatToIso(val: string): string {
    if (!val) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(val)) return val;
    const match = /^(\d{2})-(\d{2})-(\d{4})$/.exec(val);
    return match ? `${match[3]}-${match[2]}-${match[1]}` : val;
  }

  openDatePicker(input: HTMLInputElement): void {
    if (this.isReadOnly()) return;
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

  updateEmployeeDetail(field: string, value: any): void {
    if (field === 'mobile_number') {
      value = this.normalizeMobileInput(String(value ?? '')).slice(0, 10);
      this.contactFieldErrors.update((errors) => ({ ...errors, mobile_number: '' }));
    }
    const current = this.employeeDetails() || {};
    this.employeeDetails.set({ ...current, [field]: value });
  }

  private normalizeMobileInput(value: string): string {
    return value.trim().replace(/^\+\s*91[\s()-]*/, '').replace(/\D/g, '');
  }

  mobileInputValue(): string {
    return this.normalizeMobileInput(String(this.employeeDetails()?.mobile_number ?? '')).slice(0, 10);
  }

  emergencyMobileInputValue(): string {
    return this.normalizeMobileInput(String(this.employeeDetails()?.emergency_contact?.phone ?? '')).slice(0, 10);
  }

  updateNestedEmployeeDetail(group: 'emergency_contact' | 'bank_details', field: string, value: string): void {
    if (group === 'emergency_contact' && field === 'phone') {
      value = this.normalizeMobileInput(value).slice(0, 10);
      this.contactFieldErrors.update((errors) => ({ ...errors, emergency_contact_phone: '' }));
    }
    const current = this.employeeDetails() || {};
    this.employeeDetails.set({
      ...current,
      [group]: { ...(current[group] || {}), [field]: value },
    });
  }

  updateSensitiveDetail(field: string, value: string): void {
    if (field === 'uan_number') {
      value = value.replace(/\D/g, '').slice(0, 12);
      this.contactFieldErrors.update((errors) => ({ ...errors, uan_number: '' }));
    }
    this.sensitiveUpdates.update((current) => ({ ...current, [field]: value }));
  }

  validateContactField(field: 'mobile_number' | 'emergency_contact_phone' | 'uan_number'): void {
    const employeeDetails = this.employeeDetails();
    const sensitiveValues = this.sensitiveUpdates();
    let error = '';
    if (field === 'mobile_number' && employeeDetails && Object.prototype.hasOwnProperty.call(employeeDetails, field)) {
      const mobile = this.normalizeMobileInput(String(employeeDetails.mobile_number ?? ''));
      if (!/^[6-9]\d{9}$/.test(mobile)) error = 'Mobile number must be exactly 10 digits.';
    }
    if (field === 'emergency_contact_phone' && employeeDetails?.emergency_contact && Object.prototype.hasOwnProperty.call(employeeDetails.emergency_contact, 'phone')) {
      const mobile = this.normalizeMobileInput(String(employeeDetails.emergency_contact.phone ?? ''));
      if (!/^[6-9]\d{9}$/.test(mobile)) error = 'Mobile number must be exactly 10 digits.';
    }
    if (field === 'uan_number' && Object.prototype.hasOwnProperty.call(sensitiveValues, field)) {
      if (!/^[0-9]{12}$/.test(sensitiveValues[field])) error = 'UAN must be exactly 12 digits.';
    }
    this.contactFieldErrors.update((errors) => ({ ...errors, [field]: error }));
  }

  updateLanguages(value: string): void {
    const langs = value
      .split(',')
      .map((language) => language.trim())
      .filter(Boolean);
    this.updateEmployeeDetail('languages', langs);
  }

  selectDocument(type: 'identity_proof' | 'cancelled_cheque', event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0] ?? null;
    this.selectedDocuments.update((current) => ({ ...current, [type]: file }));
  }

  getDocument(type: 'identity_proof' | 'cancelled_cheque'): any {
    const docs = this.employeeDetails()?.documents;
    if (!Array.isArray(docs)) return null;
    return docs.find((d: any) => d.document_type === type) || null;
  }

  viewDocument(document: any): void {
    if (!document?.id) return;
    this.userService.viewEmployeeDocument(this.userId(), document.id, (message) => {
      this.notification.show(message, 'error');
    });
  }

  formatFileSize(bytes?: number): string {
    if (!bytes || bytes <= 0) return '';
    if (bytes < 1024 * 1024) {
      return (bytes / 1024).toFixed(1) + ' KB';
    }
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  saveUser(): void {
    if (this.isReadOnly()) {
      this.notification.show('Cannot save changes because the user account is inactive.', 'error');
      return;
    }
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

    const employeeDetails = this.employeeDetails();
    const mobileValue = this.normalizeMobileInput(String(employeeDetails?.mobile_number ?? ''));
    const emergencyMobile = this.normalizeMobileInput(String(employeeDetails?.emergency_contact?.phone ?? ''));
    const sensitiveValues = this.sensitiveUpdates();
    const uanWasEdited = Object.prototype.hasOwnProperty.call(sensitiveValues, 'uan_number');
    const uanValue = sensitiveValues['uan_number'] ?? '';
    const errors: Record<string, string> = {};
    if (employeeDetails && Object.prototype.hasOwnProperty.call(employeeDetails, 'mobile_number') && !/^[6-9]\d{9}$/.test(mobileValue)) {
      errors['mobile_number'] = 'Mobile number must be exactly 10 digits.';
    }
    if (employeeDetails?.emergency_contact && Object.prototype.hasOwnProperty.call(employeeDetails.emergency_contact, 'phone') && !/^[6-9]\d{9}$/.test(emergencyMobile)) {
      errors['emergency_contact_phone'] = 'Mobile number must be exactly 10 digits.';
    }
    if (uanWasEdited && !/^[0-9]{12}$/.test(uanValue)) {
      errors['uan_number'] = 'UAN must be exactly 12 digits.';
    }
    this.contactFieldErrors.set(errors);
    if (Object.keys(errors).length) {
      this.notification.show(Object.values(errors)[0], 'error');
      return;
    }
    if (employeeDetails && employeeDetails.date_of_birth) {
      const dob = this.formatToIso(employeeDetails.date_of_birth);
      if (dob && dob >= this.todayDate) {
        this.notification.show('Date of birth must be before today', 'error');
        return;
      }
    }

    const parseDate = (value: string): string => {
      if (!value) return '';
      if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
      const match = value.match(/^(\d{2})-(\d{2})-(\d{4})$/);
      return match ? `${match[3]}-${match[2]}-${match[1]}` : value;
    };

    const id = this.userId();
    const fullName = [firstName, lastName].filter(Boolean).join(' ');

    const isBackendUuid = typeof id === 'string' && id.includes('-') && id.length >= 32;

    if (isBackendUuid) {
      const deptOption = this.departments().find((d) => d.id === department || d.name === department);
      const roleOption = this.roles().find((r) => r.id === role || r.name === role);
      const entityOption = this.entities().find((e) => e.id === this.entity() || e.name === this.entity());

      const payload: Record<string, unknown> = {
        first_name: firstName,
        middle_name: this.middleName().trim() || null,
        last_name: lastName,
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
        account_status: this.status() === 'Active' ? 'ACTIVE' : 'INACTIVE',
      };

      if (this.reasonForChange().trim()) {
        payload['reason_for_change'] = this.reasonForChange().trim();
      }

      if (employeeDetails) {
        if (employeeDetails.date_of_birth) {
          payload['date_of_birth'] = parseDate(employeeDetails.date_of_birth);
        }
        if (employeeDetails.gender) {
          payload['gender'] = employeeDetails.gender.toUpperCase();
        }
        if (employeeDetails.mobile_number) {
          payload['mobile_number'] = mobileValue;
        }
        if (employeeDetails.emergency_contact) {
          if (employeeDetails.emergency_contact.name) {
            payload['emergency_contact_name'] = employeeDetails.emergency_contact.name;
          }
          if (employeeDetails.emergency_contact.phone) {
            payload['emergency_contact_phone'] = emergencyMobile;
          }
          if (employeeDetails.emergency_contact.relationship) {
            payload['emergency_contact_relationship'] = employeeDetails.emergency_contact.relationship;
          }
        }
        if (employeeDetails.bank_details) {
          if (employeeDetails.bank_details.bank_name) {
            payload['bank_name'] = employeeDetails.bank_details.bank_name;
          }
          if (employeeDetails.bank_details.ifsc_code) {
            payload['ifsc_code'] = employeeDetails.bank_details.ifsc_code;
          }
          if (employeeDetails.bank_details.account_holder_name) {
            payload['account_holder_name'] = employeeDetails.bank_details.account_holder_name;
          }
        }
        if (employeeDetails.qualification !== undefined) {
          payload['qualification'] = employeeDetails.qualification || null;
        }
        if (Array.isArray(employeeDetails.languages)) {
          payload['languages'] = employeeDetails.languages;
        }

        // Only send sensitive fields if the user entered a new unmasked value
        const sens = this.sensitiveUpdates();
        if (sens['aadhaar_number'] && !sens['aadhaar_number'].includes('*')) {
          payload['aadhaar_number'] = sens['aadhaar_number'].trim();
        }
        if (sens['pan_number'] && !sens['pan_number'].includes('*')) {
          payload['pan_number'] = sens['pan_number'].trim().toUpperCase();
        }
        if (sens['passport_number'] && !sens['passport_number'].includes('*')) {
          payload['passport_number'] = sens['passport_number'].trim().toUpperCase();
        }
        if (Object.prototype.hasOwnProperty.call(sens, 'uan_number') && !sens['uan_number'].includes('*')) {
          payload['uan_number'] = sens['uan_number'].trim();
        }
        if (sens['account_number'] && !sens['account_number'].includes('*')) {
          payload['account_number'] = sens['account_number'].trim();
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
    if (this.isDeactivateDisabled()) {
      return;
    }
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
