import { Injectable, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { EmployeeApiRecord, MasterDataOption } from '../../../core/models/api.models';

export type UserStatus = 'Active' | 'Inactive' | 'Deactive' | 'Pending';
export type ProfileStatus = 'Pending' | 'Submitted' | 'Approved' | 'Rejected';

export interface UserRow {
  id: number | string;
  // Personal Identity
  firstName: string;
  middleName?: string;
  lastName: string;
  name: string; // combined firstName + lastName for displays

  // Department & Role Assignment
  department: string;
  departmentId?: string;
  role: string;
  roleId?: string;
  designation: string;
  location?: string;
  entity?: string;
  entityId?: string;
  code: string; // User/Employee code, e.g. EV-8492 or E001

  // Contact Information & Compliance
  companyEmail: string;
  personalEmail?: string;
  email: string; // Primary email reference
  phone?: string;
  pfApplicable: 'Yes' | 'No';

  // Employment Timeline
  joiningDate?: string;
  startDate?: string;
  endDate?: string;

  // Status & Profile
  status: UserStatus;
  profile: ProfileStatus;
  emailDispatchStatus?: string;
  invitationStatus?: string;
  reasonForChange?: string;
  effectiveDate?: string;
  employeeDetails?: any;
  rawDetails?: any;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly apiService = inject(ApiService);

  readonly users = signal<UserRow[]>([]);

  readonly isLoading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly departments = signal<MasterDataOption[]>([]);
  readonly roles = signal<MasterDataOption[]>([]);
  readonly entities = signal<MasterDataOption[]>([]);
  readonly isSaving = signal(false);
  readonly failedInvitationIds = signal<Set<string>>(new Set());

  constructor() {
    this.loadUsers();
  }

  /**
   * Load users from backend API (GET /api/v1/users)
   */
  loadUsers(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.apiService.get<{ items: EmployeeApiRecord[] }>(API_ENDPOINTS.users.list, { page: 1, page_size: 100 }).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        const items = res?.data?.items;
        if (Array.isArray(items)) {
          const mapped: UserRow[] = items.map((u: any) => {
            const firstName = u.first_name || '';
            const lastName = u.last_name || '';
            const fullName = [firstName, u.middle_name, lastName]
              .filter(Boolean)
              .join(' ')
              .trim() || u.employee_code || 'User';

            return {
              id: u.id || u.user_id || u.employee_code || 'temp_user',
              firstName,
              middleName: u.middle_name || '',
              lastName,
              name: fullName,
              code: u.employee_code || 'E001',
              companyEmail: u.company_email || '',
              personalEmail: u.personal_email || '',
              email: u.company_email || '',
              phone: u.phone || u.phone_number || '',
              role: typeof u.role === 'object' ? u.role?.name || 'Employee' : u.role || 'Employee',
              roleId: typeof u.role === 'object' ? u.role?.id : undefined,
              department: typeof u.department === 'object' ? u.department?.name || '' : u.department || '',
              departmentId: typeof u.department === 'object' ? u.department?.id : undefined,
              designation: u.designation || 'Specialist',
              location: u.location || '',
              entity: typeof u.entity === 'object' ? u.entity?.name || '' : u.entity || '',
              entityId: typeof u.entity === 'object' ? u.entity?.id : undefined,
              pfApplicable: u.pf_applicable ? 'Yes' : 'No',
              joiningDate: u.joining_date || '',
              startDate: u.start_date || '',
              endDate: u.end_date || '',
              status: this.mapAccountStatus(u.account_status) as UserStatus,
              profile: (u.profile_status === 'APPROVED' ? 'Approved' : ['SUBMITTED', 'PENDING_APPROVAL'].includes(u.profile_status) ? 'Submitted' : u.profile_status === 'REJECTED' ? 'Rejected' : 'Pending') as ProfileStatus,
              emailDispatchStatus: u.email_dispatch_status,
              invitationStatus: u.invitation_status,
            };
          });
          this.users.set(mapped);
          console.log(`[UserService] Loaded ${mapped.length} users from backend API.`);
        } else {
          this.users.set([]);
          this.loadError.set('The users API returned an unexpected response.');
        }
      },
      error: (err) => {
        this.isLoading.set(false);
        this.users.set([]);
        this.loadError.set(err.message || 'Could not load users.');
        console.warn('[UserService] Could not load users from backend API:', err.message);
      },
    });
  }

  loadMasterData(): void {
    this.apiService.get<MasterDataOption[]>(API_ENDPOINTS.masterData.departments).subscribe({
      next: (res) => this.departments.set(res.data || []),
      error: (err) => console.warn('[UserService] Could not load departments:', err.message),
    });
    this.apiService.get<MasterDataOption[]>(API_ENDPOINTS.masterData.roles).subscribe({
      next: (res) => this.roles.set(res.data || []),
      error: (err) => console.warn('[UserService] Could not load roles:', err.message),
    });
    this.apiService.get<MasterDataOption[]>(API_ENDPOINTS.masterData.entities).subscribe({
      next: (res) => this.entities.set(res.data || []),
      error: (err) => console.warn('[UserService] Could not load entities:', err.message),
    });
  }

  private mapAccountStatus(status?: string): UserStatus {
    if (status === 'ACTIVE') return 'Active';
    if (status === 'INVITED' || status === 'PENDING_APPROVAL') return 'Pending';
    return 'Inactive';
  }

  createEmployee(payload: Record<string, unknown>, onSuccess: (result: EmployeeApiRecord) => void, onError: (message: string, fieldErrors?: Record<string, string>) => void): void {
    if (this.isSaving()) return;
    this.isSaving.set(true);
    this.apiService.post<EmployeeApiRecord>(API_ENDPOINTS.users.create, payload).subscribe({
      next: (res) => {
        this.isSaving.set(false);
        if (res.data) {
          this.rememberEmployee(res.data);
          if (res.data.email_dispatch_status === 'FAILED') {
            this.failedInvitationIds.update((ids) => new Set(ids).add(String(res.data.id)));
          }
          onSuccess(res.data);
        }
      },
      error: (err) => {
        this.isSaving.set(false);
        onError(err.message || 'Could not create user.', (err as { fieldErrors?: Record<string, string> }).fieldErrors);
      },
    });
  }

  sendInvitation(id: string | number, onDone: (success: boolean, message: string) => void): void {
    this.apiService.post<{ email_dispatch_status: string }>(API_ENDPOINTS.users.invite(id), {}).subscribe({
      next: (res) => {
        const success = res.data?.email_dispatch_status === 'DISPATCHED';
        this.failedInvitationIds.update((ids) => {
          const next = new Set(ids);
          if (success) next.delete(String(id));
          else next.add(String(id));
          return next;
        });
        this.loadUsers();
        onDone(success, success ? 'Invitation email dispatched successfully.' : 'Email could not be dispatched immediately. You can retry.');
      },
      error: (err) => {
        this.failedInvitationIds.update((ids) => new Set(ids).add(String(id)));
        this.loadUsers();
        onDone(false, err.message || 'Invitation email delivery failed. Retry it after email service is available.');
      },
    });
  }

  retryInvitation(id: string | number, onDone: (success: boolean, message: string) => void): void {
    this.apiService.post<{ email_dispatch_status: string }>(API_ENDPOINTS.users.inviteRetry(id), {}).subscribe({
      next: (res) => {
        const success = res.data?.email_dispatch_status === 'DISPATCHED';
        this.failedInvitationIds.update((ids) => {
          const next = new Set(ids);
          if (success) next.delete(String(id));
          else next.add(String(id));
          return next;
        });
        this.loadUsers();
        onDone(success, success ? 'Invitation email sent.' : 'Invitation email could not be sent. Please retry.');
      },
      error: (err) => onDone(false, err.message || 'Invitation retry failed.'),
    });
  }

  getEmployee(id: string | number, onSuccess: (user: UserRow, fullData?: any) => void, onError?: (msg: string) => void): void {
    this.apiService.get<any>(API_ENDPOINTS.users.detail(id)).subscribe({
      next: (res) => {
        const d = res.data;
        if (d && d.hr_details) {
          const hr = d.hr_details;
          const mapped: UserRow = {
            id: d.id || id,
            firstName: hr.first_name || '',
            middleName: hr.middle_name || '',
            lastName: hr.last_name || '',
            name: [hr.first_name, hr.middle_name, hr.last_name].filter(Boolean).join(' ').trim() || hr.employee_code,
            code: hr.employee_code || '',
            companyEmail: hr.company_email || '',
            personalEmail: hr.personal_email || '',
            email: hr.company_email || '',
            phone: hr.phone || d.employee_details?.mobile_number || '',
            role: typeof hr.role === 'object' ? hr.role?.name : hr.role || 'Employee',
            roleId: typeof hr.role === 'object' ? hr.role?.id : undefined,
            department: typeof hr.department === 'object' ? hr.department?.name : hr.department || '',
            departmentId: typeof hr.department === 'object' ? hr.department?.id : undefined,
            designation: hr.designation || '',
            location: hr.location || '',
            entity: typeof hr.entity === 'object' ? hr.entity?.name : hr.entity || '',
            entityId: typeof hr.entity === 'object' ? hr.entity?.id : undefined,
            pfApplicable: hr.pf_applicable ? 'Yes' : 'No',
            joiningDate: hr.joining_date || '',
            startDate: hr.start_date || '',
            endDate: hr.end_date || '',
            status: this.mapAccountStatus(d.account_status),
            profile: (d.profile_status === 'APPROVED' ? 'Approved' : ['SUBMITTED', 'PENDING_APPROVAL'].includes(d.profile_status) ? 'Submitted' : 'Pending'),
            employeeDetails: d.employee_details || null,
            rawDetails: d,
          };
          onSuccess(mapped, d);
          return;
        }
        const local = this.getUserById(id);
        if (local) onSuccess(local);
        else if (onError) onError('User not found.');
      },
      error: (err) => {
        const local = this.getUserById(id);
        if (local) onSuccess(local);
        else if (onError) onError(err.message || 'User not found.');
      },
    });
  }

  updateEmployee(id: string | number, payload: Record<string, unknown>, onSuccess: () => void, onError: (msg: string) => void): void {
    if (this.isSaving()) return;
    this.isSaving.set(true);
    this.apiService.put(API_ENDPOINTS.users.update(id), payload).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.loadUsers();
        onSuccess();
      },
      error: (err) => {
        this.isSaving.set(false);
        onError(err.message || 'Could not update user.');
      },
    });
  }

  private rememberEmployee(result: EmployeeApiRecord): void {
    const existing = this.users().find((user) => String(user.id) === result.id);
    if (existing) return;
    const user: UserRow = {
      id: result.id,
      firstName: '', middleName: '', lastName: '',
      name: 'New user', department: '', role: '', designation: '', code: result.employee_code,
      companyEmail: '', email: '', pfApplicable: 'No', status: 'Pending', profile: 'Pending',
      emailDispatchStatus: result.email_dispatch_status,
    };
    this.users.update((list) => [user, ...list]);
    this.loadUsers();
  }

  /** KPI Metrics */
  readonly totalUsersCount = computed(() => this.users().length);
  readonly activeUsersCount = computed(
    () => this.users().filter((u) => u.status === 'Active').length
  );
  readonly awaitingActivationCount = computed(
    () => this.users().filter((u) => u.status === 'Pending' || u.status === 'Deactive').length
  );
  readonly requestsPendingCount = computed(
    () => this.users().filter((u) => u.profile === 'Pending' && u.status !== 'Active').length
  );
  readonly profilesSubmittedCount = computed(
    () => this.users().filter((u) => u.profile === 'Submitted').length
  );

  getUserById(id: number | string): UserRow | undefined {
    return this.users().find((u) => String(u.id) === String(id));
  }

  addUser(userData: Omit<UserRow, 'id' | 'name'>): UserRow {
    const fullName = [userData.firstName, userData.middleName, userData.lastName]
      .filter(Boolean)
      .join(' ')
      .trim();

    const newUser: UserRow = {
      id: `temp_${Date.now()}`,
      name: fullName,
      ...userData,
      email: userData.companyEmail || userData.email,
    };

    this.users.update((list) => [newUser, ...list]);
    return newUser;
  }

  updateUser(id: number | string, updated: Partial<UserRow>): void {
    this.users.update((list) =>
      list.map((u) => {
        if (String(u.id) !== String(id)) return u;
        const merged = { ...u, ...updated };
        if (updated.firstName || updated.lastName || updated.middleName) {
          merged.name = [merged.firstName, merged.middleName, merged.lastName]
            .filter(Boolean)
            .join(' ')
            .trim();
        }
        if (updated.companyEmail) {
          merged.email = updated.companyEmail;
        }
        return merged;
      })
    );
  }

  deleteUser(id: number | string): void {
    this.users.update((list) => list.filter((u) => String(u.id) !== String(id)));
  }
}
