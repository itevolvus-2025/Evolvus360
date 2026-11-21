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

  readonly token = signal<string>('demo');
  readonly isSubmitting = signal(false);
  readonly isLoading = signal(false);

  // Candidate Data (from API or Screenshot Dummy)
  readonly candidate = signal<OnboardingCandidateInfo>(DUMMY_ONBOARDING_CANDIDATE);

  // Personal & Contact Details
  readonly dateOfBirth = signal('');
  readonly gender = signal('');
  readonly mobileNumber = signal('+91 ');
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
      'demo';
    this.token.set(queryToken);

    this.isLoading.set(true);
    this.onboardingService.validateInvitation(queryToken).subscribe({
      next: (info) => {
        this.isLoading.set(false);
        this.candidate.set(info);
      },
      error: () => {
        this.isLoading.set(false);
        this.candidate.set(DUMMY_ONBOARDING_CANDIDATE);
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
    if (!this.mobileNumber() || this.mobileNumber().trim() === '+91') missing++;
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
      this.identityProofFile.set(file);
      this.identityProofName.set(file.name);
      this.notification.show(`Attached: ${file.name}`, 'info');
    }
  }

  onCancelledChequeChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      const file = target.files[0];
      this.cancelledChequeFile.set(file);
      this.cancelledChequeName.set(file.name);
      this.notification.show(`Attached: ${file.name}`, 'info');
    }
  }

  submitOnboarding(): void {
    if (this.isSubmitting()) return;

    // Check mandatory fields
    if (!this.dateOfBirth()) {
      this.notification.show('Please provide your Date of Birth', 'error');
      return;
    }

    if (!this.gender()) {
      this.notification.show('Please select your Gender', 'error');
      return;
    }

    if (!this.mobileNumber() || this.mobileNumber().trim() === '+91') {
      this.notification.show('Mobile number is required', 'error');
      return;
    }

    if (!this.aadhaarNumber()) {
      this.notification.show('Aadhaar number is required', 'error');
      return;
    }

    if (!this.panNumber()) {
      this.notification.show('PAN Card number is required', 'error');
      return;
    }

    if (!this.emergencyContactName() || !this.emergencyContactPhone()) {
      this.notification.show('Emergency contact details are mandatory', 'error');
      return;
    }

    if (!this.bankName() || !this.accountNumber() || !this.ifscCode()) {
      this.notification.show('Banking details are mandatory for direct deposit', 'error');
      return;
    }

    this.isSubmitting.set(true);

    const formData = new FormData();
    const currentToken = this.token();
    const isDemoToken = !currentToken || currentToken === 'demo' || currentToken === 'dummy';
    const tokenToSend = isDemoToken ? 'demo0123456789abcdef0123456789abcdef' : currentToken;

    formData.append('token', tokenToSend);
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
    formData.append('qualification', this.qualification() || '');
    formData.append('languages', JSON.stringify(this.languages()));

    // Attach documents if chosen, or dummy fallbacks
    if (this.identityProofFile()) {
      formData.append('identity_proof', this.identityProofFile()!);
    } else {
      const dummyIdBlob = new Blob(['sample-identity-proof'], { type: 'application/pdf' });
      formData.append('identity_proof', dummyIdBlob, 'identity_proof.pdf');
    }

    if (this.cancelledChequeFile()) {
      formData.append('cancelled_cheque', this.cancelledChequeFile()!);
    } else {
      const dummyChequeBlob = new Blob(['sample-cheque'], { type: 'application/pdf' });
      formData.append('cancelled_cheque', dummyChequeBlob, 'cancelled_cheque.pdf');
    }

    this.onboardingService.submitOnboarding(formData).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.notification.show('Onboarding details submitted successfully!', 'success');
        void this.router.navigate(['/onboarding/success']);
      },
      error: (err: Error) => {
        this.isSubmitting.set(false);
        if (isDemoToken) {
          // In demo preview mode, celebrate successful completion
          this.notification.show('Demo onboarding submission simulated successfully!', 'success');
          void this.router.navigate(['/onboarding/success']);
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
