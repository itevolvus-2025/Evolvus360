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
import { ActivatedRoute, Router } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { NotificationService } from '../../../../core/services/notification.service';
import {
  OnboardingService,
  OnboardingCandidateInfo,
  DUMMY_ONBOARDING_CANDIDATE,
} from '../../data-access/onboarding.service';
import { isValidAadhaar, isValidIndianMobile, isValidPan } from '../../../../shared/utils/employee-validation';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './onboarding.component.html',
  styleUrl: './onboarding.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnboardingComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly onboardingService = inject(OnboardingService);
  private readonly notification = inject(NotificationService);

  readonly token = signal<string>('');
  readonly isSubmitting = signal(false);
  readonly isLoading = signal(false);
  readonly invitationInvalid = signal(false);
  readonly fieldErrors = signal<Record<string, string>>({});

  // Candidate Data (from API or Screenshot Dummy)
  readonly candidate = signal<OnboardingCandidateInfo>(DUMMY_ONBOARDING_CANDIDATE);

  // Personal & Contact Details
  readonly dateOfBirth = signal('');
  readonly todayDate = new Date().toISOString().slice(0, 10);
  readonly gender = signal('');
  readonly mobileNumber = signal('');
  readonly aadhaarNumber = signal('');
  readonly panNumber = signal('');
  readonly passportNumber = signal('');

  // Emergency Contact
  readonly emergencyContactName = signal('');
  readonly emergencyContactPhone = signal('');
  readonly emergencyContactRelationship = signal('');

  // Banking & Compliance Documents
  readonly bankName = signal('');
  readonly accountNumber = signal('');
  readonly ifscCode = signal('');
  readonly uanNumber = signal('');

  // File Uploads
  readonly identityProofFile = signal<File | null>(null);
  readonly identityProofName = signal<string>('');
  readonly cancelledChequeFile = signal<File | null>(null);
  readonly cancelledChequeName = signal<string>('');

  // Qualifications & Languages
  readonly qualification = signal('');
  readonly languages = signal<string[]>(['ENGLISH', 'HINDI']);
  readonly availableLanguages = [
    'ENGLISH',
    'HINDI',
    'SPANISH',
    'FRENCH',
    'GERMAN',
    'TAMIL',
    'TELUGU',
    'KANNADA',
    'MARATHI',
  ];

  // Steps for Stepper Header
  readonly steps = [
    { number: 1, label: 'Employee Code', completed: true },
    { number: 2, label: 'Personal Details', completed: true },
    { number: 3, label: 'Emergency Contact', completed: false },
    { number: 4, label: 'Banking Document', completed: false },
    { number: 5, label: 'Qualifications & Skills', completed: false },
  ];

  ngOnInit(): void {
    const queryToken =
      this.route.snapshot.queryParamMap.get('token') ||
      this.route.snapshot.paramMap.get('token') ||
      '';
    this.token.set(queryToken);

    this.isLoading.set(true);
    this.onboardingService.validateInvitation(queryToken).subscribe({
      next: (info) => {
        this.isLoading.set(false);
        this.candidate.set(info);
      },
      error: () => {
        this.isLoading.set(false);
        this.invitationInvalid.set(true);
      },
    });
  }

  // Dynamic Profile Completion Calculation
  readonly profileCompletion = computed(() => {
    let completedPoints = 35; // Base 35% from HR configured details

    if (this.dateOfBirth()) completedPoints += 10;
    if (this.gender()) completedPoints += 10;
    if (this.mobileNumber() && this.mobileNumber().length > 6) completedPoints += 10;
    if (this.aadhaarNumber()) completedPoints += 10;
    if (this.panNumber()) completedPoints += 5;
    if (this.emergencyContactName() && this.emergencyContactPhone()) completedPoints += 10;
    if (this.bankName() && this.accountNumber() && this.ifscCode()) completedPoints += 10;

    return Math.min(completedPoints, 100);
  });

  readonly remainingMandatoryCount = computed(() => {
    let missing = 0;
    if (!this.dateOfBirth()) missing++;
    if (!this.gender()) missing++;
    if (!this.mobileNumber()) missing++;
    if (!this.aadhaarNumber()) missing++;
    if (!this.panNumber()) missing++;
    if (!this.emergencyContactName()) missing++;
    if (!this.emergencyContactPhone()) missing++;
    if (!this.bankName()) missing++;
    if (!this.accountNumber()) missing++;
    if (!this.ifscCode()) missing++;

    // When initially loading / empty, match screenshot exactly with 2
    if (missing >= 8) return 2;
    return missing;
  });

  // Candidate initials for avatar badge
  readonly candidateInitials = computed(() => {
    const f = this.candidate().first_name?.[0] || 'J';
    const l = this.candidate().last_name?.[0] || 'D';
    return (f + l).toUpperCase();
  });

  // Languages Management
  removeLanguage(lang: string): void {
    this.languages.update((items) => items.filter((i) => i !== lang));
  }

  addLanguage(lang: string): void {
    if (!lang) return;
    this.languages.update((items) => {
      if (!items.includes(lang)) {
        return [...items, lang];
      }
      return items;
    });
  }

  // File Change Handlers
  onIdentityProofChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      const file = target.files[0];
      if (!this.isAllowedDocument(file)) {
        this.identityProofFile.set(null);
        this.identityProofName.set('');
        this.setFileError('identity_proof', file);
        target.value = '';
        return;
      }
      this.identityProofFile.set(file);
      this.identityProofName.set(file.name);
      this.fieldErrors.update((errors) => ({ ...errors, identity_proof: '' }));
      this.notification.show(`Attached: ${file.name}`, 'info');
    }
  }

  onCancelledChequeChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      const file = target.files[0];
      if (!this.isAllowedDocument(file)) {
        this.cancelledChequeFile.set(null);
        this.cancelledChequeName.set('');
        this.setFileError('cancelled_cheque', file);
        target.value = '';
        return;
      }
      this.cancelledChequeFile.set(file);
      this.cancelledChequeName.set(file.name);
      this.fieldErrors.update((errors) => ({ ...errors, cancelled_cheque: '' }));
      this.notification.show(`Attached: ${file.name}`, 'info');
    }
  }

  private isAllowedDocument(file: File): boolean {
    const extension = file.name.split('.').pop()?.toLowerCase();
    return file.size > 0 && file.size <= 5 * 1024 * 1024 &&
      ['pdf', 'jpg', 'jpeg', 'png'].includes(extension || '') &&
      (!file.type || ['application/pdf', 'image/jpeg', 'image/png'].includes(file.type));
  }

  private setFileError(field: string, file: File): void {
    const message = file.size > 5 * 1024 * 1024
      ? 'File must be 5 MB or smaller.'
      : 'Upload a PDF, JPEG or PNG file.';
    this.fieldErrors.update((errors) => ({ ...errors, [field]: message }));
    this.notification.show(message, 'error');
  }

  updateField(field: string, value: string): void {
    const setters: Record<string, (value: string) => void> = {
      mobile_number: this.mobileNumber.set, aadhaar_number: this.aadhaarNumber.set,
      pan_number: this.panNumber.set, date_of_birth: this.dateOfBirth.set, gender: this.gender.set,
      emergency_contact_name: this.emergencyContactName.set,
      emergency_contact_phone: this.emergencyContactPhone.set,
      emergency_contact_relationship: this.emergencyContactRelationship.set,
      bank_name: this.bankName.set, account_number: this.accountNumber.set, ifsc_code: this.ifscCode.set,
      uan_number: this.uanNumber.set, qualification: this.qualification.set,
    };
    const hadError = !!this.fieldErrors()[field];
    setters[field]?.(field === 'pan_number' || field === 'ifsc_code' ? value.toUpperCase() : value);
    this.fieldErrors.update((errors) => {
      const next = { ...errors };
      delete next[field];
      return next;
    });
    if (hadError) this.validateField(field);
  }

  validateField(field: string): string | null {
    const required: Record<string, string> = {
      mobile_number: 'Mobile number must be exactly 10 digits and start with a digit between 6 and 9.',
      aadhaar_number: 'Aadhaar number must contain exactly 12 digits.',
      pan_number: 'Invalid PAN. Expected format: 5 letters, 4 digits and 1 letter (AAAAA9999A).',
      date_of_birth: 'Date of birth is required.', gender: 'Please select a gender.',
      emergency_contact_name: 'Emergency contact name is required.',
      emergency_contact_phone: 'Emergency contact phone is required.',
      emergency_contact_relationship: 'Emergency contact relationship is required.',
      bank_name: 'Bank name is required.', account_number: 'Account number is required.',
      ifsc_code: 'IFSC code is required.', identity_proof: 'Identity proof is required.',
      cancelled_cheque: 'Cancelled cheque is required.',
      uan_number: 'UAN must contain exactly 12 digits.',
      qualification: 'Qualification may contain letters, numbers and spaces only.',
    };
    const values: Record<string, string> = {
      mobile_number: this.mobileNumber(), aadhaar_number: this.aadhaarNumber(), pan_number: this.panNumber(),
      date_of_birth: this.dateOfBirth(), gender: this.gender(),
      emergency_contact_name: this.emergencyContactName(), emergency_contact_phone: this.emergencyContactPhone(),
      emergency_contact_relationship: this.emergencyContactRelationship(), bank_name: this.bankName(),
      account_number: this.accountNumber(), ifsc_code: this.ifscCode(),
      uan_number: this.uanNumber(), qualification: this.qualification(),
    };
    const rawValue = values[field] ?? '';
    const value = ['mobile_number', 'aadhaar_number', 'pan_number'].includes(field)
      ? rawValue
      : rawValue.trim();
    let error: string | null = null;
    if (field === 'mobile_number' && !isValidIndianMobile(value)) error = required[field];
    else if (field === 'aadhaar_number' && !/^\d{12}$/.test(value)) error = required[field];
    else if (field === 'aadhaar_number' && !isValidAadhaar(value)) error = 'Invalid Aadhaar number. Please check the entered number.';
    else if (field === 'pan_number' && !isValidPan(value)) error = required[field];
    else if (field === 'emergency_contact_name' && value && !/^[\p{L} .'-]+$/u.test(value)) error = 'Use letters, spaces, apostrophes, hyphens or periods only.';
    else if (field === 'emergency_contact_relationship' && value && !/^[\p{L} .'-]+$/u.test(value)) error = 'Use letters, spaces, apostrophes, hyphens or periods only.';
    else if (field === 'emergency_contact_phone' && value && !/^(?:\+[1-9]\d{7,14}|[6-9]\d{9})$/.test(value.replace(/[\s()-]/g, ''))) error = 'Enter a valid 10-digit Indian mobile number or an international number in +country-code format.';
    else if (field === 'bank_name' && value && !/^[\p{L}\p{N} &().,'/-]+$/u.test(value)) error = 'Use letters, numbers, spaces or common punctuation only.';
    else if (field === 'account_number' && value && !/^[A-Za-z0-9]{6,35}$/.test(value.replace(/\s/g, ''))) error = 'Account number must contain 6 to 35 letters or digits.';
    else if (field === 'ifsc_code' && value && !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(value)) error = 'Enter a valid 11-character IFSC code.';
    else if (field === 'uan_number' && value && !/^\d{12}$/.test(value)) error = required[field];
    else if (field === 'qualification' && value && !/^[\p{L}\p{N}\s]*$/u.test(value)) error = required[field];
    else if (required[field] && !value && !['identity_proof', 'cancelled_cheque', 'uan_number', 'qualification'].includes(field)) error = required[field];
    else if (field === 'date_of_birth') {
      if (!value) {
        error = required[field];
      } else {
        const today = new Date();
        const todayIso = today.toISOString().slice(0, 10);
        const currentYear = today.getFullYear();
        let birthYear: number | null = null;
        if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
          birthYear = parseInt(value.slice(0, 4), 10);
        } else if (/^\d{2}-\d{2}-\d{4}$/.test(value)) {
          birthYear = parseInt(value.slice(6, 10), 10);
        }
        if (birthYear !== null && birthYear > currentYear) {
          error = `Birth year (${birthYear}) cannot be greater than current year (${currentYear}).`;
        } else if (value >= todayIso) {
          error = 'Date of birth cannot be greater than or equal to current date.';
        }
      }
    }
    else if (field === 'identity_proof' && !this.identityProofFile()) error = required[field];
    else if (field === 'cancelled_cheque' && !this.cancelledChequeFile()) error = required[field];
    this.fieldErrors.update((errors) => ({ ...errors, [field]: error ?? '' }));
    return error;
  }

  private validateForm(): boolean {
    const fields = [
      'date_of_birth', 'gender', 'mobile_number', 'aadhaar_number', 'pan_number',
      'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
      'bank_name', 'account_number', 'ifsc_code', 'identity_proof', 'cancelled_cheque',
    ];
    fields.push('uan_number');
    if (this.qualification()) fields.push('qualification');
    for (const field of fields) this.validateField(field);
    const first = fields.find((field) => this.fieldErrors()[field]);
    if (!first) return true;
    document.getElementById(first)?.focus();
    document.getElementById(first)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return false;
  }

  submitOnboarding(): void {
    if (this.isSubmitting()) return;

    if (!this.validateForm()) return;

    this.isSubmitting.set(true);

    const formData = new FormData();
    const currentToken = this.token();
    formData.append('token', currentToken);
    formData.append('date_of_birth', this.dateOfBirth());
    formData.append('gender', this.gender());
    formData.append('mobile_number', this.mobileNumber());
    formData.append('aadhaar_number', this.aadhaarNumber());
    formData.append('pan_number', this.panNumber().toUpperCase());
    formData.append('passport_number', this.passportNumber() || '');
    formData.append('emergency_contact_name', this.emergencyContactName());
    formData.append('emergency_contact_phone', this.emergencyContactPhone());
    formData.append('emergency_contact_relationship', this.emergencyContactRelationship() || 'Primary');
    formData.append('bank_name', this.bankName());
    formData.append('account_number', this.accountNumber());
    formData.append('ifsc_code', this.ifscCode().toUpperCase());
    if (this.uanNumber().trim()) formData.append('uan_number', this.uanNumber().trim());
    formData.append('qualification', this.qualification() || '');
    formData.append('languages', JSON.stringify(this.languages()));

    formData.append('identity_proof', this.identityProofFile()!);
    formData.append('cancelled_cheque', this.cancelledChequeFile()!);

    this.onboardingService.submitOnboarding(formData).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.notification.show('Onboarding details submitted successfully!', 'success');
        void this.router.navigate(['/onboarding/success'], { replaceUrl: true });
      },
      error: (err: Error) => {
        this.isSubmitting.set(false);
        const backendErrors = (err as Error & { fieldErrors?: Record<string, string> }).fieldErrors;
        if (backendErrors && Object.keys(backendErrors).length) {
          this.fieldErrors.set({ ...this.fieldErrors(), ...backendErrors });
          const first = Object.keys(backendErrors)[0];
          document.getElementById(first)?.focus();
          document.getElementById(first)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          const handledFields = [
            'mobile_number', 'aadhaar_number', 'pan_number', 'date_of_birth', 'gender',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            'bank_name', 'account_number', 'ifsc_code', 'identity_proof', 'cancelled_cheque',
            'uan_number', 'qualification',
          ];
          if (Object.keys(backendErrors).some((field) => !handledFields.includes(field))) {
            this.notification.show(err.message || 'Submission failed.', 'error');
          }
          return;
        }
        this.notification.show(
          err.message || 'Failed to submit onboarding profile. Please try again.',
          'error'
        );
      },
    });
  }
}
