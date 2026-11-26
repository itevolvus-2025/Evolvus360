import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, map, of, shareReplay, throwError } from 'rxjs';
import { User, UserRole } from '../models/hrms.models';
import { TokenResponse } from '../models/api.models';
import { ApiService } from './api.service';
import { API_ENDPOINTS } from '../constants/api-endpoints';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly router = inject(Router);
  private readonly apiService = inject(ApiService);

  private readonly sessionKey = 'hrms_session';
  private readonly tokenKey = 'access_token';
  private readonly refreshKey = 'refresh_token';
  private readonly expiryKey = 'token_expiry';
  private readonly sessionStorageKeys = [this.sessionKey, this.tokenKey, this.refreshKey, this.expiryKey];

  private readonly currentUser = signal<User | null>(this.restore());
  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUser() !== null);
  readonly showLogoutModal = signal<boolean>(false);

  /** Active timeout handle for proactive background token refresh */
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;

  /** In-flight token refresh observable mutex to prevent race conditions during rotation */
  private refreshInProgress$: Observable<TokenResponse | null> | null = null;

  constructor() {
    this.clearLegacyLocalSession();
    this.checkAndResumeSession();
  }

  /**
   * Check stored session and schedule token refresh or refresh immediately if near expiry
   */
  private checkAndResumeSession(): void {
    const refreshToken = this.getStoredItem(this.refreshKey);
    const accessToken = this.getStoredItem(this.tokenKey);
    const expiryStr = this.getStoredItem(this.expiryKey);

    if (!refreshToken || refreshToken === 'demo-hardcoded-session-token' || !accessToken) {
      this.clearStoredSession();
      this.currentUser.set(null);
      return;
    }

    const expiryTimestamp = Number(expiryStr);
    const remainingSeconds = Math.floor((expiryTimestamp - Date.now()) / 1000);

    if (Number.isFinite(expiryTimestamp) && remainingSeconds > 60) {
      this.scheduleTokenRefresh(remainingSeconds);
      return;
    }

    // Missing, invalid, or nearly expired access-token metadata must be refreshed.
    this.refreshToken().subscribe({
      error: (err) => console.warn('[AuthService] Startup token refresh error:', err),
    });
  }

  /**
   * Schedule automatic token refresh prior to access token expiry.
   * Refreshes 60 seconds before expiration (or 20% before for short-lived tokens).
   */
  scheduleTokenRefresh(expiresInSeconds: number): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }

    const bufferSeconds =
      expiresInSeconds > 120 ? 60 : Math.max(Math.floor(expiresInSeconds * 0.2), 5);
    const delayMs = Math.max((expiresInSeconds - bufferSeconds) * 1000, 5000);

    console.log(
      `[AuthService] Token expires in ${expiresInSeconds}s. Scheduled refresh in ${Math.round(
        delayMs / 1000
      )}s.`
    );

    this.refreshTimer = setTimeout(() => {
      console.log('[AuthService] Auto-refresh timer triggered. Fetching fresh access token...');
      this.refreshToken().subscribe({
        next: (data) => {
          if (data) {
            console.log('[AuthService] Token successfully refreshed and stored.');
          }
        },
        error: (err) => {
          console.error('[AuthService] Auto-refresh failed:', err);
        },
      });
    }, delayMs);
  }

  /**
   * Exchange the current refresh token for a new access token and rotated refresh token.
   * Endpoint: POST /api/v1/auth/refresh
   */
  refreshToken(): Observable<TokenResponse | null> {
    // If a refresh is already in-flight, return the shared observable
    if (this.refreshInProgress$) {
      return this.refreshInProgress$;
    }

    const refreshToken = this.getStoredItem(this.refreshKey);
    if (!refreshToken || refreshToken === 'demo-hardcoded-session-token') {
      return of(null);
    }

    this.refreshInProgress$ = this.apiService
      .post<TokenResponse>(API_ENDPOINTS.auth.refresh, { refresh_token: refreshToken })
      .pipe(
        map((response) => {
          if (response && response.data) {
            this.handleAuthSuccess(response.data);
            return response.data;
          }
          return null;
        }),
        catchError((err: Error) => {
          console.warn('[AuthService] Refresh token call failed:', err.message);
          // If refresh token is revoked, invalid or expired, log out cleanly
          if (
            err.message.includes('401') ||
            err.message.includes('Invalid refresh token') ||
            err.message.includes('revoked')
          ) {
            this.logout();
          }
          return throwError(() => err);
        }),
        finalize(() => {
          this.refreshInProgress$ = null;
        }),
        shareReplay(1)
      );

    return this.refreshInProgress$;
  }

  /**
   * Process and store successful auth token bundle (from login or refresh).
   */
  private handleAuthSuccess(data: TokenResponse): void {
    if (data.access_token) {
      this.setStoredItem(this.tokenKey, data.access_token);
    }
    if (data.refresh_token) {
      this.setStoredItem(this.refreshKey, data.refresh_token);
    }
    if (data.expires_in) {
      const expiryTimestamp = Date.now() + data.expires_in * 1000;
      this.setStoredItem(this.expiryKey, String(expiryTimestamp));
      this.scheduleTokenRefresh(data.expires_in);
    }

    const authUser = data.user;
    if (authUser) {
      const fullName =
        [authUser.first_name, authUser.last_name]
          .filter(Boolean)
          .join(' ')
          .trim() || authUser.email;

      const primaryRole =
        (authUser.roles?.[0]?.name as UserRole) || 'Super Admin';

      const user: User = {
        id: authUser.id,
        name: fullName,
        email: authUser.email,
        role: primaryRole,
        token: data.access_token,
        permissions: data.permissions || authUser.permissions || [],
      };

      this.persistSession(user);
    }
  }

  /**
   * Authenticate with backend API.
   * Credentials must be validated against the backend database.
   */
  login(
    email: string,
    password: string
  ): Observable<{ success: boolean; message?: string }> {
    if (!email || password.length < 8) {
      return of({
        success: false,
        message: 'Valid email and password (min 8 chars) are required.',
      });
    }

    const trimmedEmail = email.trim().toLowerCase();

    // Authenticate with real Backend API (/api/v1/auth/login)
    return this.apiService
      .post<TokenResponse>(API_ENDPOINTS.auth.login, {
        email: trimmedEmail,
        password,
      })
      .pipe(
        map((response) => {
          if (response && response.data) {
            this.handleAuthSuccess(response.data);
            return { success: true };
          }

          return {
            success: false,
            message: response?.message || 'Sign in failed. Please check your details and try again.',
          };
        }),
        catchError((err: Error) => {
          return of({
            success: false,
            message: err.message || 'Authentication failed. Please verify your credentials.',
          });
        })
      );
  }

  openLogoutModal(): void {
    this.showLogoutModal.set(true);
  }

  closeLogoutModal(): void {
    this.showLogoutModal.set(false);
  }

  confirmLogout(): void {
    this.showLogoutModal.set(false);
    this.logout();
  }

  logout(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }

    const refreshToken = this.getStoredItem(this.refreshKey);
    if (refreshToken && refreshToken !== 'demo-hardcoded-session-token') {
      this.apiService
        .post(API_ENDPOINTS.auth.logout, { refresh_token: refreshToken })
        .subscribe({
          error: () => { }, // Fire-and-forget
        });
    }

    this.clearStoredSession();
    this.currentUser.set(null);
    void this.router.navigateByUrl('/auth/login');
  }

  /**
   * Hardcoded demo user fallback ensuring application functionality when offline or on CORS
   */
  fallbackHardcodedLogin(
    email: string
  ): { success: boolean } {
    const isAdmin = email.toLowerCase().includes('admin');
    const prefix = email.split('@')[0] || 'User';
    const displayName = prefix.charAt(0).toUpperCase() + prefix.slice(1);

    const hardcodedUser: User = {
      id: isAdmin ? 1 : 2,
      name: displayName,
      email,
      role: isAdmin ? 'Super Admin' : 'Employee',
      token: 'demo-hardcoded-session-token',
      permissions: isAdmin
        ? [
          'Dashboard',
          'Role Management',
          'User Management',
          'Approval',
          'Project',
          'Leave Request',
          'Leave Management',
        ]
        : ['Approval', 'Project', 'Leave Request'],
    };

    this.setStoredItem(this.tokenKey, hardcodedUser.token!);
    this.persistSession(hardcodedUser);
    return { success: true };
  }

  /**
   * Check whether the logged-in user holds the specified module or activity permission.
   * Module visibility strictly follows the user's granted permissions list.
   */
  hasPermission(permission: string): boolean {
    const user = this.currentUser();
    if (!user) return false;

    // Super Admin role automatically has access to all modules
    const roleNorm = (user.role || '').trim().toLowerCase();
    if (roleNorm === 'super admin' || roleNorm === 'super_admin' || roleNorm === 'admin') {
      return true;
    }

    // Wildcard permissions grant access to everything
    if (
      user.permissions?.includes('all') ||
      user.permissions?.includes('*')
    ) {
      return true;
    }

    if (!user.permissions || !Array.isArray(user.permissions) || user.permissions.length === 0) {
      return false;
    }

    const targetNorm = permission.trim().toLowerCase();
    return user.permissions.some((p) => {
      if (typeof p !== 'string') return false;
      const pNorm = p.trim().toLowerCase();
      if (pNorm === targetNorm) return true;
      // Handle semantic alias variants (e.g. 'Approval' <-> 'Approval Hub', 'Project' <-> 'Projects')
      if (
        (targetNorm === 'approval' || targetNorm === 'approval hub') &&
        (pNorm === 'approval' || pNorm === 'approval hub' || pNorm === 'approval-hub')
      ) {
        return true;
      }
      if (
        (targetNorm === 'project' || targetNorm === 'projects') &&
        (pNorm === 'project' || pNorm === 'projects')
      ) {
        return true;
      }
      return false;
    });
  }

  /**
   * Returns the default landing route based on the logged-in user's permitted modules.
   * Avoids always landing on /dashboard when Dashboard permission is not granted.
   */
  getDefaultRoute(): string {
    const user = this.currentUser();
    if (!user) return '/auth/login';

    if (this.hasPermission('Dashboard')) return '/dashboard';
    if (this.hasPermission('Role Management')) return '/administration';
    if (this.hasPermission('User Management')) return '/users';
    if (this.hasPermission('Approval')) return '/approval-hub';
    if (this.hasPermission('Project')) return '/projects';
    if (this.hasPermission('Leave Request')) return '/leave/request';
    if (this.hasPermission('Leave Management')) return '/leave';

    return '/access-denied';
  }

  /**
   * Check whether the user has at least one permission in the requested list.
   */
  hasAnyPermission(permissions: string[]): boolean {
    return permissions.some((p) => this.hasPermission(p));
  }

  /**
   * Request password recovery link for registered user account (POST /api/v1/auth/forgot-password)
   */
  forgotPassword(email: string): Observable<{ success: boolean; message: string }> {
    const trimmedEmail = email.trim().toLowerCase();
    return this.apiService
      .post<any>(API_ENDPOINTS.auth.forgotPassword, { email: trimmedEmail })
      .pipe(
        map((res) => ({
          success: true,
          message: res?.message || 'Password reset link has been sent to your email.',
          data: res?.data,
        })),
        catchError((err: Error) => {
          return of({
            success: false,
            message: err.message || 'Unable to process password recovery request. Please check your email.',
          });
        })
      );
  }

  /**
   * Submit new password using single-use reset token (POST /api/v1/auth/reset-password)
   */
  resetPassword(payload: {
    token: string;
    email?: string;
    new_password: string;
    confirm_password: string;
  }): Observable<{ success: boolean; message: string }> {
    return this.apiService
      .post<void>(API_ENDPOINTS.auth.resetPassword, payload)
      .pipe(
        map((res) => ({
          success: true,
          message: res?.message || 'Password reset successful. You can now sign in with your new password.',
        })),
        catchError((err: Error) => {
          return of({
            success: false,
            message: err.message || 'Password reset failed. The link may have expired or is invalid.',
          });
        })
      );
  }

  getAccessToken(): string | null {
    const token = this.getStoredItem(this.tokenKey);
    return token && token !== 'demo-hardcoded-session-token' ? token : null;
  }

  getRefreshToken(): string | null {
    const token = this.getStoredItem(this.refreshKey);
    return token && token !== 'demo-hardcoded-session-token' ? token : null;
  }

  isMockSession(): boolean {
    return this.getStoredItem(this.tokenKey) === 'demo-hardcoded-session-token';
  }

  getTokenExpiry(): number | null {
    const val = this.getStoredItem(this.expiryKey);
    return val ? parseInt(val, 10) : null;
  }

  isTokenExpired(): boolean {
    const expiry = this.getTokenExpiry();
    if (!expiry) return false;
    return Date.now() >= expiry;
  }

  private persistSession(user: User): void {
    this.setStoredItem(this.sessionKey, JSON.stringify(user));
    this.currentUser.set(user);
  }

  private restore(): User | null {
    try {
      const user = JSON.parse(this.getStoredItem(this.sessionKey) ?? 'null') as User | null;
      if (!user || !this.getStoredItem(this.tokenKey) || !this.getStoredItem(this.refreshKey)) {
        return null;
      }
      return user;
    } catch {
      return null;
    }
  }

  private clearLegacyLocalSession(): void {
    for (const key of this.sessionStorageKeys) {
      localStorage.removeItem(key);
    }
    localStorage.removeItem('auth_storage_mode');
  }

  private getStoredItem(key: string): string | null {
    return sessionStorage.getItem(key);
  }

  private setStoredItem(key: string, value: string): void {
    localStorage.removeItem(key);
    sessionStorage.setItem(key, value);
  }

  private clearStoredSession(): void {
    for (const key of this.sessionStorageKeys) {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    }
  }
}
