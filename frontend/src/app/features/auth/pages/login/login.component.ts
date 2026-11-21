import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';
import { API_ENDPOINTS } from '../../../../core/constants/api-endpoints';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';

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
  readonly loginApiUrl = API_ENDPOINTS.auth.login; // http://localhost:8000/api/v1/auth/login

  /** Form submission & UI state signals */
  readonly isLoading = signal(false);
  readonly error = signal('');
  readonly passwordVisible = signal(false);

  togglePasswordVisibility(): void {
    this.passwordVisible.update((visible) => !visible);
  }

  /** Reactive login form with field validation */
  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    rememberMe: [true],
  });

  /**
   * Submit login credentials to backend API (/api/v1/auth/login)
   * with automatic hardcoded session fallback if backend server is offline.
   */
  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.error.set('');

    const { email, password, rememberMe } = this.form.getRawValue();

    console.log(`[Auth] Attempting login via API: ${this.loginApiUrl}`);

    this.auth.login(email, password, rememberMe).subscribe({
      next: (result) => {
        this.isLoading.set(false);
        if (result.success) {
          const targetRoute = this.auth.getDefaultRoute();
          console.log(`[Auth] Login successful. Redirecting to ${targetRoute}...`);
          void this.router.navigateByUrl(targetRoute);
        } else {
          this.error.set(
            result.message || 'Authentication failed. Please check your email and password.'
          );
        }
      },
      error: (err: Error) => {
        this.isLoading.set(false);
        console.warn('[Auth] API request encountered error:', err);
        this.error.set(err.message || 'Authentication failed. Please verify your credentials.');
      },
    });
  }
}
