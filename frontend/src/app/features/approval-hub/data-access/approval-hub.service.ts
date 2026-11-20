import { Injectable, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';

export type ApprovalType = 'EMPLOYEE ONBOARDING' | 'LEAVES & TIME-OFF' | 'ROLE ESCALATION';
export type ApprovalStatus = 'Pending' | 'Authorized' | 'Rejected';

export interface ApprovalItem {
  id: string | number;
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
  userId?: string | number;
}

@Injectable({ providedIn: 'root' })
export class ApprovalHubService {
  private readonly apiService = inject(ApiService);
  private readonly notification = inject(NotificationService);

  readonly items = signal<ApprovalItem[]>([
    {
      id: 1,
      type: 'EMPLOYEE ONBOARDING',
      title: 'New Hire Onboarding: Jhon Doe',
      description:
        'HR Manager registered new employee Sanya Kapoor (Junior Full-stack Engineer, Engineering). Proposed Role: Employee. Requires Super Admin approval to activate system login credentials.',
      status: 'Pending',
      submittedDate: 'Nov 4, 2026',
      admin: 'Asha Rao',
      department: 'Engineering',
      assignedRole: 'Employee',
      submittedBy: 'Meera Iyer (HR Manager)',
      loginState: 'Disabled (Pending Approval)',
      userId: 1,
    },
    {
      id: 2,
      type: 'EMPLOYEE ONBOARDING',
      title: 'New Hire Onboarding: Rahul Mehta',
      description:
        'HR Manager registered new employee Rahul Mehta (HR Generalist, Human Resources). Proposed Role: HR Manager. System login credentials authorized.',
      status: 'Authorized',
      submittedDate: 'Nov 2, 2026',
      admin: 'Asha Rao',
      department: 'Human Resources',
      assignedRole: 'HR Manager',
      submittedBy: 'Meera Iyer (HR Manager)',
      loginState: 'Enabled (Active)',
      userId: 2,
    },
    {
      id: 3,
      type: 'LEAVES & TIME-OFF',
      title: 'Annual Leave Request: Priya Nair',
      description:
        'Senior Financial Analyst requested 3 days of Annual Leave from Nov 20, 2026 to Nov 22, 2026 for personal commitments.',
      status: 'Authorized',
      submittedDate: 'Nov 1, 2026',
      admin: 'Asha Rao',
      department: 'Finance',
      assignedRole: 'Employee',
      submittedBy: 'Priya Nair (Self)',
      loginState: 'Not Applicable',
      userId: 3,
    },
  ]);

  /** KPI Metrics matching screenshot */
  readonly totalPending = computed(
    () => this.items().filter((i) => i.status === 'Pending').length
  );

  readonly employeeOnboardingCount = computed(
    () =>
      this.items().filter(
        (i) => i.type === 'EMPLOYEE ONBOARDING' && i.status === 'Pending'
      ).length
  );

  readonly leavesCount = computed(
    () =>
      this.items().filter(
        (i) => i.type === 'LEAVES & TIME-OFF' && i.status === 'Pending'
      ).length
  );

  readonly authorizedCount = computed(
    () => this.items().filter((i) => i.status === 'Authorized').length
  );

  readonly totalCount = computed(() => this.items().length);

  /**
   * Authorize a pending request and activate employee credentials
   */
  authorize(id: string | number): void {
    const item = this.items().find((i) => String(i.id) === String(id));
    if (!item) return;

    this.items.update((list) =>
      list.map((it) =>
        String(it.id) === String(id)
          ? {
              ...it,
              status: 'Authorized',
              loginState: 'Enabled (Active)',
            }
          : it
      )
    );

    // Call backend API if a backend UUID is associated
    if (item.userId && typeof item.userId === 'string' && !item.userId.startsWith('temp_')) {
      this.apiService.post(API_ENDPOINTS.users.approve(item.userId), {}).subscribe({
        next: () => {
          console.log(`[ApprovalHub] User ${item.userId} approved on backend.`);
        },
        error: (err) => {
          console.warn('[ApprovalHub] Backend approval sync failed:', err.message);
        },
      });
    }

    this.notification.show(
      `Request "${item.title}" authorized and login enabled successfully!`,
      'success'
    );
  }

  /**
   * Reject a pending request
   */
  reject(id: string | number): void {
    const item = this.items().find((i) => String(i.id) === String(id));
    if (!item) return;

    this.items.update((list) =>
      list.map((it) =>
        String(it.id) === String(id)
          ? {
              ...it,
              status: 'Rejected',
              loginState: 'Disabled (Rejected)',
            }
          : it
      )
    );

    this.notification.show(`Request "${item.title}" has been rejected.`, 'info');
  }
}
