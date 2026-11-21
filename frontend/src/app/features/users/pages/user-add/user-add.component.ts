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
import { isValidEmail } from '../../../../shared/utils/employee-validation';

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
  readonly fieldErrors = signal<Record<string, string>>({});

  private readonly messages: Record<string, string> = {
    first_name: 'First name must contain only letters and spaces.',
    middle_name: 'Middle name must contain only letters and spaces.',
    last_name: 'Last name must contain only letters and spaces.',
    designation: 'Designation must contain only letters and spaces.',
    location: 'Location must contain only letters and spaces.',
    company_email: 'Please enter a valid company email address.',
    personal_email: 'Please enter a valid personal email address.',
    department_id: 'Please select an active department.',
    role_id: 'Please select an active role.',
    entity_id: 'Please select an active entity.',
    joining_date: 'Invalid joining date. Please provide a valid date in YYYY-MM-DD format.',
    start_date: 'Invalid start date. Please provide a valid date in YYYY-MM-DD format.',
    end_date: 'Invalid end date. Please provide a valid date in YYYY-MM-DD format.',
  };

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
    const field = target === 'department' ? 'department_id' : target === 'role' ? 'role_id' : 'entity_id';
    this.fieldErrors.update((errors) => ({ ...errors, [field]: '' }));
  }

  optionName(options: MasterDataOption[], id: string): string {
    return options.find((option) => option.id === id)?.name || '';
  }

  setField(field: string, value: string): void {
    const setters: Record<string, (value: string) => void> = {
      first_name: this.firstName.set,
      middle_name: this.middleName.set,
      last_name: this.lastName.set,
      designation: this.designation.set,
      location: this.location.set,
      company_email: this.companyEmail.set,
      personal_email: this.personalEmail.set,
      joining_date: this.joiningDate.set,
      start_date: this.startDate.set,
      end_date: this.endDate.set,
    };
    const hadError = !!this.fieldErrors()[field];
    setters[field]?.(value);
    this.fieldErrors.update((errors) => {
      const next = { ...errors };
      delete next[field];
      return next;
    });
    if (hadError) this.validateField(field);
  }

  validateSelection(field: 'department_id' | 'role_id' | 'entity_id'): void {
    const selection = field === 'department_id'
      ? this.department()
      : field === 'role_id'
        ? this.role()
        : this.entity();
    const options = field === 'department_id'
      ? this.departments()
      : field === 'role_id'
        ? this.roles()
        : this.entities();
    const message = this.messages[field];
    this.fieldErrors.update((errors) => ({
      ...errors,
      [field]: options.some((option) => option.id === selection) ? '' : message,
    }));
  }

  validateField(field: string): string | null {
    const rawValues: Record<string, string> = {
      first_name: this.firstName(), middle_name: this.middleName(), last_name: this.lastName(),
      designation: this.designation(), location: this.location(), company_email: this.companyEmail(),
      personal_email: this.personalEmail(), joining_date: this.joiningDate(),
      start_date: this.startDate(), end_date: this.endDate(),
    };
    const value = (rawValues[field] ?? '').trim();
    let error: string | null = null;
    if (['first_name', 'last_name', 'designation', 'location'].includes(field) && !value) {
      error = field === 'first_name' ? 'First name is required.' : `${field.replace('_', ' ')} is required.`;
    } else if (field === 'middle_name' && !value) {
      error = null;
    } else if (['first_name', 'middle_name', 'last_name', 'designation', 'location'].includes(field)
      && value && [...value].some((char) => !(char === ' ' || /\p{L}/u.test(char)))) {
      error = this.messages[field];
    } else if (field === 'personal_email' && !value) {
      error = 'Personal email is required.';
    } else if (['company_email', 'personal_email'].includes(field) && value && !isValidEmail(value)) {
      error = this.messages[field];
    } else if (['joining_date', 'start_date', 'end_date'].includes(field) && value && !this.isValidDate(value)) {
      error = this.messages[field];
    }
    this.fieldErrors.update((errors) => ({ ...errors, [field]: error ?? '' }));
    return error;
  }

  private isValidDate(value: string): boolean {
    const match = /^(\d{2})-(\d{2})-(\d{4})$/.exec(value);
    if (!match) return false;
    const date = new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
    return date.getFullYear() === Number(match[3]) && date.getMonth() === Number(match[2]) - 1 && date.getDate() === Number(match[1]);
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

    const fields = ['first_name', 'middle_name', 'last_name', 'designation', 'location', 'company_email', 'personal_email', 'joining_date', 'start_date', 'end_date'];
    for (const field of fields) this.validateField(field);
    const errors = { ...this.fieldErrors() };
    if (!this.departments().some((item) => item.id === departmentId)) errors['department_id'] = this.messages['department_id'];
    if (!this.roles().some((item) => item.id === roleId)) errors['role_id'] = this.messages['role_id'];
    if (!this.entities().some((item) => item.id === entityId)) errors['entity_id'] = this.messages['entity_id'];
    const joining = joiningDate ? this.toIso(joiningDate) : '';
    const start = startDate ? this.toIso(startDate) : '';
    const end = this.endDate().trim() ? this.toIso(this.endDate().trim()) : '';
    if (joining && start && start < joining) errors['start_date'] = 'Start date must be on or after joining date.';
    if (start && end && end < start) errors['end_date'] = 'End date must be on or after start date.';
    this.fieldErrors.set(errors);
    const firstError = Object.keys(errors).find((key) => errors[key]);
    if (firstError) {
      document.getElementById(firstError)?.focus();
      document.getElementById(firstError)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    const parseDate = (value: string): string => this.toIso(value);

    this.userService.createEmployee({
      first_name: firstName,
      middle_name: this.middleName().trim() || null,
      last_name: lastName,
      department_id: departmentId,
      role_id: roleId,
      designation,
      entity_id: entityId,
      location: this.location().trim(),
      company_email: companyEmail || null,
      personal_email: this.normalizeEmail(personalEmail),
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
    }, (message, backendErrors) => {
      if (backendErrors && Object.keys(backendErrors).length) {
        const knownFields = new Set([
          'first_name', 'middle_name', 'last_name', 'department_id', 'role_id',
          'designation', 'entity_id', 'location', 'company_email', 'personal_email',
          'pf_applicable', 'joining_date', 'start_date', 'end_date',
        ]);
        const mappedErrors = Object.fromEntries(
          Object.entries(backendErrors).filter(([field]) => knownFields.has(field)),
        );
        if (Object.keys(mappedErrors).length) {
          this.fieldErrors.set({ ...this.fieldErrors(), ...mappedErrors });
          const first = Object.keys(mappedErrors)[0];
          document.getElementById(first)?.focus();
          document.getElementById(first)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        if (Object.keys(mappedErrors).length !== Object.keys(backendErrors).length) {
          this.notification.show(message || 'Please correct the highlighted fields.', 'error');
        }
      } else {
        const lowerMessage = message.toLowerCase();
        const field = [
          'company_email', 'personal_email', 'department_id', 'role_id', 'entity_id',
          'first_name', 'middle_name', 'last_name', 'designation', 'location',
          'joining_date', 'start_date', 'end_date',
        ].find((candidate) => lowerMessage.includes(candidate.replace('_id', '').replace('_', ' ')));
        if (field) {
          this.fieldErrors.update((current) => ({ ...current, [field]: message }));
          document.getElementById(field)?.focus();
          document.getElementById(field)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          this.notification.show(message, 'error');
        }
      }
    });
  }

  private toIso(value: string): string {
    const match = /^(\d{2})-(\d{2})-(\d{4})$/.exec(value);
    return match ? `${match[3]}-${match[2]}-${match[1]}` : value;
  }

  private normalizeEmail(value: string): string {
    const [local, domain] = value.trim().split('@');
    return domain ? `${local}@${domain.toLowerCase()}` : value.trim();
  }
}
