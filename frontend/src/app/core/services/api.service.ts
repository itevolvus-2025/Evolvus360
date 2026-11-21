import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, catchError, throwError } from 'rxjs';
import { ApiResponse } from '../models/api.models';

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  /**
   * Generic GET request returning typed data from ApiResponse envelope
   */
  get<T>(
    url: string,
    params?: HttpParams | Record<string, string | number | boolean>
  ): Observable<ApiResponse<T>> {
    return this.http
      .get<ApiResponse<T>>(url, { params: this.buildParams(params) })
      .pipe(catchError((err) => this.handleError(err)));
  }

  /**
   * Generic POST request
   */
  post<T>(url: string, body: unknown, headers?: HttpHeaders): Observable<ApiResponse<T>> {
    return this.http
      .post<ApiResponse<T>>(url, body, { headers })
      .pipe(catchError((err) => this.handleError(err)));
  }

  /** POST multipart form data without setting Content-Type (the browser adds its boundary). */
  postForm<T>(url: string, body: FormData): Observable<ApiResponse<T>> {
    return this.http
      .post<ApiResponse<T>>(url, body)
      .pipe(catchError((err) => this.handleError(err)));
  }

  /**
   * Generic PUT request
   */
  put<T>(url: string, body: unknown): Observable<ApiResponse<T>> {
    return this.http
      .put<ApiResponse<T>>(url, body)
      .pipe(catchError((err) => this.handleError(err)));
  }

  /**
   * Generic PATCH request
   */
  patch<T>(url: string, body: unknown): Observable<ApiResponse<T>> {
    return this.http
      .patch<ApiResponse<T>>(url, body)
      .pipe(catchError((err) => this.handleError(err)));
  }

  /**
   * Generic DELETE request
   */
  delete<T>(url: string): Observable<ApiResponse<T>> {
    return this.http
      .delete<ApiResponse<T>>(url)
      .pipe(catchError((err) => this.handleError(err)));
  }

  private buildParams(
    params?: HttpParams | Record<string, string | number | boolean>
  ): HttpParams | undefined {
    if (!params) return undefined;
    if (params instanceof HttpParams) return params;

    let httpParams = new HttpParams();
    for (const [key, val] of Object.entries(params)) {
      if (val !== undefined && val !== null) {
        httpParams = httpParams.set(key, String(val));
      }
    }
    return httpParams;
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unexpected error occurred. Please try again.';
    let fieldErrors: Record<string, string> = {};

    // Status 0 represents browser CORS rejection or connection refused
    if (error.status === 0) {
      errorMessage = 'CORS_OR_NETWORK_ERROR: Backend server connection was blocked or refused on port 8000.';
    } else if (error.error) {
      if (typeof error.error === 'string') {
        errorMessage = error.error;
      } else if (error.error.message) {
        errorMessage = error.error.message;
        if (error.error.errors && typeof error.error.errors === 'object') {
          fieldErrors = Object.fromEntries(
            Object.entries(error.error.errors).map(([key, value]) => [key, String(value)]),
          );
        }
      } else if (error.error.detail) {
        if (typeof error.error.detail === 'string') {
          errorMessage = error.error.detail;
        } else if (Array.isArray(error.error.detail)) {
          errorMessage = error.error.detail.map((d: any) => d.msg || d).join(', ');
        }
      }
    } else if (error.statusText) {
      errorMessage = `${error.status}: ${error.statusText}`;
    }

    return throwError(() => new ApiRequestError(errorMessage, error.status, fieldErrors));
  }
}
