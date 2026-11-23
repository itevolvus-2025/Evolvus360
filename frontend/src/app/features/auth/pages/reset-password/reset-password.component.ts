import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, IconComponent],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.scss'
})
export class ResetPasswordComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  readonly token = signal('');
  readonly email = signal('');
  readonly passwordVisible = signal(false);
  readonly confirmPasswordVisible = signal(false);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  readonly form = this.fb.nonNullable.group({
    newPassword: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(128)]],
    confirmPassword: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(128)]],
  });

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => {
      if (params['token']) {
        this.token.set(params['token']);
      }
      if (params['email']) {
        this.email.set(params['email']);
      }
    });
  }

  togglePasswordVisibility(): void {
    this.passwordVisible.update((v) => !v);
  }

  toggleConfirmPasswordVisibility(): void {
    this.confirmPasswordVisible.update((v) => !v);
  }

  // Password Strength Indicators
  hasMinLength(): boolean {
    return (this.form.controls.newPassword.value || '').length >= 8;
  }

  hasUppercase(): boolean {
    return /[A-Z]/.test(this.form.controls.newPassword.value || '');
  }

  hasLowercase(): boolean {
    return /[a-z]/.test(this.form.controls.newPassword.value || '');
  }

  hasNumber(): boolean {
    return /\d/.test(this.form.controls.newPassword.value || '');
  }

  hasSpecial(): boolean {
    return /[^A-Za-z0-9]/.test(this.form.controls.newPassword.value || '');
  }

  passwordsMatch(): boolean {
    const { newPassword, confirmPassword } = this.form.getRawValue();
    return newPassword.length > 0 && newPassword === confirmPassword;
  }

  isFormValid(): boolean {
    return (
      this.hasMinLength() &&
      this.hasUppercase() &&
      this.hasLowercase() &&
      this.hasNumber() &&
      this.hasSpecial() &&
      this.passwordsMatch()
    );
  }

  submit(): void {
    if (!this.token()) {
      this.errorMessage.set('Invalid or missing password reset token. Please request a new link.');
      return;
    }

    if (!this.isFormValid()) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    const { newPassword, confirmPassword } = this.form.getRawValue();

    this.auth
      .resetPassword({
        token: this.token(),
        email: this.email() || undefined,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      .subscribe({
        next: (result) => {
          this.isLoading.set(false);
          if (result.success) {
            this.successMessage.set(
              result.message || 'Password updated successfully! Redirecting to login...'
            );
            setTimeout(() => {
              void this.router.navigateByUrl('/auth/login');
            }, 2500);
          } else {
            this.errorMessage.set(
              result.message || 'Password reset failed. The link may have expired or is invalid.'
            );
          }
        },
        error: (err: Error) => {
          this.isLoading.set(false);
          this.errorMessage.set(err.message || 'An error occurred during password reset.');
        },
      });
  }
}
