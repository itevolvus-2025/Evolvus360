import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize, throwError, timeout } from 'rxjs';
import { LoadingService } from '../services/loading.service';

export const loadingInterceptor: HttpInterceptorFn = (request, next) => {
  const loadingService = inject(LoadingService);

  // Allow bypassing the loader with a custom header if needed
  if (request.headers.has('X-Skip-Loading')) {
    const cleanedRequest = request.clone({
      headers: request.headers.delete('X-Skip-Loading'),
    });
    return next(cleanedRequest);
  }

  // Derive an appropriate loading message based on HTTP method and endpoint
  let message = 'Processing, please wait...';
  const method = request.method.toUpperCase();
  const url = request.url.toLowerCase();

  if (method === 'GET') {
    if (url.includes('/users') || url.includes('/employees')) {
      message = 'Loading user records...';
    } else if (url.includes('/roles') || url.includes('/permissions')) {
      message = 'Loading roles & permissions...';
    } else if (url.includes('/approvals')) {
      message = 'Loading approvals...';
    } else if (url.includes('/departments') || url.includes('/master-data')) {
      message = 'Loading master data...';
    } else {
      message = 'Loading records...';
    }
  } else if (method === 'POST') {
    if (url.includes('/auth/login')) {
      message = 'Signing in...';
    } else if (url.includes('/deactivate')) {
      message = 'Deactivating user account...';
    } else if (url.includes('/approve')) {
      message = 'Approving request...';
    } else if (url.includes('/reject')) {
      message = 'Rejecting request...';
    } else if (url.includes('/send-invitation') || url.includes('/invite')) {
      message = 'Sending onboarding invitation...';
    } else {
      message = 'Saving record...';
    }
  } else if (method === 'PUT' || method === 'PATCH') {
    message = 'Saving changes...';
  } else if (method === 'DELETE') {
    message = 'Deleting record...';
  }

  loadingService.show(message);

  return next(request).pipe(
    timeout({
      each: 45_000,
      with: () => throwError(() => new HttpErrorResponse({
        status: 0,
        statusText: 'Request timed out',
      })),
    }),
    finalize(() => {
      loadingService.hide();
    })
  );
};
