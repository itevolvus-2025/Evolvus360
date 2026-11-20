import { Injectable, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';

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
  role: string;
  designation: string;
  location?: string;
  entity?: string;
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
  reasonForChange?: string;
  effectiveDate?: string;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly apiService = inject(ApiService);

  readonly users = signal<UserRow[]>([
    {
      id: 1,
      firstName: 'Jhon',
      middleName: '',
      lastName: 'Doe',
      name: 'Jhon Doe',
      code: 'E001',
      companyEmail: 'jhon.doe@evolvus360.com',
      personalEmail: 'jhon.doe@gmail.com',
      email: 'jhon.doe@evolvus360.com',
      phone: '+91 98765 43210',
      role: 'Super Admin',
      department: 'Engineering',
      designation: 'Principal Architect',
      location: 'Bengaluru',
      entity: 'Evolvus India Pvt Ltd',
      pfApplicable: 'Yes',
      joiningDate: '17-11-2026',
      startDate: '17-11-2026',
      endDate: '',
      status: 'Active',
      profile: 'Pending',
    },
    {
      id: 2,
      firstName: 'Rahul',
      middleName: '',
      lastName: 'Mehta',
      name: 'Rahul Mehta',
      code: 'E002',
      companyEmail: 'rahul.mehta@evolvus360.com',
      personalEmail: 'rahul.mehta@gmail.com',
      email: 'rahul.mehta@evolvus360.com',
      phone: '+91 98765 43211',
      role: 'HR Manager',
      department: 'Human Resources',
      designation: 'HR Generalist / Operations Lead',
      location: 'Hyderabad',
      entity: 'Evolvus India Pvt Ltd',
      pfApplicable: 'Yes',
      joiningDate: '17-11-2026',
      startDate: '17-11-2026',
      endDate: '',
      status: 'Inactive',
      profile: 'Submitted',
    },
    {
      id: 3,
      firstName: 'Priya',
      middleName: '',
      lastName: 'Nair',
      name: 'Priya Nair',
      code: 'E014',
      companyEmail: 'priya.nair@evolvus360.com',
      personalEmail: 'priya.nair@gmail.com',
      email: 'priya.nair@evolvus360.com',
      phone: '+91 98765 43212',
      role: 'Employee',
      department: 'Finance',
      designation: 'Senior Financial Analyst',
      location: 'Bengaluru',
      entity: 'Evolvus India Pvt Ltd',
      pfApplicable: 'Yes',
      joiningDate: '17-11-2026',
      startDate: '17-11-2026',
      endDate: '',
      status: 'Active',
      profile: 'Approved',
    },
  ]);

  readonly isLoading = signal(false);

  constructor() {
    this.loadUsers();
  }

  /**
   * Load users from backend API (GET /api/v1/users)
   * Falls back to default users if offline or unauthenticated
   */
  loadUsers(): void {
    this.isLoading.set(true);
    this.apiService.get<{ items: any[] }>(API_ENDPOINTS.users.list).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        const items = res?.data?.items;
        if (Array.isArray(items) && items.length > 0) {
          const mapped: UserRow[] = items.map((u: any) => {
            const firstName = u.first_name || '';
            const lastName = u.last_name || '';
            const fullName = [firstName, u.middle_name, lastName]
              .filter(Boolean)
              .join(' ')
              .trim() || u.employee_code || 'User';

            return {
              id: u.id || u.user_id,
              firstName,
              middleName: u.middle_name || '',
              lastName,
              name: fullName,
              code: u.employee_code || 'E001',
              companyEmail: u.company_email || u.email || '',
              personalEmail: u.personal_email || '',
              email: u.company_email || u.email || '',
              phone: u.phone || '',
              role: u.role?.name || u.role || 'Employee',
              department: u.department?.name || u.department || 'Engineering',
              designation: u.designation || 'Specialist',
              location: u.location || 'Bengaluru',
              entity: u.entity?.name || 'Evolvus India Pvt Ltd',
              pfApplicable: 'Yes',
              joiningDate: u.joining_date || '17-11-2026',
              startDate: u.start_date || '17-11-2026',
              endDate: u.end_date || '',
              status: (u.account_status === 'ACTIVE' || u.status === 'Active' ? 'Active' : 'Inactive') as UserStatus,
              profile: (u.profile_status === 'APPROVED' ? 'Approved' : u.profile_status === 'SUBMITTED' ? 'Submitted' : 'Pending') as ProfileStatus,
            };
          });
          this.users.set(mapped);
          console.log(`[UserService] Loaded ${mapped.length} users from backend API.`);
        }
      },
      error: (err) => {
        this.isLoading.set(false);
        console.warn('[UserService] Backend offline or unauthenticated, using local user list:', err.message);
      },
    });
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
