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

  private readonly currentUser = signal<User | null>(this.restore());
  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUser() !== null);

  /** Active timeout handle for proactive background token refresh */
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;

  /** In-flight token refresh observable mutex to prevent race conditions during rotation */
  private refreshInProgress$: Observable<TokenResponse | null> | null = null;

  constructor() {
    this.checkAndResumeSession();
  }

  /**
   * Check stored session and schedule token refresh or refresh immediately if near expiry
   */
  private checkAndResumeSession(): void {
    const refreshToken = localStorage.getItem(this.refreshKey);
    const accessToken = localStorage.getItem(this.tokenKey);
    const expiryStr = localStorage.getItem(this.expiryKey);

    if (!refreshToken || refreshToken === 'demo-hardcoded-session-token' || !accessToken) {
      return;
    }

    if (expiryStr) {
      const expiryTimestamp = parseInt(expiryStr, 10);
      const remainingMs = expiryTimestamp - Date.now();
      const remainingSeconds = Math.floor(remainingMs / 1000);

      if (remainingSeconds > 60) {
        // Token still valid, schedule proactive refresh before it expires
        this.scheduleTokenRefresh(remainingSeconds);
      } else {
        // Token is expired or expiring within 60s, refresh immediately
        console.log('[AuthService] Token near expiry or expired on app startup. Refreshing immediately...');
        this.refreshToken().subscribe({
          error: (err) => console.warn('[AuthService] Startup token refresh error:', err),
        });
      }
    }
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

    const refreshToken = localStorage.getItem(this.refreshKey);
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
      localStorage.setItem(this.tokenKey, data.access_token);
    }
    if (data.refresh_token) {
      localStorage.setItem(this.refreshKey, data.refresh_token);
    }
    if (data.expires_in) {
      const expiryTimestamp = Date.now() + data.expires_in * 1000;
      localStorage.setItem(this.expiryKey, String(expiryTimestamp));
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
   * On CORS / network error or offline backend, gracefully falls back to the hardcoded user
   * as requested so local workflows are never interrupted.
   */
  login(
    email: string,
    password: string
  ): Observable<{ success: boolean; message?: string }> {
    if (!email || password.length < 6) {
      return of({
        success: false,
        message: 'Valid email and password (min 6 chars) are required.',
      });
    }

    const trimmedEmail = email.trim().toLowerCase();

    // 1. Try real Backend API
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

          // Fallback if response payload unexpected
          return this.fallbackHardcodedLogin(trimmedEmail);
        }),
        catchError((err: Error) => {
          // Check for CORS / connection refused / network error
          const isCorsOrNetwork =
            err.message.includes('CORS_OR_NETWORK_ERROR') ||
            err.message.includes('Unable to connect') ||
            err.message.includes('blocked') ||
            err.message.includes('0:');

          // If it's genuinely a CORS/network error while backend is offline, fall back to local session
          if (isCorsOrNetwork && !err.message.includes('401') && !err.message.includes('422')) {
            console.warn(
              'Backend offline or CORS restricted. Falling back to local hardcoded user session:',
              err.message
            );
            return of(this.fallbackHardcodedLogin(trimmedEmail));
          }

          return of({
            success: false,
            message: err.message || 'Authentication failed. Please verify your credentials.',
          });
        })
      );
  }

  logout(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }

    const refreshToken = localStorage.getItem(this.refreshKey);
    if (refreshToken && refreshToken !== 'demo-hardcoded-session-token') {
      this.apiService
        .post(API_ENDPOINTS.auth.logout, { refresh_token: refreshToken })
        .subscribe({
          error: () => { }, // Fire-and-forget
        });
    }

    localStorage.removeItem(this.sessionKey);
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshKey);
    localStorage.removeItem(this.expiryKey);
    this.currentUser.set(null);
    void this.router.navigateByUrl('/auth/login');
  }

  /**
   * Hardcoded demo user fallback ensuring application functionality when offline or on CORS
   */
  fallbackHardcodedLogin(email: string): { success: boolean } {
    const isAdmin =
      email.includes('admin') ||
      email.includes('asha');

    const hardcodedUser: User = {
      id: isAdmin ? 1 : 2,
      name: isAdmin ? 'Asha Rao' : 'Meera Iyer',
      email,
      role: isAdmin ? 'Super Admin' : 'HR Manager',
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

    localStorage.setItem(this.tokenKey, hardcodedUser.token!);
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

    return '/dashboard';
  }

  /**
   * Check whether the user has at least one permission in the requested list.
   */
  hasAnyPermission(permissions: string[]): boolean {
    return permissions.some((p) => this.hasPermission(p));
  }

  getAccessToken(): string | null {
    const token = localStorage.getItem(this.tokenKey);
    return token && token !== 'demo-hardcoded-session-token' ? token : null;
  }

  getRefreshToken(): string | null {
    const token = localStorage.getItem(this.refreshKey);
    return token && token !== 'demo-hardcoded-session-token' ? token : null;
  }

  isMockSession(): boolean {
    return localStorage.getItem(this.tokenKey) === 'demo-hardcoded-session-token';
  }

  getTokenExpiry(): number | null {
    const val = localStorage.getItem(this.expiryKey);
    return val ? parseInt(val, 10) : null;
  }

  isTokenExpired(): boolean {
    const expiry = this.getTokenExpiry();
    if (!expiry) return false;
    return Date.now() >= expiry;
  }

  private persistSession(user: User): void {
    localStorage.setItem(this.sessionKey, JSON.stringify(user));
    this.currentUser.set(user);
  }

  private restore(): User | null {
    try {
      return JSON.parse(localStorage.getItem(this.sessionKey) ?? 'null') as User | null;
    } catch {
      return null;
    }
  }
}
