import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly email = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.email]
  });

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');
  readonly resetUrl = signal('');

  readonly resetQueryParams = computed(() => {
    const url = this.resetUrl();
    const emailVal = this.email.value.trim();
    if (!url) return { token: '1234', email: emailVal };
    try {
      const parsed = new URL(url);
      const token = parsed.searchParams.get('token') || '1234';
      const email = parsed.searchParams.get('email') || emailVal;
      return { token, email };
    } catch {
      return { token: '1234', email: emailVal };
    }
  });

  send(): void {
    if (this.email.invalid) {
      this.email.markAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');
    this.resetUrl.set('');

    const emailValue = this.email.value.trim();

    this.auth.forgotPassword(emailValue).subscribe({
      next: (result) => {
        this.isLoading.set(false);
        if (result.success) {
          this.successMessage.set(
            result.message || 'Password reset instructions have been sent to your email.'
          );
          if (result.data?.reset_link) {
            this.resetUrl.set(result.data.reset_link);
          }
        } else {
          this.errorMessage.set(
            result.message || 'Could not send recovery link. Please verify your email address.'
          );
        }
      },
      error: (err: Error) => {
        this.isLoading.set(false);
        this.errorMessage.set(err.message || 'An unexpected error occurred. Please try again.');
      }
    });
  }
}
