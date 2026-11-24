import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { AlertComponent } from '../../../../shared/ui/alert/alert.component';

/** Standard comprehensive email validation pattern */
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, AlertComponent],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent {
  private readonly auth = inject(AuthService);
  private readonly notification = inject(NotificationService);

  readonly email = new FormControl('', {
    nonNullable: true,
    validators: [
      Validators.required,
      Validators.pattern(EMAIL_REGEX)
    ]
  });

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  send(): void {
    if (this.isLoading()) return;
    if (this.email.invalid) {
      this.email.markAsTouched();
      this.notification.show('Please enter a valid registered email address.', 'warning');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');
    const emailValue = this.email.value.trim();

    this.auth.forgotPassword(emailValue).subscribe({
      next: (result) => {
        this.isLoading.set(false);
        if (result.success) {
          const msg = 'Password reset instructions have been sent to your email.';
          this.successMessage.set(msg);
          this.notification.show(msg, 'success');
        } else {
          const msg = result.message || 'Could not send recovery link. Please verify your email address.';
          this.errorMessage.set(msg);
          this.notification.show(msg, 'error');
        }
      },
      error: (err: Error) => {
        this.isLoading.set(false);
        const msg = err.message || 'An unexpected error occurred. Please try again.';
        this.errorMessage.set(msg);
        this.notification.show(msg, 'error');
      }
    });
  }
}
