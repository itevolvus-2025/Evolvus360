import { Injectable, inject } from '@angular/core';
import { Observable, map, throwError } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { ApiResponse } from '../../../core/models/api.models';

export interface OnboardingCandidateInfo {
  employee_code: string;
  first_name: string;
  last_name: string;
  company_email: string;
  department: string;
  entity: string;
  pf_applicable: string;
  role: string;
  status: string;
  expires_at?: string;
  draft?: Record<string, string | null>;
  documents?: Array<{ document_type: string; original_filename: string }>;
}

export const DUMMY_ONBOARDING_CANDIDATE: OnboardingCandidateInfo = {
  employee_code: 'E014',
  first_name: 'Jhon',
  last_name: 'Doe',
  company_email: 'Jhon@evolvus.com',
  department: 'Chemistry',
  entity: 'ETPL',
  pf_applicable: 'YES',
  role: 'Employee',
  status: 'Pending',
};

@Injectable({ providedIn: 'root' })
export class OnboardingService {
  private readonly api = inject(ApiService);

  /**
   * Validate invitation token with backend (POST /api/v1/onboarding/invitations/validate)
   */
  validateInvitation(token: string): Observable<OnboardingCandidateInfo> {
    if (!token || token === 'dummy' || token === 'demo' || token === 'demo-token')
      return throwError(() => new Error('Invitation link is missing or invalid.'));

    return this.api
      .post<Record<string, any>>(API_ENDPOINTS.onboarding.validate, { token })
      .pipe(
        map((res) => {
          if (res?.data) {
            const d = res.data;
            return {
              employee_code: d['employee_code'] || DUMMY_ONBOARDING_CANDIDATE.employee_code,
              first_name: d['first_name'] || 'Jhon',
              last_name: d['last_name'] || 'Doe',
              company_email: d['company_email'] || DUMMY_ONBOARDING_CANDIDATE.company_email,
              department: d['department'] || DUMMY_ONBOARDING_CANDIDATE.department,
              entity: d['entity'] || d['company_name'] || DUMMY_ONBOARDING_CANDIDATE.entity,
              pf_applicable: d['pf_applicable'] || 'NO',
              role: d['role'] || DUMMY_ONBOARDING_CANDIDATE.role,
              status: 'Pending',
              expires_at: d['expires_at'],
              draft: d['draft'] || {},
              documents: d['documents'] || [],
            };
          }
          throw new Error('Invitation details were not returned by the server.');
        }),
      );
  }

  /**
   * Submit onboarding form payload with uploaded multipart files (POST /api/v1/onboarding/submit)
   */
  submitOnboarding(formData: FormData): Observable<any> {
    return this.api.postForm<any>(API_ENDPOINTS.onboarding.submit, formData);
  }

  saveDraft(formData: FormData): Observable<any> {
    return this.api.postForm<any>(API_ENDPOINTS.onboarding.saveDraft, formData);
  }
}
