import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';
import { API_ENDPOINTS } from '../../../../core/constants/api-endpoints';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';

/** Standard comprehensive email validation pattern */
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, IconComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Centralized API Endpoint for login */
  readonly loginApiUrl = API_ENDPOINTS.auth.login;

  /** Form submission & UI state signals */
  readonly isLoading = signal(false);
  readonly error = signal('');
  readonly passwordVisible = signal(false);

  togglePasswordVisibility(): void {
    this.passwordVisible.update((visible) => !visible);
  }

  /** Reactive login form with strict email validation pattern */
  readonly form = this.fb.nonNullable.group({
    email: [
      '',
      [
        Validators.required,
        Validators.pattern(EMAIL_REGEX),
      ],
    ],
    password: ['', [Validators.required, Validators.minLength(6)]],
    rememberMe: [true],
  });

  get emailControl() {
    return this.form.controls.email;
  }

  get passwordControl() {
    return this.form.controls.password;
  }

  /**
   * Submit login credentials to backend API (/api/v1/auth/login)
   */
  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.error.set('');

    const raw = this.form.getRawValue();
    const email = raw.email.trim();
    const password = raw.password;
    const rememberMe = raw.rememberMe;

    this.auth.login(email, password, rememberMe).subscribe({
      next: (result) => {
        this.isLoading.set(false);
        if (result.success) {
          const targetRoute = this.auth.getDefaultRoute();
          void this.router.navigateByUrl(targetRoute);
        } else {
          this.error.set(
            result.message || 'Invalid email or password. Please verify your credentials.'
          );
        }
      },
      error: (err: Error) => {
        this.isLoading.set(false);
        this.error.set(err.message || 'Authentication failed. Please verify your credentials.');
      },
    });
  }
}
