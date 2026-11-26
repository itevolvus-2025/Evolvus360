import { Injectable, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { EmployeeApprovalRecord } from '../../../core/models/api.models';

export type ApprovalType = 'EMPLOYEE ONBOARDING' | 'LEAVES & TIME-OFF' | 'ROLE ESCALATION';
export type ApprovalStatus = 'Pending' | 'Authorized' | 'Rejected';

export interface ApprovalItem {
  id: string | number;
  userId?: string | number;
  type: ApprovalType;
  title: string;
  description: string;
  status: ApprovalStatus;
  submittedDate: string;
  employeeName?: string;
  admin?: string;
  department: string;
  assignedRole: string;
  submittedBy?: string;
  loginState: string;
  emailDispatchStatus?: string;
}

export interface ReviewDocument {
  id: string;
  document_type: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  verification_status: string;
  download_url?: string;
}

export interface ApprovalDetails {
  id: string;
  employee_id: string;
  employee_code: string;
  name: string;
  profile_status: string;
  account_status?: string;
  onboarding_status?: string;
  can_view_employee_details: boolean;

  employment: {
    company_email?: string;
    personal_email?: string;
    department?: string;
    designation?: string;
    entity?: string;
    work_location?: string;
    pf_applicable?: string | boolean;
    joining_date?: string;
    start_date?: string;
    end_date?: string;
  };

  profile: {
    date_of_birth?: string;
    gender?: string;
    aadhaar_number?: string;
    pan_number?: string;
    passport_number?: string;
    uan_number?: string;
    mobile_number?: string;
    emergency_contact_name?: string;
    emergency_contact_phone?: string;
    emergency_contact_relation?: string;
    bank_name?: string;
    account_number?: string;
    ifsc_code?: string;
    qualification?: string;
    languages?: string[];
  } | null;

  documents: ReviewDocument[];
  rejection_reason?: string;
}

@Injectable({ providedIn: 'root' })
export class ApprovalHubService {
  private readonly apiService = inject(ApiService);
  private readonly notification = inject(NotificationService);

  readonly items = signal<ApprovalItem[]>([]);
  readonly totalApprovalCount = signal(0);
  readonly isLoading = signal(false);
  readonly reviewDetails = signal<ApprovalDetails | null>(null);
  readonly reviewLoading = signal(false);
  readonly retryingEmailIds = signal<Set<string>>(new Set());

  readonly totalPending = computed(() => this.items().filter((item) => item.status === 'Pending').length);
  readonly employeeOnboardingCount = computed(() => this.items().filter((item) => item.type === 'EMPLOYEE ONBOARDING' && item.status === 'Pending' && item.loginState.includes('Active')).length);
  readonly leavesCount = computed(() => 0);
  readonly authorizedCount = computed(() => this.items().filter((item) => item.status === 'Authorized').length);
  readonly totalCount = computed(() => this.totalApprovalCount());

  constructor() {
    this.loadApprovals();
  }

  loadApprovals(onboardingStatus?: string, search?: string): void {
    this.isLoading.set(true);
    const statusMap: Record<string, string> = { 'Pending Only': 'PENDING_APPROVAL', Authorized: 'APPROVED', Rejected: 'REJECTED' };
    const params: Record<string, string | number> = { page: 1, page_size: 100 };
    if (search && search.trim()) {
      params['search'] = search.trim();
    }
    const selectedStatus = onboardingStatus ? statusMap[onboardingStatus] : undefined;
    if (selectedStatus) params['onboarding_status'] = selectedStatus;
    const loadStatus = (status: string) => this.apiService.get<{ items: EmployeeApprovalRecord[]; total?: number; page?: number; page_size?: number }>(API_ENDPOINTS.approvals.employees, { ...params, onboarding_status: status });
    const request = forkJoin(['PENDING_APPROVAL', 'APPROVED', 'REJECTED'].map(loadStatus));
    request.subscribe({
      next: (responses) => {
        const mapped = responses.flatMap((response) => (response.data?.items || []).map((record) => this.toItem(record)));
        this.items.set(mapped);
        const total = responses.reduce((sum, response) => sum + (response.data?.total ?? response.data?.items?.length ?? 0), 0);
        this.totalApprovalCount.set(total);
        this.isLoading.set(false);
      },
      error: () => {
        this.items.set([]);
        this.totalApprovalCount.set(0);
        this.isLoading.set(false);
      },
    });
  }

  private toItem(record: EmployeeApprovalRecord): ApprovalItem {
    const approved = record.onboarding_status === 'APPROVED';
    const rejected = record.onboarding_status === 'REJECTED';
    const employeeName = this.formatPersonName(record.name);
    return {
      id: record.employee_id,
      userId: record.employee_id,
      type: 'EMPLOYEE ONBOARDING',
      title: `New Hire Onboarding: ${employeeName}`,
      description: `HR Manager registered new employee ${employeeName}${record.designation ? ` Proposed Role: ${record.designation}.` : '.'} Requires approval to activate system login credentials.`,
      status: approved ? 'Authorized' : rejected ? 'Rejected' : 'Pending',
      submittedDate: record.submitted_at
        ? new Date(record.submitted_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
        : '',
      employeeName,
      admin: (record as any).admin || undefined,
      department: record.department || '',
      assignedRole: record.designation || '',
      submittedBy: (record as any).submitted_by || undefined,
      loginState: approved ? 'Enabled (Active)' : rejected ? 'Disabled (Rejected)' : 'Disabled (Pending Approval)',
      emailDispatchStatus: record.email_dispatch_status,
    };
  }

  private formatPersonName(name: string | null | undefined): string {
    return (name || '').trim().toLocaleLowerCase()
      .replace(/\b([\p{L}])/gu, (letter) => letter.toLocaleUpperCase());
  }

  review(id: string | number): void {
    this.reviewLoading.set(true);
    this.reviewDetails.set(null);

    // Call GET /api/v1/approvals/employees/{employee_id}
    this.apiService.get<any>(API_ENDPOINTS.approvals.employee(id)).subscribe({
      next: (res) => {
        const d = res.data;
        if (!d) {
          this.fallbackReviewUser(id);
          return;
        }
        this.reviewDetails.set(this.normalizeApprovalDetails(id, d));
        this.reviewLoading.set(false);
      },
      error: () => {
        // Fallback to GET /api/v1/users/{user_id}
        this.fallbackReviewUser(id);
      },
    });
  }

  private fallbackReviewUser(id: string | number): void {
    this.apiService.get<any>(API_ENDPOINTS.users.detail(id)).subscribe({
      next: (res) => {
        const d = res.data;
        this.reviewDetails.set(this.normalizeApprovalDetails(id, d));
        this.reviewLoading.set(false);
      },
      error: () => {
        this.reviewDetails.set(null);
        this.reviewLoading.set(false);
      },
    });
  }

  private normalizeApprovalDetails(id: string | number, data: any): ApprovalDetails {
    // Check if format is from approval_service.details
    if (data.employment) {
      const personal = data.personal_details;
      const contact = data.contact_details;
      const bank = data.bank_details;
      const skills = data.skills_and_interests;

      const languages: string[] = Array.isArray(skills?.languages_spoken)
        ? skills.languages_spoken
        : typeof skills?.languages_spoken === 'string'
        ? (()=>{ try { return JSON.parse(skills.languages_spoken); } catch { return [skills.languages_spoken]; } })()
        : [];

      return {
        id: String(id),
        employee_id: data.employee_id || String(id),
        employee_code: data.employee_code || '',
        name: data.name || '',
        profile_status: data.profile_status || data.onboarding_status || 'PENDING',
        account_status: data.account?.status,
        onboarding_status: data.onboarding_status,
        can_view_employee_details: true,
        employment: {
          company_email: data.employment?.company_email || '',
          personal_email: data.employment?.personal_email || '',
          department: data.employment?.department || '',
          designation: data.employment?.designation || '',
          entity: data.employment?.entity || '',
          work_location: data.employment?.work_location || '',
          pf_applicable: data.employment?.pf_applicable == null ? '' : data.employment.pf_applicable ? 'YES' : 'NO',
          joining_date: data.employment?.joining_date || '',
          start_date: data.employment?.employment_start_date || '',
          end_date: data.employment?.employment_end_date,
        },
        profile: {
          date_of_birth: personal?.birth_date || '',
          gender: personal?.gender || '',
          aadhaar_number: personal?.aadhaar_last_four ? `•••• •••• ${personal.aadhaar_last_four}` : '',
          pan_number: personal?.pan_number || '',
          passport_number: personal?.passport_number || '',
          uan_number: personal?.uan_number || '',
          mobile_number: contact?.mobile_number || '',
          emergency_contact_name: contact?.emergency_contact_name || '',
          emergency_contact_phone: contact?.emergency_contact_phone || '',
          emergency_contact_relation: contact?.emergency_contact_relation || '',
          bank_name: bank?.bank_name || '',
          account_number: bank?.account_number_last_four ? `••••${bank.account_number_last_four}` : '',
          ifsc_code: bank?.ifsc_code || '',
          qualification: skills?.qualifications || '',
          languages,
        },
        documents: (data.documents && data.documents.length > 0) ? (data.documents || []).map((doc: any) => ({
          id: String(doc.id),
          document_type: doc.document_type || '',
          filename: doc.filename || doc.file_name || '',
          mime_type: doc.mime_type || '',
          size_bytes: doc.size_bytes || doc.file_size_bytes || 0,
          verification_status: doc.verification_status || '',
          download_url: doc.download_url || API_ENDPOINTS.approvals.document(id, doc.id),
        })) : [],
        rejection_reason: data.rejection_reason,
      };
    }

    // Otherwise format is from employee_service.employee_details (hr_details + employee_details)
    const hr = data.hr_details || {};
    const emp = data.employee_details || {};
    const fullName = [hr.first_name, hr.middle_name, hr.last_name].filter(Boolean).join(' ');

    return {
      id: String(id),
      employee_id: String(id),
      employee_code: hr.employee_code || '',
      name: fullName,
      profile_status: data.profile_status || 'PENDING',
      account_status: data.account_status,
      can_view_employee_details: true,
      employment: {
        company_email: hr.company_email || '',
        personal_email: hr.personal_email || '',
        department: typeof hr.department === 'object' ? hr.department?.name : (hr.department || ''),
        designation: hr.designation || '',
        entity: typeof hr.entity === 'object' ? hr.entity?.name : (hr.entity || ''),
        work_location: hr.location || '',
        pf_applicable: hr.pf_applicable == null ? '' : hr.pf_applicable ? 'YES' : 'NO',
        joining_date: hr.joining_date || '',
        start_date: hr.start_date || '',
        end_date: hr.end_date,
      },
      profile: {
        date_of_birth: emp.date_of_birth || '',
        gender: emp.gender || '',
        aadhaar_number: emp.aadhaar_number || '',
        pan_number: emp.pan_number || '',
        passport_number: emp.passport_number || '',
        uan_number: emp.uan_number || '',
        mobile_number: emp.mobile_number || '',
        emergency_contact_name: emp.emergency_contact?.name || '',
        emergency_contact_phone: emp.emergency_contact?.phone || '',
        emergency_contact_relation: emp.emergency_contact?.relationship || '',
        bank_name: emp.bank_details?.bank_name || '',
        account_number: emp.bank_details?.account_number || '',
        ifsc_code: emp.bank_details?.ifsc_code || '',
        qualification: emp.qualification || '',
        languages: Array.isArray(emp.languages) ? emp.languages : [],
      },
      documents: (emp.documents && emp.documents.length > 0) ? (emp.documents || []).map((doc: any) => ({
        id: String(doc.id),
        document_type: doc.document_type || '',
        filename: doc.file_name || doc.filename || '',
        mime_type: doc.mime_type || '',
        size_bytes: doc.file_size_bytes || doc.size_bytes || 0,
        verification_status: doc.verification_status || '',
        download_url: API_ENDPOINTS.approvals.document(id, doc.id),
      })) : [],
    };
  }

  closeReview(): void {
    this.reviewDetails.set(null);
  }

  downloadDocument(employeeId: string | number, documentId: string | number): void {
    const preview = window.open('', '_blank');
    if (!preview) {
      this.notification.show('Allow pop-ups to preview this document.', 'error');
      return;
    }
    this.apiService.getBlob(API_ENDPOINTS.approvals.document(employeeId, documentId)).subscribe({
      next: (file) => {
        const url = URL.createObjectURL(file);
        preview.location.href = url;
        window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      },
      error: (error: Error) => {
        preview.close();
        this.notification.show(error.message || 'Could not load the document.', 'error');
      },
    });
  }

  retryInvitation(id: string | number): void {
    this.apiService.post<{ email_dispatch_status: string }>(API_ENDPOINTS.users.inviteRetry(id), {}).subscribe({
      next: (res) => {
        const ok = res.data?.email_dispatch_status === 'DISPATCHED';
        this.notification.show(ok ? 'Invitation email dispatched successfully.' : 'Email dispatch pending/failed. You can retry again.', ok ? 'success' : 'info');
        this.loadApprovals();
      },
      error: (err) => this.notification.show(err.message || 'Invitation retry failed.', 'error'),
    });
  }

  sendInvitation(id: string | number): void {
    this.apiService.post<{ email_dispatch_status: string }>(API_ENDPOINTS.users.invite(id), {}).subscribe({
      next: (res) => {
        const ok = res.data?.email_dispatch_status === 'DISPATCHED';
        this.notification.show(ok ? 'Onboarding link sent to candidate email.' : 'Email service unavailable. Please retry shortly.', ok ? 'success' : 'error');
        this.loadApprovals();
      },
      error: (err) => this.notification.show(err.message || 'Could not send invitation email.', 'error'),
    });
  }

  authorize(id: string | number): void {
    this.apiService.post(API_ENDPOINTS.approvals.approveEmployee(id), {}).subscribe({
      next: () => {
        this.notification.show('Employee profile approved & system credentials activated.', 'success');
        this.closeReview();
        this.loadApprovals();
      },
      error: (err) => this.notification.show(err.message || 'Approval failed.', 'error'),
    });
  }

  reject(id: string | number, reason: string): void {
    this.apiService.post(API_ENDPOINTS.approvals.rejectEmployee(id), { reason }).subscribe({
      next: () => {
        this.notification.show('Employee profile rejected with feedback notice sent to candidate.', 'info');
        this.closeReview();
        this.loadApprovals();
      },
      error: (err) => this.notification.show(err.message || 'Rejection failed.', 'error'),
    });
  }

  retryEmail(id: string | number, event: 'approval' | 'rejection' | string): void {
    const key = `${id}:${event}`;
    this.retryingEmailIds.update((ids) => new Set(ids).add(key));
    this.apiService.post<{ email_dispatch_status: string }>(API_ENDPOINTS.approvals.retryEmail(id, event), {}).subscribe({
      next: (res) => {
        const success = res.data?.email_dispatch_status === 'DISPATCHED';
        this.retryingEmailIds.update((ids) => {
          const next = new Set(ids);
          next.delete(key);
          return next;
        });
        this.notification.show(
          success ? 'Notification email dispatched successfully.' : 'Email delivery failed. You may retry again.',
          success ? 'success' : 'error'
        );
      },
      error: (err) => {
        this.retryingEmailIds.update((ids) => {
          const next = new Set(ids);
          next.delete(key);
          return next;
        });
        this.notification.show(err.message || 'Email retry failed.', 'error');
      },
    });
  }
}
