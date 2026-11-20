import { Injectable, computed, inject, signal } from '@angular/core';
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
  admin: string;
  department: string;
  assignedRole: string;
  submittedBy: string;
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
  readonly isLoading = signal(false);
  readonly reviewDetails = signal<ApprovalDetails | null>(null);
  readonly reviewLoading = signal(false);
  readonly retryingEmailIds = signal<Set<string>>(new Set());

  readonly totalPending = computed(() => this.items().filter((item) => item.status === 'Pending').length);
  readonly employeeOnboardingCount = computed(() => this.items().filter((item) => item.type === 'EMPLOYEE ONBOARDING' && item.status === 'Pending').length);
  readonly leavesCount = computed(() => 0);
  readonly authorizedCount = computed(() => this.items().filter((item) => item.status === 'Authorized').length);
  readonly totalCount = computed(() => this.items().length);

  constructor() {
    this.loadApprovals();
  }

  loadApprovals(): void {
    this.isLoading.set(true);
    this.apiService.get<{ items: EmployeeApprovalRecord[] }>(API_ENDPOINTS.approvals.employees, { page: 1, page_size: 100, onboarding_status: 'PENDING_APPROVAL' }).subscribe({
      next: (res) => {
        const pending = (res.data?.items || []).map((record) => this.toItem(record));
        this.apiService.get<{ items: EmployeeApprovalRecord[] }>(API_ENDPOINTS.approvals.employees, { page: 1, page_size: 100, onboarding_status: 'APPROVED' }).subscribe({
          next: (approvedRes) => {
            this.items.set([...pending, ...(approvedRes.data?.items || []).map((record) => this.toItem(record))]);
            this.isLoading.set(false);
          },
          error: () => {
            this.items.set(pending);
            this.isLoading.set(false);
          },
        });
      },
      error: (err) => {
        this.isLoading.set(false);
        this.notification.show(`Could not load employee approvals: ${err.message}`, 'error');
      },
    });
  }

  private toItem(record: EmployeeApprovalRecord): ApprovalItem {
    const approved = record.onboarding_status === 'APPROVED';
    const rejected = record.onboarding_status === 'REJECTED';
    return {
      id: record.employee_id,
      userId: record.employee_id,
      type: 'EMPLOYEE ONBOARDING',
      title: `New Hire Onboarding: ${record.name}`,
      description: `${record.designation || 'Employee'} in ${record.department || 'Unassigned'}. ${approved ? 'Profile approved.' : rejected ? 'Profile rejected.' : 'Review submitted profile before approval.'}`,
      status: approved ? 'Authorized' : rejected ? 'Rejected' : 'Pending',
      submittedDate: record.submitted_at ? new Date(record.submitted_at).toLocaleDateString() : 'Not submitted',
      admin: 'HR Admin',
      department: record.department || '—',
      assignedRole: record.designation || 'Employee',
      submittedBy: record.name,
      loginState: approved ? 'Enabled (Active)' : 'Disabled (Pending Approval)',
      emailDispatchStatus: record.email_dispatch_status,
    };
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
      error: (err) => {
        this.reviewLoading.set(false);
        this.notification.show(err.message || 'Could not load submission details.', 'error');
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
        can_view_employee_details: Boolean(personal || contact || bank),
        employment: {
          company_email: data.employment?.company_email,
          personal_email: data.employment?.personal_email,
          department: data.employment?.department,
          designation: data.employment?.designation,
          entity: data.employment?.entity,
          work_location: data.employment?.work_location,
          pf_applicable: data.employment?.pf_applicable ? 'YES' : 'NO',
          joining_date: data.employment?.joining_date,
          start_date: data.employment?.employment_start_date,
          end_date: data.employment?.employment_end_date,
        },
        profile: (personal || contact || bank) ? {
          date_of_birth: personal?.birth_date,
          gender: personal?.gender,
          aadhaar_number: personal?.aadhaar_last_four ? `•••• •••• ${personal.aadhaar_last_four}` : undefined,
          pan_number: personal?.pan_present ? 'Verified on File' : undefined,
          passport_number: personal?.passport_present ? 'On File' : undefined,
          mobile_number: contact?.mobile_number,
          emergency_contact_name: contact?.emergency_contact_name,
          emergency_contact_phone: contact?.emergency_contact_phone,
          emergency_contact_relation: contact?.emergency_contact_relation,
          bank_name: bank?.bank_name,
          account_number: bank?.account_number_last_four ? `•••• ${bank.account_number_last_four}` : undefined,
          ifsc_code: bank?.ifsc_code,
          qualification: skills?.qualifications,
          languages,
        } : null,
        documents: (data.documents || []).map((doc: any) => ({
          id: String(doc.id),
          document_type: doc.document_type || 'DOCUMENT',
          filename: doc.filename || doc.file_name || 'Document',
          mime_type: doc.mime_type || 'application/pdf',
          size_bytes: doc.size_bytes || doc.file_size_bytes || 0,
          verification_status: doc.verification_status || 'PENDING',
          download_url: doc.download_url || API_ENDPOINTS.approvals.document(id, doc.id),
        })),
        rejection_reason: data.rejection_reason,
      };
    }

    // Otherwise format is from employee_service.employee_details (hr_details + employee_details)
    const hr = data.hr_details || {};
    const emp = data.employee_details || {};
    const fullName = [hr.first_name, hr.middle_name, hr.last_name].filter(Boolean).join(' ') || hr.employee_code || 'Employee';

    return {
      id: String(id),
      employee_id: String(id),
      employee_code: hr.employee_code || '',
      name: fullName,
      profile_status: data.profile_status || 'PENDING',
      account_status: data.account_status,
      can_view_employee_details: Boolean(data.can_view_employee_details),
      employment: {
        company_email: hr.company_email,
        personal_email: hr.personal_email,
        department: typeof hr.department === 'object' ? hr.department?.name : hr.department,
        designation: hr.designation,
        entity: typeof hr.entity === 'object' ? hr.entity?.name : hr.entity,
        work_location: hr.location,
        pf_applicable: hr.pf_applicable ? 'YES' : 'NO',
        joining_date: hr.joining_date,
        start_date: hr.start_date,
        end_date: hr.end_date,
      },
      profile: emp && Object.keys(emp).length > 0 ? {
        date_of_birth: emp.date_of_birth,
        gender: emp.gender,
        aadhaar_number: emp.aadhaar_number,
        pan_number: emp.pan_number,
        passport_number: emp.passport_number,
        mobile_number: emp.mobile_number,
        emergency_contact_name: emp.emergency_contact?.name,
        emergency_contact_phone: emp.emergency_contact?.phone,
        emergency_contact_relation: emp.emergency_contact?.relationship,
        bank_name: emp.bank_details?.bank_name,
        account_number: emp.bank_details?.account_number,
        ifsc_code: emp.bank_details?.ifsc_code,
        qualification: emp.qualification,
        languages: Array.isArray(emp.languages) ? emp.languages : [],
      } : null,
      documents: (emp.documents || []).map((doc: any) => ({
        id: String(doc.id),
        document_type: doc.document_type || 'DOCUMENT',
        filename: doc.file_name || doc.filename || 'Document',
        mime_type: doc.mime_type || 'application/pdf',
        size_bytes: doc.file_size_bytes || doc.size_bytes || 0,
        verification_status: doc.verification_status || 'PENDING',
        download_url: API_ENDPOINTS.approvals.document(id, doc.id),
      })),
    };
  }

  closeReview(): void {
    this.reviewDetails.set(null);
  }

  downloadDocument(employeeId: string | number, documentId: string | number): void {
    const url = API_ENDPOINTS.approvals.document(employeeId, documentId);
    window.open(url, '_blank');
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
