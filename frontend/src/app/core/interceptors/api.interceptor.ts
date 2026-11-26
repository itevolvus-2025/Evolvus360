import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const apiInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  // Invitation onboarding is authorized by its 48-hour invitation token in the
  // request body. Do not couple these public endpoints to the user's session.
  const isInvitationRequest = ['/onboarding/invitations/validate', '/onboarding/draft', '/onboarding/submit']
    .some((path) => request.url.includes(path));
  const token = authService.getAccessToken();
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };

  // Only attach Bearer header if a valid real token exists (never dummy fallback tokens)
  if (!isInvitationRequest && token && token !== 'demo-hardcoded-session-token') {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const apiRequest = request.clone({
    setHeaders: headers,
  });

  return next(apiRequest).pipe(
    catchError((error: unknown) => {
      // Intercept 401 Unauthorized for regular API endpoints (excluding auth operations)
      if (
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        !isInvitationRequest &&
        !['/auth/login', '/auth/refresh', '/auth/logout', '/auth/forgot-password', '/auth/reset-password']
          .some((path) => request.url.includes(path))
      ) {
        console.warn(
          `[ApiInterceptor] 401 Unauthorized on ${request.url}. Attempting token refresh...`
        );
        return authService.refreshToken().pipe(
          switchMap((tokenResponse) => {
            if (tokenResponse && tokenResponse.access_token) {
              console.log(
                `[ApiInterceptor] Token refreshed successfully. Retrying request: ${request.url}`
              );
              const retryRequest = request.clone({
                setHeaders: {
                  ...headers,
                  Authorization: `Bearer ${tokenResponse.access_token}`,
                },
              });
              return next(retryRequest);
            }
            return throwError(() => error);
          }),
          catchError((refreshErr) => {
            console.error('[ApiInterceptor] Token refresh failed during 401 retry:', refreshErr);
            return throwError(() => refreshErr);
          })
        );
      }

      return throwError(() => error);
    })
  );
};
