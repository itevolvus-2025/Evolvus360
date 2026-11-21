import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
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
  readonly email = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.email]
  });

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');
  send(): void {
    if (this.isLoading()) return;
    if (this.email.invalid) {
      this.email.markAsTouched();
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
          this.successMessage.set('Password reset link has been sent to your email.');
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
